"""Translation with Google's TranslateGemma run by Ollama, for people who already
use the Ollama app (Settings > Translation engine). The built-in engine
(llamacpp.py) needs no extra app and is the default in the installed app."""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..languages import valid
from .base import Translator, clean_output, prompt_for
from ..net import open_url

BASE = os.environ.get("FACTOPIA_VOICE_OLLAMA", "http://127.0.0.1:11434").rstrip("/")
MODELS = {"standard": ("translategemma:4b", "3.3 GB"), "high": ("translategemma:12b", "8.1 GB")}


def _request(path, body=None, timeout=10):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    return open_url(req, timeout=timeout)


def find_ollama():
    """Where the Ollama program is installed on this computer, if anywhere."""
    found = shutil.which("ollama")
    if found:
        return found
    home = Path.home()
    candidates = [Path("/Applications/Ollama.app/Contents/Resources/ollama"), home / "Applications/Ollama.app/Contents/Resources/ollama",
                  Path("/opt/homebrew/bin/ollama"), Path("/usr/local/bin/ollama"), home / ".homebrew/bin/ollama",
                  home / ".local/bin/ollama", Path(os.environ.get("LOCALAPPDATA", str(home))) / "Programs/Ollama/ollama.exe"]
    return next((str(c) for c in candidates if c.exists()), None)


class OllamaTranslator(Translator):
    id = "ollama"
    name = "TranslateGemma on Ollama"

    def __init__(self, quality="standard"):
        self.model, self.size = MODELS.get(quality, MODELS["standard"])

    # ---- engine state ----------------------------------------------------
    def _running(self):
        try:
            with _request("/api/tags", timeout=3) as r:
                return [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def _has_model(self, names):
        return any(n == self.model or n.startswith(self.model + "-") for n in names or [])

    def status(self):
        names = self._running()
        if names is None:
            program = find_ollama()
            if program:
                return {"ready": False, "step": "start", "message": "Ollama is installed but not running. Press Set up to start it."}
            return {"ready": False, "step": "install", "message": "Translation runs on Ollama, a free app for running AI models on this "
                    "computer. Install it from ollama.com, open it once, then press Check again."}
        if not self._has_model(names):
            return {"ready": False, "step": "download",
                    "message": f"Ollama is running. The translation model ({self.model}, {self.size}) still needs to be downloaded."}
        return {"ready": True, "step": "ready", "message": f"Ready: {self.model} on Ollama."}

    def _start(self):
        program = find_ollama()
        if not program:
            raise RuntimeError("Ollama is not installed. Get it free from ollama.com, open it once, then try again.")
        if sys.platform == "darwin" and ".app/" in program:
            subprocess.Popen(["open", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.Popen([program, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=sys.platform != "win32", creationflags=flags)
        for _ in range(40):
            if self._running() is not None:
                return
            time.sleep(0.5)
        raise RuntimeError("Ollama did not start. Open the Ollama app yourself, then try again.")

    def setup(self, on_progress):
        on_progress(2, "Checking Ollama")
        names = self._running()
        if names is None:
            on_progress(4, "Starting Ollama")
            self._start()
            names = self._running()
        if self._has_model(names):
            on_progress(100, "Ready")
            return
        with _request("/api/pull", {"model": self.model, "stream": True}, timeout=60) as r:
            for raw in r:
                if not raw.strip():
                    continue
                event = json.loads(raw)
                if event.get("error"):
                    raise RuntimeError("Ollama could not download the model: " + event["error"])
                total, done = event.get("total") or 0, event.get("completed") or 0
                if total:
                    on_progress(min(99, 5 + int(done * 94 / total)),
                                f"Downloading {self.model}: {done >> 20} of {total >> 20} MB")
                elif event.get("status"):
                    on_progress(None, str(event["status"]).capitalize())
        if not self._has_model(self._running()):
            raise RuntimeError("The model download did not finish. Try again.")
        on_progress(100, "Ready")

    # ---- translating -----------------------------------------------------
    def translate(self, text, source, target):
        source, target = valid(source), valid(target)
        if source == target or not text.strip():
            return text
        prompt = prompt_for(text, source, target)
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": False,
                "keep_alive": "15m", "options": {"temperature": 0, "num_predict": max(256, len(text) * 6)}}
        try:
            with _request("/api/chat", body, timeout=300) as r:
                reply = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            raise RuntimeError(f"Translation failed: {detail}")
        except (urllib.error.URLError, OSError):
            raise RuntimeError("Ollama stopped responding. Make sure the Ollama app is open, then try again.")
        return clean_output((reply.get("message") or {}).get("content", ""))
