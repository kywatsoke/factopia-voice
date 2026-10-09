"""The built-in translation engine: Google's TranslateGemma run by llama.cpp's
llama-server (MIT), which ships inside the installed app. No extra app, no
account: the model file is downloaded once from a public mirror on Hugging Face.

llama-server uses the Mac's graphics chip (Metal) and, on Windows, a graphics
card through Vulkan when there is one; otherwise the processor. It is started
on first use, kept loaded while translating, and stopped after a quiet spell
so its memory comes back."""
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..config import LOGS, MODELS, profile_store
from ..downloads import fetch_one
from ..languages import valid
from .base import Translator, clean_output, prompt_for

TERMS_URL = "https://ai.google.dev/gemma/terms"
POLICY_URL = "https://ai.google.dev/gemma/prohibited_use_policy"
NOTICE = "Gemma is provided under and subject to the Gemma Terms of Use found at ai.google.dev/gemma/terms"
IDLE_SECONDS = 600
FOLDER = "translation"


@dataclass(frozen=True)
class GGUF:
    file: str
    repo: str
    revision: str
    size: int
    sha256: str
    label: str

    @property
    def url(self):
        return f"https://huggingface.co/{self.repo}/resolve/{self.revision}/{self.file}"


# Pinned files (revision and checksum) so every download is the file that was tested.
MODELS_AVAILABLE = {
    "standard": GGUF("translategemma-4b-it.Q4_K_M.gguf", "mradermacher/translategemma-4b-it-GGUF",
                     "main", 0, "", "TranslateGemma 4B"),
    "high": GGUF("translategemma-12b-it.Q4_K_M.gguf", "mradermacher/translategemma-12b-it-GGUF",
                 "main", 0, "", "TranslateGemma 12B"),
}


def size_label(n):
    return f"{n / 1e9:.1f} GB" if n else "about 2.5 GB"


def server_command():
    """How to start llama-server: the copy inside the installed app, or one named
    by FACTOPIA_VOICE_LLAMA_SERVER (tests point it at a stand-in), or one on PATH."""
    custom = os.environ.get("FACTOPIA_VOICE_LLAMA_SERVER")
    if custom:
        if custom.lstrip().startswith("["):
            return json.loads(custom)
        if sys.platform == "win32":
            return [part.strip('"') for part in shlex.split(custom, posix=False)]
        return shlex.split(custom)
    exe = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        for candidate in (base / "llama" / exe, Path(sys.executable).resolve().parent / "llama" / exe,
                          Path(sys.executable).resolve().parent.parent / "Frameworks" / "llama" / exe):
            if candidate.is_file():
                return [str(candidate)]
    found = shutil.which("llama-server")
    return [found] if found else None


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Server:
    """One llama-server process for the whole app, started on demand."""

    def __init__(self):
        self.proc = None
        self.port = None
        self.model = None
        self.mode = None            # "gpu" or "cpu"
        self.lock = threading.RLock()
        self.timer = None
        self.log = None

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def _get(self, path, timeout=3):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=timeout) as r:
            return r.status, r.read()

    def post(self, path, body, timeout=600):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def _launch(self, model_path, gpu):
        command = server_command()
        if not command:
            raise RuntimeError("The translation engine is not part of this copy of Factopia Voice. Use the installed "
                               "app, or choose Ollama under Settings > Translation.")
        self.port = _free_port()
        args = command + ["-m", str(model_path), "--host", "127.0.0.1", "--port", str(self.port),
                          "-c", "4096", "-np", "1"]
        args += ["-ngl", "99"] if gpu else ["-ngl", "0", "--device", "none"]
        LOGS.mkdir(parents=True, exist_ok=True)
        self.log = open(LOGS / "translation-engine.log", "ab")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=self.log, stdin=subprocess.DEVNULL,
                                     creationflags=flags, start_new_session=sys.platform != "win32")
        deadline = time.time() + 240
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return False
            try:
                if self._get("/health")[0] == 200:
                    return True
            except (urllib.error.URLError, OSError, ValueError):
                pass
            time.sleep(0.4)
        self.stop()
        return False

    def ensure(self, model_path, allow_gpu):
        with self.lock:
            self._touch()
            if self.running() and self.model == str(model_path) and (self.mode == "gpu") == allow_gpu:
                return
            self.stop()
            for gpu in ([True, False] if allow_gpu else [False]):
                if self._launch(model_path, gpu):
                    self.model, self.mode = str(model_path), "gpu" if gpu else "cpu"
                    return
                self.stop()
            raise RuntimeError("The translation engine could not start. Details are in the log folder "
                               "(Settings > About > Open log folder).")

    def _touch(self):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(IDLE_SECONDS, self.stop)
        self.timer.daemon = True
        self.timer.start()

    def stop(self):
        with self.lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None
            if self.proc is not None:
                if self.proc.poll() is None:
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.proc.kill()
                self.proc = None
            if self.log:
                self.log.close()
                self.log = None
            self.model = self.mode = None


SERVER = _Server()


class BuiltinTranslator(Translator):
    id = "builtin"
    name = "TranslateGemma (built in)"

    def __init__(self, quality="standard"):
        self.spec = MODELS_AVAILABLE.get(quality, MODELS_AVAILABLE["standard"])
        self.size = size_label(self.spec.size)

    @property
    def path(self):
        return MODELS / FOLDER / self.spec.file

    def installed(self):
        return self.path.is_file() and (not self.spec.size or self.path.stat().st_size >= self.spec.size * 0.98)

    def status(self):
        if not server_command():
            return {"ready": False, "step": "engine", "message": "The built-in translation engine is not part of this copy "
                    "(it comes with the installed app). Choose Ollama under Settings > Translation, or use the installed app."}
        if not self.installed():
            return {"ready": False, "step": "download",
                    "message": f"Translation needs a one-time download of {self.spec.label} ({self.size})."}
        state = f" on the {'graphics chip' if SERVER.mode == 'gpu' else 'processor'}" if SERVER.running() else ""
        return {"ready": True, "step": "ready", "message": f"Ready: {self.spec.label}, built in{state}."}

    def setup(self, on_progress):
        on_progress(1, f"Downloading {self.spec.label}")
        if not self.installed():
            fetch_one(self.spec.url, self.path, self.spec.size, self.spec.sha256 or None,
                      lambda done, total: on_progress(min(99, int(done * 99 / max(total, 1))),
                                                      f"Downloading {self.spec.label}: {done >> 20} of {total >> 20} MB"))
            (self.path.parent / "ABOUT.txt").write_text(
                f"{self.spec.label} ({self.spec.file}), downloaded from https://huggingface.co/{self.spec.repo}\n"
                f"{NOTICE}.\nTerms: {TERMS_URL}\nProhibited use policy: {POLICY_URL}\n", encoding="utf-8")
        on_progress(100, "Ready")

    def translate(self, text, source, target):
        source, target = valid(source), valid(target)
        if source == target or not text.strip():
            return text
        if not self.installed():
            raise ValueError("Set up translation first.")
        allow_gpu = profile_store.load().get("acceleration", "auto") != "off"
        body = {"prompt": f"<start_of_turn>user\n{prompt_for(text, source, target)}<end_of_turn>\n<start_of_turn>model\n",
                "n_predict": max(256, len(text) * 6), "temperature": 0, "top_k": 1, "cache_prompt": True,
                "stop": ["<end_of_turn>", "<start_of_turn>"]}
        for attempt in (1, 2):
            SERVER.ensure(self.path, allow_gpu)
            try:
                reply = SERVER.post("/completion", body)
                return clean_output(reply.get("content", ""))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:200]
                raise RuntimeError(f"Translation failed: {detail}")
            except (urllib.error.URLError, OSError):
                SERVER.stop()                    # the engine stopped; start it once more
                if attempt == 2:
                    raise RuntimeError("The translation engine stopped responding. Try again.")

    def stop(self):
        SERVER.stop()

    def engine_mode(self):
        return SERVER.mode
