"""A small local HTTP API plus the web interface. It listens on this computer
only (127.0.0.1) and refuses requests that come from other websites."""
import json
import mimetypes
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import __version__, library
from .config import CACHE, DATA, OUTPUT, PORT, WEB, dictionary_store, profile_store
from .pipeline import Studio, clamp
from .translate import REGISTRY as TRANSLATORS

studio = Studio()
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
STATIC = {"/": "index.html", "/app.css": "app.css", "/app.js": "app.js", "/icon.svg": "icon.svg"}
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml",
         ".mp3": "audio/mpeg", ".wav": "audio/wav"}


def state():
    profile = profile_store.load()
    engine = studio.engine
    voice = engine.voice(profile["voice"]) if engine else None
    return {
        "version": __version__, "status": studio.status, "profile": profile,
        "voice": voice.to_dict() if voice else None,
        "engine": {"id": engine.id, "name": engine.name, "license": engine.license,
                   "voices": len(engine.voices())} if engine else None,
        "folder": str(OUTPUT), "data_folder": str(DATA),
        "dictionary": dictionary_store.load(), "library": library.items(),
        "translation": bool(TRANSLATORS),
    }


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
        with open(path, "rb") as f:
            f.seek(start)
            body = f.read(end - start + 1)
        headers = {"Accept-Ranges": "bytes"}
        if code == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        if download_name:
            headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
        ctype = TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.reply(code, body, ctype, headers)

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
        try:
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length) or b"{}") if length < 2_000_000 else None
            if not isinstance(data, dict):
                raise ValueError
        except ValueError:
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
            if path == "/api/open":
                open_folder(OUTPUT)
                return self.reply(200, {"ok": True})
            if path == "/api/quit":
                self.reply(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
        except (ValueError, RuntimeError) as e:
            return self.reply(400, {"error": str(e)})
        except Exception as e:
            return self.reply(500, {"error": f"Something went wrong: {e}"})
        self.reply(404, {"error": "Not found."})


def open_folder(folder):
    if sys.platform == "win32":
        os.startfile(folder)  # noqa
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(folder)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_server():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    return server
