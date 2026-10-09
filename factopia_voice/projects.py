"""Caption projects: one imported file (or one voiceover clip), its caption
track and its style. Long jobs run in the background and report progress."""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path

from . import captions, fonts, languages, library, media, render, text as T
from .config import DATA, MODELS, OUTPUT, profile_store
from .listeners import create_listener
from .translate import get_translator

PROJECTS = DATA / "projects"
jobs = {}
_lock = threading.RLock()


# ---- storage ---------------------------------------------------------------
def _folder(project_id):
    if not project_id or not all(c in "0123456789abcdef" for c in project_id):
        raise ValueError("Unknown captions project.")
    return PROJECTS / project_id


def load(project_id):
    try:
        project = json.loads((_folder(project_id) / "project.json").read_text(encoding="utf-8"))
    except OSError:
        raise ValueError("That captions project no longer exists.")
    project.setdefault("language", "en")             # projects made by 2.1 are English
    project.setdefault("has_audio", True)
    return project


def save(project):
    with _lock:
        project["updated"] = time.strftime("%Y-%m-%d %H:%M")
        folder = _folder(project["id"])
        tmp = folder / "project.tmp"
        tmp.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
        tmp.replace(folder / "project.json")
    return project


def summaries():
    out = []
    if PROJECTS.is_dir():
        for folder in PROJECTS.iterdir():
            try:
                p = json.loads((folder / "project.json").read_text(encoding="utf-8"))
                out.append({k: p.get(k) for k in ("id", "name", "duration", "has_video", "updated", "created")}
                           | {"lines": len(p.get("lines", [])), "language": p.get("language", "en")})
            except (OSError, ValueError):
                continue
    return sorted(out, key=lambda p: p.get("created") or "", reverse=True)


def delete(project_id):
    shutil.rmtree(_folder(project_id), ignore_errors=True)


def source_path(project):
    return _folder(project["id"]) / project["source"] if project.get("source") else None


def default_style():
    return render.clean_style(profile_store.load().get("caption_style"))


def _create(name, source_file, script=""):
    project_id = uuid.uuid4().hex[:12]
    folder = _folder(project_id)
    folder.mkdir(parents=True)
    try:
        source = "source" + Path(source_file).suffix.lower()
        shutil.move(str(source_file), folder / source)
        info = media.probe(folder / source)
        if not info["has_audio"]:
            raise ValueError("That file has no sound to caption.")
        media.extract_audio(folder / source, folder / "audio.wav")
        return save({"id": project_id, "name": name, "source": source, "script": script, "words": [], "lines": [],
                     "length": "short", "language": "en", "style": default_style(),
                     "created": time.strftime("%Y-%m-%d %H:%M:%S"), **info})
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


def create_from_file(path, filename):
    if Path(filename).suffix.lower() not in media.MEDIA_TYPES:
        raise ValueError("That file type is not supported. Use a video or audio file such as mp4, mov, mp3 or wav.")
    return _create(Path(filename).name, path)


def create_from_clip(clip_id):
    clip = next((c for c in library.items() if c["id"] == clip_id), None)
    if clip is None:
        raise ValueError("That clip is no longer in the library.")
    copy = PROJECTS / f"_{uuid.uuid4().hex[:8]}{Path(clip['file']).suffix}"
    PROJECTS.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUTPUT / clip["file"], copy)
    return _create(clip["title"], copy, script=clip["script"])


def import_srt(text, filename, project_id=None, language=None):
    """Load a subtitle file: into an existing project (its timings replace the
    captions), or as a project of its own when there is no video."""
    lines = captions.parse_srt(text)
    lang = languages.valid(language) if language else languages.detect(" ".join(l["text"] for l in lines[:40]))
    if project_id:
        project = load(project_id)
    else:
        project_id = uuid.uuid4().hex[:12]
        _folder(project_id).mkdir(parents=True)
        project = {"id": project_id, "name": Path(filename).name, "source": "", "script": "", "words": [],
                   "length": "short", "created": time.strftime("%Y-%m-%d %H:%M:%S"), "has_video": False,
                   "has_audio": False, "width": 1080, "height": 1920, "fps": 30.0,
                   "duration": max(l["end"] for l in lines), "style": default_style()}
    project.update(lines=captions.tidy(lines, project.get("duration") or None), language=lang, words=[])
    project["style"]["font"] = fonts.for_language(lang, project["style"].get("font", ""))
    return save(project)


def update(project_id, lines=None, style=None, language=None):
    project = load(project_id)
    if language is not None:
        project["language"] = languages.valid(language)
        project["style"]["font"] = fonts.for_language(project["language"], project["style"].get("font", ""))
    if lines is not None:
        project["lines"] = captions.tidy(lines, project["duration"])
    if style is not None:
        project["style"] = render.clean_style(style)
        if language is None and style.get("font") and not fonts.covers(project["style"]["font"], project.get("language", "en")):
            raise ValueError("That font has no " + languages.LANGUAGES[project.get("language", "en")]["name"]
                             + " letters, so the captions would show empty boxes. Pick another font.")
        profile = profile_store.load()
        profile["caption_style"] = project["style"]          # the next project starts with this look
        profile_store.save(profile)
    return save(project)


def regroup(project_id, length):
    project = load(project_id)
    if not project["words"]:
        raise ValueError("Line length can only change on captions made from speech.")
    project["length"] = length if length in captions.LENGTHS else "short"
    project["lines"] = captions.group(project["words"], project["length"])
    return save(project)


# ---- background jobs -------------------------------------------------------
def _start(kind, work):
    job_id = uuid.uuid4().hex[:10]
    job = jobs[job_id] = {"id": job_id, "kind": kind, "percent": 0, "detail": "Starting", "done": False,
                          "error": None, "result": None}

    def progress(percent, detail=None):
        if percent is not None:
            job["percent"] = int(percent)
        if detail:
            job["detail"] = detail

    def run():
        try:
            job["result"] = work(progress)
        except (ValueError, RuntimeError, IOError) as e:
            job["error"] = str(e)
        except Exception as e:
            traceback.print_exc()
            job["error"] = f"Something went wrong: {e}"
        job["done"] = True

    threading.Thread(target=run, daemon=True).start()
    return job


def start_transcribe(project_id, script=None, length=None):
    project = load(project_id)

    def work(progress):
        listener = create_listener()
        if not listener.ready(MODELS):
            listener.install(MODELS, progress)
        progress(0, "Listening to the recording")
        folder = _folder(project_id)
        out = folder / "words.json"
        out.unlink(missing_ok=True)
        proc = subprocess.Popen(
            [sys.executable, "-m", "factopia_voice.listeners.worker", listener.id, str(MODELS),
             str(folder / "audio.wav"), str(out)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(Path(__file__).resolve().parent.parent),
            creationflags=media.NO_WINDOW)
        for line in proc.stdout:
            if line.startswith("P "):
                progress(int(line[2:]), "Listening to the recording")
        errors = proc.stderr.read()
        if proc.wait() != 0 or not out.is_file():
            print(errors, file=sys.stderr)
            raise RuntimeError("Speech recognition stopped unexpectedly. " + errors.strip().splitlines()[-1][:200]
                               if errors.strip() else "Speech recognition stopped unexpectedly.")
        words = captions.word_ends(json.loads(out.read_text(encoding="utf-8")), project["duration"] or 1e9)
        out.unlink(missing_ok=True)
        fresh = load(project_id)
        if script is not None:
            fresh["script"] = script
        exact = T.normalize(fresh["script"]).replace("\n", " ") if fresh["script"].strip() else ""
        if exact:
            import re
            exact = re.sub(r"\[\s*pause[^\]]*\]", " ", exact, flags=re.I)
            words = captions.align(exact, words)
        fresh["words"] = words
        fresh["length"] = length if length in captions.LENGTHS else fresh.get("length", "short")
        fresh["lines"] = captions.group(words, fresh["length"])
        save(fresh)
        return {"lines": len(fresh["lines"]), "words": len(words)}

    return _start("transcribe", work)


def start_translate(project_id, target):
    """Translate a caption track sentence by sentence into a new project that
    keeps the same video and timings, so the original stays untouched."""
    project = load(project_id)
    source = project.get("language", "en")
    target = languages.valid(target)
    if target == source:
        raise ValueError("These captions are already in " + languages.LANGUAGES[target]["name"] + ".")
    if not project["lines"]:
        raise ValueError("There are no captions to translate yet.")
    translator = get_translator()
    if not translator.status()["ready"]:
        raise ValueError("Set up translation first (Translate screen).")

    def work(progress):
        groups = captions.sentences(project["lines"], source)
        progress(1, f"Translating 0 of {len(groups)} sentences")
        done = translator.translate_many([g["text"] for g in groups], source, target,
                                         lambda d, n: progress(int(d * 97 / n), f"Translating {d} of {n} sentences"))
        lines = []
        for group, text in zip(groups, done):
            lines += captions.spread(text, group["start"], group["end"], target)
        new_id = uuid.uuid4().hex[:12]
        folder = _folder(new_id)
        folder.mkdir(parents=True)
        for name in (project.get("source"), "audio.wav"):
            if name and (_folder(project_id) / name).exists():
                try:
                    os.link(_folder(project_id) / name, folder / name)      # no second copy of a large video
                except OSError:
                    shutil.copyfile(_folder(project_id) / name, folder / name)
        style = dict(project["style"])
        style["font"] = fonts.for_language(target, style.get("font", ""))
        if target != "en":
            style["uppercase"] = False
        copy = {k: v for k, v in project.items() if k not in ("id", "lines", "words", "script", "style", "language", "name")}
        save({**copy, "id": new_id, "name": f"{Path(project['name']).stem} ({languages.LANGUAGES[target]['name']})",
              "lines": captions.tidy(lines, project.get("duration") or None), "words": [], "script": "", "style": style,
              "language": target, "translated_from": project_id, "created": time.strftime("%Y-%m-%d %H:%M:%S")})
        progress(100, "Done")
        return {"id": new_id, "lines": len(lines), "sentences": len(groups)}

    return _start("translate", work)


def start_translate_text(text, source, target):
    if len(text) > 20000:
        raise ValueError("That text is too long. Translate it in parts.")
    source = languages.detect(text) if source == "auto" else languages.valid(source)
    translator = get_translator()
    if not translator.status()["ready"]:
        raise ValueError("Set up translation first.")

    def work(progress):
        paragraphs = [p for p in re.split(r"\n\s*\n", text.strip())]
        progress(1, "Translating")
        parts = translator.translate_many(paragraphs, source, target,
                                          lambda d, n: progress(int(d * 99 / n), f"Translating part {d} of {n}"))
        return {"text": "\n\n".join(parts), "source": source, "target": languages.valid(target)}

    return _start("translate-text", work)


def start_translation_setup():
    return _start("setup", lambda progress: (get_translator().setup(progress), get_translator().status())[1])


def export_srt(project_id):
    project = load(project_id)
    if not project["lines"]:
        raise ValueError("There are no captions to export yet.")
    name = f"{T.slug(Path(project['name']).stem)}_{time.strftime('%Y%m%d-%H%M%S')}.srt"
    (OUTPUT / name).write_text(captions.srt(project["lines"]), encoding="utf-8")
    return {"file": name}


def start_export_video(project_id):
    project = load(project_id)
    if not project["has_video"]:
        raise ValueError("This project has sound only, so there is no picture to put captions on. Export the subtitle file instead.")
    if not project["lines"]:
        raise ValueError("There are no captions to export yet.")

    def work(progress):
        name = f"{T.slug(Path(project['name']).stem)}_captioned_{time.strftime('%Y%m%d-%H%M%S')}.mp4"
        started = time.time()
        progress(0, "Drawing captions into the video")
        frames = render.burn(source_path(project), OUTPUT / name, project["lines"], project["style"], project,
                             lambda pct: progress(pct, "Drawing captions into the video"))
        return {"file": name, "frames": frames, "took": round(time.time() - started, 1),
                "megabytes": round(os.path.getsize(OUTPUT / name) / 1e6, 1)}

    return _start("export", work)
