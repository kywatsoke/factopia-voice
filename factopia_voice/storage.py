"""What the app keeps on disk: how big each part is, removing downloaded models,
moving the models to another drive, and bringing in work from a 2.x folder."""
import json
import os
import shutil
from pathlib import Path

from . import config
from .config import CACHE, DATA, LOCATIONS, MODELS, OUTPUT, PROJECTS
from .jobs import start


def size_of(path):
    path = Path(path)
    if path.is_file():
        return path.stat().st_size
    total = 0
    if path.is_dir():
        for root, _, files in os.walk(path):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                except OSError:
                    pass
    return total


def _model_items():
    from .engines import create_engine
    from .listeners.parakeet import FOLDER as SPEECH
    from .translate import llamacpp
    voice = [MODELS / f.name for f in create_engine("kokoro").files()]
    items = [{"id": "voice", "label": "Voice (Kokoro)", "paths": voice, "removable": False,
              "note": "Needed for voiceovers"},
             {"id": "speech", "label": "Speech to text (Parakeet)", "paths": [MODELS / SPEECH], "removable": True,
              "note": "Downloads again the next time you make captions"}]
    for quality, spec in llamacpp.MODELS_AVAILABLE.items():
        items.append({"id": f"translation-{quality}", "label": f"Translation ({spec.label})",
                      "paths": [MODELS / llamacpp.FOLDER / spec.file], "removable": True,
                      "note": "Downloads again the next time you set up translation"})
    return items


def summary():
    items = []
    for item in _model_items():
        size = sum(size_of(p) for p in item["paths"])
        if size:
            items.append({k: v for k, v in item.items() if k != "paths"} | {"bytes": size, "kind": "model"})
    items += [
        {"id": "projects", "label": "Captions projects", "bytes": size_of(PROJECTS), "removable": False, "kind": "work",
         "note": "Copies of imported videos; delete projects in Captions"},
        {"id": "output", "label": "Your files", "bytes": size_of(OUTPUT), "removable": False, "kind": "work",
         "note": str(OUTPUT)},
        {"id": "cache", "label": "Temporary files", "bytes": size_of(CACHE), "removable": True, "kind": "other",
         "note": "Previews and the font list; made again when needed"},
    ]
    try:
        free = shutil.disk_usage(MODELS if MODELS.exists() else DATA).free
    except OSError:
        free = None
    return {"items": items, "models_folder": str(MODELS), "data_folder": str(DATA), "output_folder": str(OUTPUT),
            "free_bytes": free, "layout": config.LAYOUT, "moved": MODELS != DATA / "models"}


def remove(item_id):
    if item_id == "cache":
        shutil.rmtree(CACHE, ignore_errors=True)
        CACHE.mkdir(parents=True, exist_ok=True)
        return summary()
    item = next((i for i in _model_items() if i["id"] == item_id), None)
    if item is None or not item["removable"]:
        raise ValueError("That cannot be removed here.")
    if item_id.startswith("translation"):
        from .translate import shutdown
        shutdown()                       # the engine may have the file open
    for path in item["paths"]:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    return summary()


def _copy_tree(src, dest, progress, label, done=0, total=0, skip_existing=True):
    """Copy every file under src into dest, reporting bytes copied."""
    for root, _, files in os.walk(src):
        for name in files:
            if name.endswith((".part", ".tmp")):
                continue
            source = Path(root) / name
            target = Path(dest) / source.relative_to(src)
            size = source.stat().st_size
            if skip_existing and target.exists() and target.stat().st_size == size:
                done += size
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(source, "rb") as a, open(str(target) + ".part", "wb") as b:
                while True:
                    chunk = a.read(1 << 22)
                    if not chunk:
                        break
                    b.write(chunk)
                    done += len(chunk)
                    if total:
                        progress(min(99, int(done * 100 / total)), f"{label}: {done >> 20} of {total >> 20} MB")
            os.replace(str(target) + ".part", target)
            shutil.copystat(source, target)
    return done


def start_move(folder):
    """Copy the models to another folder (for example another drive). The old
    copies are removed the next time the app starts, once nothing uses them."""
    target = Path(folder) / "Factopia Voice models"
    if target.resolve() == MODELS.resolve() or MODELS.resolve() in target.resolve().parents:
        raise ValueError("Pick a folder outside the current models folder.")
    total = size_of(MODELS)
    try:
        if shutil.disk_usage(Path(folder)).free < total * 1.05:
            raise ValueError("There is not enough free space there for the models.")
    except OSError:
        raise ValueError("That folder cannot be used.")

    def work(progress):
        target.mkdir(parents=True, exist_ok=True)
        _copy_tree(MODELS, target, progress, "Moving models", 0, total)
        LOCATIONS.write_text(json.dumps({"models": str(target), "previous": str(MODELS)}), encoding="utf-8")
        progress(100, "Done")
        return {"folder": str(target), "restart": True}

    return start("move-models", work)


def finish_move():
    """On start: delete the old copies left behind by a move."""
    try:
        data = json.loads(LOCATIONS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    previous = data.pop("previous", None)
    if previous and Path(previous).resolve() != MODELS.resolve():
        shutil.rmtree(previous, ignore_errors=True)
        LOCATIONS.write_text(json.dumps(data), encoding="utf-8")


# ---- bringing in work from an earlier version --------------------------------
PROFILE_KEYS = ("voice", "speed", "pause", "format", "max_seconds", "wps", "caption_style", "translation_quality")


def earlier_data(folder):
    """The data folder of a 2.x copy: the app folder itself, or its data folder."""
    folder = Path(folder)
    for candidate in (folder / "data", folder):
        if (candidate / "profile.json").is_file() or (candidate / "library.json").is_file():
            if candidate.resolve() == DATA.resolve():
                raise ValueError("That is the folder this copy already uses.")
            return candidate
    raise ValueError("No Factopia Voice settings were found there. Pick the folder the earlier version was in "
                     "(the one with the Start Factopia Voice files), or its data folder.")


def start_import(folder):
    src = earlier_data(folder)
    total = sum(size_of(src / part) for part in ("output", "projects", "models"))

    def work(progress):
        def read(name, default):
            try:
                return json.loads((src / name).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return default

        old = read("profile.json", {})
        profile = config.profile_store.load()
        profile.update({k: old[k] for k in PROFILE_KEYS if k in old})
        config.profile_store.save(profile)
        words = config.dictionary_store.load()
        known = {w["word"].lower() for w in words}
        config.dictionary_store.save(words + [w for w in read("dictionary.json", []) if w.get("word", "").lower() not in known])
        clips = config.library_store.load()
        ids = {c.get("id") for c in clips}
        config.library_store.save((clips + [c for c in read("library.json", []) if c.get("id") not in ids])[:500])
        done = 0
        for part, dest, label in (("output", OUTPUT, "Copying your files"), ("projects", PROJECTS, "Copying captions projects"),
                                  ("models", MODELS, "Copying downloaded models")):
            if (src / part).is_dir():
                done = _copy_tree(src / part, dest, progress, label, done, total)
        progress(100, "Done")
        return {"clips": len(read("library.json", [])), "words": len(read("dictionary.json", [])), "from": str(src)}

    return start("import", work)
