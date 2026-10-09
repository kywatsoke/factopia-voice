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
from ..net import open_url

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
                     "d37868f759d2f817a43d28dd80cf9f982ffa62fd", 2_489_909_760,
                     "81200d03e843d2ec1ece6eeafe7d13cb6e5211e1fcd336ade55790b683a08330", "TranslateGemma 4B"),
    "high": GGUF("translategemma-12b-it.Q4_K_M.gguf", "mradermacher/translategemma-12b-it-GGUF",
                 "41d7c8aa650b26791225ad9d0597e674e680da96", 7_300_794_112,
                 "b7aac4b4be7ab0c49b6556c29c4467e74313df7f1e95d9f9676bb2adf0afa528", "TranslateGemma 12B"),
}


def size_label(n):
    return f"{n / 1e9:.1f} GB" if n else "a few GB"


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


# On macOS and Linux, llama-server runs under a tiny shell that ends it as soon
# as the app is gone, however the app ends (Quit, Cmd+Q, a crash, a closed
# terminal). On Windows, a job object does the same.
_WATCH = """
"$@" &
child=$!
trap 'kill $child 2>/dev/null; wait $child 2>/dev/null; exit 0' TERM INT HUP
while kill -0 "$FV_PARENT" 2>/dev/null && kill -0 $child 2>/dev/null; do sleep 1; done
kill $child 2>/dev/null
wait $child
"""
_JOB = None


def _spawn(args, log):
    if sys.platform == "win32":
        proc = subprocess.Popen(args, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        _end_with_app(proc)
        return proc
    env = {**os.environ, "FV_PARENT": str(os.getpid())}
    return subprocess.Popen(["/bin/sh", "-c", _WATCH, "factopia-translation"] + list(args), stdout=log, stderr=log,
                            stdin=subprocess.DEVNULL, env=env, start_new_session=True)


def _end_with_app(proc):
    """Windows: put the process in a job that ends it when the app's last handle
    to the job closes, which happens however the app ends."""
    global _JOB
    try:
        import ctypes
        from ctypes import wintypes

        class IoCounters(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ("Read", "Write", "Other", "ReadBytes", "WriteBytes", "OtherBytes")]

        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IoCounters),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        if _JOB is None:
            job = k32.CreateJobObjectW(None, None)
            info = Extended()
            info.BasicLimitInformation.LimitFlags = 0x2000          # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if job and k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
                _JOB = job                                           # 9 = JobObjectExtendedLimitInformation
        if _JOB:
            k32.AssignProcessToJobObject(_JOB, int(proc._handle))
    except Exception as e:                       # the engine still works; it may outlive a crash
        print(f"Could not tie the translation engine to the app: {e}", flush=True)


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
        self.allowed = None         # whether the graphics chip was allowed when it started
        self.mode = None            # "gpu" or "cpu": what it actually runs on
        self.device = None          # e.g. "Apple M4 GPU", from the engine's log
        self.lock = threading.RLock()
        self.timer = None
        self.log = None
        self.gpu_failed = False     # the graphics chip failed while translating: processor until the app restarts

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def _get(self, path, timeout=3):
        with open_url(f"http://127.0.0.1:{self.port}{path}", timeout=timeout) as r:
            return r.status, r.read()

    def post(self, path, body, timeout=600):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with open_url(req, timeout=timeout) as r:
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
        log_path = LOGS / "translation-engine.log"
        start = log_path.stat().st_size if log_path.exists() else 0
        self.log = open(log_path, "ab")
        self.proc = _spawn(args, self.log)
        deadline = time.time() + 240
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return False
            try:
                if self._get("/health")[0] == 200:
                    self.device = _device_from_log(log_path, start) if gpu else None
                    return True
            except (urllib.error.URLError, OSError, ValueError):
                pass
            time.sleep(0.4)
        self.stop()
        return False

    def ensure(self, model_path, allow_gpu):
        allow_gpu = allow_gpu and not self.gpu_failed
        with self.lock:
            if self.running() and self.model == str(model_path) and self.allowed == allow_gpu:
                self._touch()
                return
            self.stop()
            for gpu in ([True, False] if allow_gpu else [False]):
                if self._launch(model_path, gpu):
                    self.model, self.allowed = str(model_path), allow_gpu
                    self.mode = "gpu" if gpu and self.device else "cpu"
                    self._touch()                 # stop after IDLE_SECONDS without a translation
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
                        if sys.platform == "win32":
                            self.proc.kill()
                        else:
                            import signal
                            try:
                                os.killpg(self.proc.pid, signal.SIGKILL)   # the watcher and the engine
                            except OSError:
                                pass
                        self.proc.wait(timeout=5)
                self.proc = None
            if self.log:
                self.log.close()
                self.log = None
            self.model = self.mode = self.allowed = self.device = None


def _device_from_log(path, start):
    """The graphics device llama-server says it is using, e.g. "Apple M4 GPU".
    None when it runs on the processor only."""
    import re
    try:
        with open(path, "rb") as f:
            f.seek(start)
            text = f.read(400_000).decode("utf-8", "replace")
    except OSError:
        return None
    m = re.search(r"using device (?:\S+) \(([^)]+)\)", text) or re.search(r"GPU name:\s*(.+)", text)
    return m.group(1).strip() if m else None


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
        state = ""
        if SERVER.running():
            state = f", running on the {SERVER.device}" if SERVER.mode == "gpu" else ", running on the processor"
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
        for attempt in (1, 2, 3):
            SERVER.ensure(self.path, allow_gpu)
            on_gpu = SERVER.mode == "gpu"
            try:
                reply = SERVER.post("/completion", body)
                return clean_output(reply.get("content", ""))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:200]
                if not on_gpu:
                    raise RuntimeError(f"Translation failed: {detail}")
                print(f"Translation failed on the graphics chip ({e.code}: {detail}); using the processor.", flush=True)
                SERVER.gpu_failed = True         # a graphics driver problem: the processor from now on
                SERVER.stop()
            except (urllib.error.URLError, OSError):
                SERVER.stop()                    # the engine stopped; start it again
                if on_gpu and attempt >= 2:
                    SERVER.gpu_failed = True     # it keeps stopping on the graphics chip
                if attempt == 3:
                    raise RuntimeError("The translation engine stopped responding. Try again.")
        raise RuntimeError("The translation engine stopped responding. Try again.")

    def stop(self):
        SERVER.stop()

    def engine_mode(self):
        return SERVER.mode
