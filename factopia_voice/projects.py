"""Caption projects: one imported file (or one voiceover clip), its caption
track and its style. Long jobs run in the background and report progress."""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path

from . import captions, library, media, render, text as T
from .config import DATA, MODELS, OUTPUT, profile_store
from .listeners import create_listener

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
        return json.loads((_folder(project_id) / "project.json").read_text(encoding="utf-8"))
    except OSError:
        raise ValueError("That captions project no longer exists.")


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
                           | {"lines": len(p.get("lines", []))})
            except (OSError, ValueError):
                continue
    return sorted(out, key=lambda p: p.get("created") or "", reverse=True)


def delete(project_id):
    shutil.rmtree(_folder(project_id), ignore_errors=True)


def source_path(project):
    return _folder(project["id"]) / project["source"]


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
                     "length": "short", "style": default_style(), "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                     **info})
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


def update(project_id, lines=None, style=None):
    project = load(project_id)
    if lines is not None:
        project["lines"] = captions.tidy(lines, project["duration"])
    if style is not None:
        project["style"] = render.clean_style(style)
        profile = profile_store.load()
        profile["caption_style"] = project["style"]          # the next project starts with this look
        profile_store.save(profile)
    return save(project)


def regroup(project_id, length):
    project = load(project_id)
    if not project["words"]:
        raise ValueError("Transcribe the file first.")
    project["length"] = length if length in captions.LENGTHS else "short"
    project["lines"] = captions.group(project["words"], project["length"])
    return save(project)


# ---- background jobs -------------------------------------------------------
def _start(kind, work):
    job_id = uuid.uuid4().hex[:10]
    job = jobs[job_id] = {"id": job_id, "kind": kind, "percent": 0, "detail": "Starting", "done": False,
                          "error": None, "result": None}

    def progress(percent, detail=None):
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
