"""A small local HTTP API plus the web interface. It listens on this computer
only (127.0.0.1) and refuses requests that come from other websites."""
import json
import mimetypes
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__, about, config, jobs, library, shell, storage, updates
from . import fonts, languages, media, projects, render
from .config import CACHE, DATA, LOGS, MODELS, OUTPUT, PORT, PROJECTS, WEB, dictionary_store, profile_store
from .pipeline import Studio, clamp
from .translate import ENGINES, engine_choice, get_translator, qualities

studio = Studio()
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
STATIC = {"/": "index.html", "/app.css": "app.css", "/app.js": "app.js", "/captions.js": "captions.js",
          "/translate.js": "translate.js", "/settings.js": "settings.js", "/welcome.js": "welcome.js",
          "/icon.svg": "icon.svg"}
SETTINGS = {"acceleration": ("auto", "off"), "translation_engine": tuple(ENGINES), "check_updates": (True, False)}
MAX_UPLOAD = 8 * 1024 ** 3
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml",
         ".mp3": "audio/mpeg", ".wav": "audio/wav", ".mp4": "video/mp4",
         ".srt": "application/x-subrip; charset=utf-8"}


def state():
    profile = profile_store.load()
    engine = studio.engine
    voice = engine.voice(profile["voice"]) if engine else None
    choice = engine_choice(profile)
    return {
        "version": __version__, "status": studio.status, "profile": profile,
        "voice": voice.to_dict() if voice else None,
        "engine": {"id": engine.id, "name": engine.name, "license": engine.license,
                   "voices": len(engine.voices())} if engine else None,
        "folder": str(OUTPUT), "data_folder": str(DATA), "models_folder": str(MODELS), "layout": config.LAYOUT,
        "shell": shell.MODE, "platform": sys.platform, "welcome": not profile.get("terms_accepted"),
        "dictionary": dictionary_store.load(), "library": library.items(),
        "languages": {k: {"name": v["name"], "native": v["native"]} for k, v in languages.LANGUAGES.items()},
        "translation_languages": list(languages.TRANSLATION),
        "translation": {"engine": choice, "setting": profile.get("translation_engine", "auto"), "engines": ENGINES,
                        "qualities": qualities(choice)},
        "translation_qualities": qualities(choice),
    }


def performance():
    """What each engine runs on, for Settings > Performance."""
    from .translate import llamacpp
    on = profile_store.load().get("acceleration", "auto") != "off"
    if sys.platform == "darwin":
        translation = "Apple graphics chip (Metal)" if on else "Processor"
    elif sys.platform == "win32":
        translation = "Graphics card when one is found (Vulkan), otherwise the processor" if on else "Processor"
    else:
        translation = "Processor"
    if llamacpp.SERVER.running():
        translation = (llamacpp.SERVER.device if llamacpp.SERVER.mode == "gpu" else "Processor") + " (running now)"
    encoder = media.hardware_encoder() if on else None
    return {"acceleration": "auto" if on else "off", "translation": translation,
            "video": media.LABELS[encoder], "voice": "Processor (already faster than real time)",
            "speech": "Processor (already faster than real time)"}


def begin():
    """Start loading the voice, once the model terms have been agreed."""
    if profile_store.load().get("terms_accepted"):
        studio.start()


def public(project):
    """What the browser needs of a project: everything except the word timings."""
    project = dict(project)
    project["has_words"] = bool(project.pop("words", None))
    project.setdefault("language", "en")
    project.setdefault("has_audio", True)
    return project


def clean_dictionary(entries):
    out, seen = [], set()
    for e in entries if isinstance(entries, list) else []:
        word = str(e.get("word", "")).strip()[:60]
        say = str(e.get("say", "")).strip()[:120]
        if word and say and word.lower() not in seen:
            seen.add(word.lower())
            out.append({"word": word, "say": say})
    return out[:500]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    # ---- helpers --------------------------------------------------------
    def reply(self, code, body, ctype="application/json", headers=None):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_file(self, path, download_name=None):
        """Serve a file with byte-range support (Safari needs it to play audio)."""
        if not path.is_file():
            return self.reply(404, {"error": "Not found."})
        size = path.stat().st_size
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes="):
            try:
                a, b = rng[6:].split(",")[0].split("-")
                if a == "":
                    start = max(0, size - int(b))
                else:
                    start = int(a)
                    end = min(int(b), size - 1) if b else size - 1
                if start > end or start >= size:
                    raise ValueError
                code = 206
            except ValueError:
                return self.reply(416, {"error": "Bad range."}, headers={"Content-Range": f"bytes */{size}"})
        headers = {"Accept-Ranges": "bytes"}
        if code == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        if download_name:
            headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
        ctype = TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(path, "rb") as f:               # streamed, so a large video never sits in memory
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def local_only(self):
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            self.reply(403, {"error": "Forbidden."})
            return False
        return True

    # ---- routes ---------------------------------------------------------
    def do_GET(self):
        if not self.local_only():
            return
        url = urlparse(self.path)
        path = unquote(url.path)
        if path in STATIC:
            return self.send_file(WEB / STATIC[path])
        if path == "/api/state":
            return self.reply(200, state())
        if path == "/preview.wav":
            return self.send_file(CACHE / "preview.wav")
        if path == "/api/captions":
            return self.reply(200, {"projects": projects.summaries(), "lengths": list(projects.captions.LENGTHS)})
        if path == "/api/captions/fonts":
            return self.reply(200, {"fonts": [{"id": f["id"], "label": f["label"]} for f in fonts.all_fonts()],
                                    "default": fonts.default_id()})
        if path == "/api/translate/status":
            return self.reply(200, get_translator().status())
        if path == "/api/storage":
            return self.reply(200, storage.summary())
        if path == "/api/performance":
            return self.reply(200, performance())
        if path == "/api/about":
            return self.reply(200, about.info() | {"version": __version__, "logs": str(LOGS),
                                                   "data_folder": str(DATA), "models_folder": str(MODELS)})
        if path == "/api/update":
            if not profile_store.load().get("check_updates", True):
                return self.reply(200, {"current": __version__, "newer": False, "disabled": True})
            return self.reply(200, updates.check(force="force=1" in url.query))
        if path == "/api/job":
            job = jobs.jobs.get((parse_qs(url.query).get("id") or [""])[0])
            return self.reply(200, job) if job else self.reply(404, {"error": "That job is no longer running."})
        if path in ("/api/captions/project", "/api/captions/job"):
            ident = (parse_qs(url.query).get("id") or [""])[0]
            try:
                if path.endswith("/job"):
                    job = projects.jobs.get(ident)
                    return self.reply(200, job) if job else self.reply(404, {"error": "That job is no longer running."})
                return self.reply(200, public(projects.load(ident)))
            except ValueError as e:
                return self.reply(404, {"error": str(e)})
        if path.startswith("/captions/audio/"):
            try:
                return self.send_file(projects._folder(Path(path).name) / "audio.wav")
            except ValueError:
                return self.reply(404, {"error": "Not found."})
        if path.startswith("/audio/"):
            name = Path(path[7:]).name
            return self.send_file(OUTPUT / name, name if "download=1" in url.query else None)
        self.reply(404, {"error": "Not found."})

    do_HEAD = do_GET

    def do_POST(self):
        if not self.local_only():
            return
        origin = self.headers.get("Origin")
        if origin is not None and origin.split("://")[-1] not in ALLOWED_HOSTS:
            return self.reply(403, {"error": "Forbidden."})
        if urlparse(self.path).path == "/api/captions/import":
            return self.receive_upload()
        if urlparse(self.path).path == "/api/captions/import-srt":
            return self.receive_srt()
        try:
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length) or b"{}") if length < 2_000_000 else None
            if not isinstance(data, dict):
                raise ValueError
        except ValueError:
            self.close_connection = True          # the body may be unread
            return self.reply(400, {"error": "Bad request."})
        path = urlparse(self.path).path
        try:
            if path == "/api/generate":
                script = str(data.get("text") or "")
                if len(script) > 20000:
                    raise ValueError("That script is too long for one clip. Split it into parts.")
                return self.reply(200, studio.generate(script, data.get("speed"), data.get("pause"),
                                                       data.get("format"), data.get("target_language")))
            if path == "/api/preview":
                return self.reply(200, studio.preview(str(data.get("text") or "")))
            if path == "/api/profile":
                profile = profile_store.load()
                profile["speed"] = clamp(data.get("speed"), 0.8, 1.3, profile["speed"])
                profile["pause"] = clamp(data.get("pause"), 0.0, 2.0, profile["pause"])
                profile["max_seconds"] = int(clamp(data.get("max_seconds"), 10, 180, profile["max_seconds"]))
                if data.get("format") in ("mp3", "wav"):
                    profile["format"] = data["format"]
                return self.reply(200, profile_store.save(profile))
            if path == "/api/dictionary":
                return self.reply(200, dictionary_store.save(clean_dictionary(data.get("entries"))))
            if path == "/api/library/delete":
                library.delete(str(data.get("id") or ""))
                return self.reply(200, library.items())
            if path == "/api/captions/from-clip":
                return self.reply(200, public(projects.create_from_clip(str(data.get("clip_id") or ""))))
            if path == "/api/captions/transcribe":
                script = data.get("script")
                job = projects.start_transcribe(str(data.get("id") or ""), None if script is None else str(script)[:20000],
                                                data.get("length"))
                return self.reply(200, job)
            if path == "/api/captions/regroup":
                return self.reply(200, public(projects.regroup(str(data.get("id") or ""), data.get("length"))))
            if path == "/api/captions/save":
                project = projects.update(str(data.get("id") or ""), data.get("lines"), data.get("style"), data.get("language"))
                return self.reply(200, {"lines": project["lines"], "style": project["style"], "language": project["language"]})
            if path == "/api/captions/translate":
                return self.reply(200, projects.start_translate(str(data.get("id") or ""), data.get("target")))
            if path == "/api/translate/text":
                return self.reply(200, projects.start_translate_text(str(data.get("text") or ""), str(data.get("source") or "auto"),
                                                                     data.get("target")))
            if path == "/api/translate/setup":
                if data.get("quality") in ("standard", "high"):
                    profile = profile_store.load()
                    profile["translation_quality"] = data["quality"]
                    profile_store.save(profile)
                if data.get("check_only"):
                    return self.reply(200, get_translator().status())
                return self.reply(200, projects.start_translation_setup())
            if path == "/api/captions/preview":
                project = projects.load(str(data.get("id") or ""))
                image = render.preview(projects.source_path(project), project["has_video"], project["width"],
                                       project["height"], clamp(data.get("t"), 0, 1e6, 0.0),
                                       str(data.get("text") or "")[:400], data.get("style") or project["style"])
                import io
                buffer = io.BytesIO()
                image.save(buffer, "JPEG", quality=86)
                return self.reply(200, buffer.getvalue(), "image/jpeg")
            if path == "/api/captions/export":
                ident = str(data.get("id") or "")
                if data.get("kind") == "video":
                    return self.reply(200, projects.start_export_video(ident))
                return self.reply(200, projects.export_srt(ident))
            if path == "/api/captions/delete":
                projects.delete(str(data.get("id") or ""))
                return self.reply(200, {"projects": projects.summaries()})
            if path == "/api/voice/retry":
                if studio.status.get("phase") == "error":
                    studio.status = {"phase": "starting", "percent": 0, "detail": "Trying again"}
                    begin()
                return self.reply(200, {"ok": True})
            if path == "/api/open":
                where = {"output": OUTPUT, "data": DATA, "logs": LOGS, "models": MODELS, "projects": PROJECTS,
                         "licences": about.licences_folder()}.get(data.get("what") or "output")
                if where is None:
                    raise ValueError("Unknown folder.")
                shell.open_path(where)
                return self.reply(200, {"ok": True})
            if path == "/api/reveal":
                name = Path(str(data.get("file") or "")).name
                if not name or not (OUTPUT / name).is_file():
                    raise ValueError("That file is no longer there.")
                shell.reveal(OUTPUT / name)
                return self.reply(200, {"ok": True})
            if path == "/api/open-url":
                shell.open_url(str(data.get("url") or ""))
                return self.reply(200, {"ok": True})
            if path == "/api/settings":
                profile = profile_store.load()
                for key, allowed in SETTINGS.items():
                    if key in data and data[key] in allowed:
                        profile[key] = data[key]
                if profile.get("translation_engine") != profile_store.load().get("translation_engine"):
                    from .translate import shutdown
                    shutdown()
                profile_store.save(profile)
                return self.reply(200, state())
            if path == "/api/welcome/accept":
                profile = profile_store.load()
                if not profile.get("terms_accepted"):
                    import time
                    profile["terms_accepted"] = time.strftime("%Y-%m-%d")
                    profile_store.save(profile)
                begin()
                return self.reply(200, state())
            if path == "/api/import-earlier":
                folder = data.get("folder") or shell.pick_folder()
                if not folder:
                    return self.reply(200, {"cancelled": True})
                return self.reply(200, storage.start_import(folder))
            if path == "/api/storage/remove":
                return self.reply(200, storage.remove(str(data.get("id") or "")))
            if path == "/api/storage/move":
                folder = data.get("folder") or shell.pick_folder()
                if not folder:
                    return self.reply(200, {"cancelled": True})
                return self.reply(200, storage.start_move(folder))
            if path == "/api/focus":
                shell.focus()
                return self.reply(200, {"ok": True})
            if path == "/api/alive":
                import time
                shell.last_seen = time.time()
                return self.reply(200, {"ok": True})
            if path == "/api/quit":
                self.reply(200, {"ok": True})
                threading.Thread(target=quit_app, args=(self.server,), daemon=True).start()
                return
        except (ValueError, RuntimeError) as e:
            return self.reply(400, {"error": str(e)})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return self.reply(500, {"error": f"Something went wrong: {e}"})
        self.reply(404, {"error": "Not found."})


def _receive_upload(self):
    """Save an imported video or audio file straight to disk, then make a captions project from it."""
    try:
        length = int(self.headers.get("Content-Length") or 0)
        name = Path(unquote(self.headers.get("X-File-Name") or "")).name
        if not name or length <= 0:
            raise ValueError("No file was received.")
        if length > MAX_UPLOAD:
            raise ValueError("That file is larger than 8 GB.")
        projects.PROJECTS.mkdir(parents=True, exist_ok=True)
        temp = projects.PROJECTS / f"_upload_{threading.get_ident()}{Path(name).suffix.lower()}"
        try:
            with open(temp, "wb") as out:
                left = length
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        raise ValueError("The upload was interrupted.")
                    out.write(chunk)
                    left -= len(chunk)
            project = projects.create_from_file(temp, name)
        finally:
            temp.unlink(missing_ok=True)
        return self.reply(200, public(project))
    except (ValueError, RuntimeError) as e:
        self.close_connection = True          # part of the body may be unread
        return self.reply(400, {"error": str(e)})
    except Exception as e:
        self.close_connection = True
        return self.reply(500, {"error": f"Something went wrong: {e}"})


Handler.receive_upload = _receive_upload


def _receive_srt(self):
    """A subtitle file, either for an existing project (X-Project) or on its own."""
    try:
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length < 20_000_000:
            raise ValueError("That subtitle file is empty or too large.")
        raw = self.rfile.read(length)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("gb18030", errors="replace")          # common for Chinese subtitle files
        project = projects.import_srt(text, unquote(self.headers.get("X-File-Name") or "subtitles.srt"),
                                      self.headers.get("X-Project") or None, self.headers.get("X-Language") or None)
        return self.reply(200, public(project))
    except (ValueError, RuntimeError) as e:
        self.close_connection = True
        return self.reply(400, {"error": str(e)})
    except Exception as e:
        self.close_connection = True
        return self.reply(500, {"error": f"Something went wrong: {e}"})


Handler.receive_srt = _receive_srt


def quit_app(server):
    """Stop everything: the window (if any), the engines and the server."""
    from .translate import shutdown
    shutdown()
    shell.close()
    server.shutdown()


def make_server(port=PORT):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    actual = server.server_address[1]
    ALLOWED_HOSTS.update({f"127.0.0.1:{actual}", f"localhost:{actual}"})
    return server
