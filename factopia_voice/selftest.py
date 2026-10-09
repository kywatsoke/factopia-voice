"""Checks that a built copy of the app has everything it needs. The installer
workflow runs it on the packed app on macOS and Windows:

    <app> --self-test result.json

Optional, when the models are at hand (the workflow caches them):
FV_SELFTEST_VOICE=<folder with the Kokoro files> speaks a sentence, and
FV_SELFTEST_SPEECH=<models folder with Parakeet> listens to it again."""
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request

from .net import open_url
from pathlib import Path


def main(argv):
    out = Path(argv[0]) if argv else None
    results = {}
    frozen = bool(getattr(sys, "frozen", False))
    desktop = sys.platform in ("darwin", "win32")

    def check(name, fn, required=True):
        started = time.time()
        try:
            detail = fn()
            results[name] = {"ok": True, "detail": detail}
        except Exception as e:
            traceback.print_exc()
            results[name] = {"ok": False, "detail": f"{type(e).__name__}: {e}"}
        results[name].update(required=required, seconds=round(time.time() - started, 1))

    from . import __version__, media, shaping, workers
    from .config import FROZEN

    check("app", lambda: {"version": __version__, "frozen": FROZEN, "platform": sys.platform,
                          "machine": platform.machine(), "python": sys.version.split()[0]})

    def text_shaping():
        st = shaping.status()
        if desktop and frozen and not st["raqm"]:
            raise RuntimeError(f"Burmese shaping is not available: {st}")
        return st
    check("text shaping", text_shaping)

    def voice_runtime():
        import espeakng_loader
        import kokoro_onnx  # noqa: F401
        import onnxruntime
        import phonemizer  # noqa: F401
        data = Path(espeakng_loader.get_data_path())
        if not data.is_dir():
            raise RuntimeError(f"eSpeak data missing at {data}")
        return {"onnxruntime": onnxruntime.__version__, "providers": onnxruntime.get_available_providers(),
                "espeak_library": Path(espeakng_loader.get_library_path()).name}
    check("voice engine", voice_runtime)

    def speech_runtime():
        import sherpa_onnx
        return {"sherpa_onnx": getattr(sherpa_onnx, "__version__", "?")}
    check("speech engine", speech_runtime)

    def video_tools():
        first = media.run("-version").stdout.decode("utf-8", "replace").splitlines()[0]
        return {"ffmpeg": first[:80], "hardware_encoder": media.LABELS[media.hardware_encoder()]}
    check("video tools", video_tools)

    def fonts_found():
        from . import fonts
        return {"fonts": len(fonts.all_fonts()), "default": fonts.default_id()}
    check("fonts", fonts_found)

    def translation_engine():
        from .translate import llamacpp
        command = llamacpp.server_command()
        if not command:
            raise RuntimeError("llama-server not found")
        r = subprocess.run(command + ["--version"], capture_output=True, text=True, timeout=60,
                           creationflags=media.NO_WINDOW)
        said = (r.stdout + r.stderr).strip().splitlines()
        return {"command": Path(command[0]).name, "version": next((l for l in said if "version" in l.lower()), said[:1])}
    check("translation engine", translation_engine, required=frozen)

    def engine_lifetime():
        """The translation engine is tied to the app (Windows job object; on
        macOS and Linux the shell watcher, which the unit tests check)."""
        from .translate import llamacpp
        if sys.platform != "win32":
            return "shell watcher"
        import ctypes
        from ctypes import wintypes
        log = open(os.devnull, "wb")
        proc = llamacpp._spawn(["cmd", "/c", "ping -n 30 127.0.0.1 >nul"], log)
        try:
            k32 = ctypes.WinDLL("kernel32")
            k32.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
            inside = wintypes.BOOL(False)
            k32.IsProcessInJob(int(proc._handle), llamacpp._JOB, ctypes.byref(inside))
            if not (llamacpp._JOB and inside.value):
                raise RuntimeError("the engine is not tied to the app (job object missing)")
            return "job object"
        finally:
            proc.kill()
            log.close()
    check("engine ends with the app", engine_lifetime, required=frozen)

    def window_toolkit():
        import webview
        detail = {"pywebview": getattr(webview, "__version__", "?")}
        if sys.platform == "win32":
            import clr_loader  # noqa: F401  (pythonnet, which hosts WebView2)
            from webview.platforms import winforms  # noqa: F401
            detail["webview2"] = winforms.__name__
        elif sys.platform == "darwin":
            from webview.platforms import cocoa  # noqa: F401
            detail["backend"] = "cocoa"
        return detail
    check("window", window_toolkit, required=frozen)

    def helper_process():
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "pong.txt"
            r = subprocess.run(workers.command("ping", target), cwd=workers.workdir(), timeout=120,
                               capture_output=True, creationflags=media.NO_WINDOW)
            if r.returncode != 0 or target.read_text(encoding="utf-8") != "pong":
                raise RuntimeError(f"exit {r.returncode}: {r.stderr.decode('utf-8', 'replace')[-300:]}")
            return "ok"
    check("helper process", helper_process)

    def local_server():
        from .server import make_server
        server = make_server(0)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/state")
            with open_url(req, timeout=20) as r:
                state = json.loads(r.read())
            with open_url(f"http://127.0.0.1:{port}/", timeout=20) as r:
                page = r.read()
            if b"Factopia" not in page:
                raise RuntimeError("the interface did not load")
            return {"version": state["version"], "layout": state.get("layout")}
        finally:
            server.shutdown()
    check("local server", local_server)

    voice_dir = os.environ.get("FV_SELFTEST_VOICE")
    if voice_dir:
        def speak():
            import soundfile as sf
            from . import audio
            from .engines import create_engine
            engine = create_engine("kokoro")
            engine.load(Path(voice_dir))
            samples, rate = engine.synthesize("Honey never spoils. Here is why.", "am_michael", 1.0)
            if len(samples) < rate:
                raise RuntimeError("the voice made almost no sound")
            wav = Path(tempfile.gettempdir()) / "fv-selftest.wav"
            audio.save(wav, samples, rate, "wav")
            return {"seconds": round(len(samples) / rate, 2), "file": str(wav), "rate": sf.info(str(wav)).samplerate}
        check("speak", speak)

    speech_dir = os.environ.get("FV_SELFTEST_SPEECH")
    if speech_dir and results.get("speak", {}).get("ok"):
        def listen():
            from . import media as m
            src = results["speak"]["detail"]["file"]
            with tempfile.TemporaryDirectory() as tmp:
                wav16, out = Path(tmp) / "a.wav", Path(tmp) / "words.json"
                m.extract_audio(src, str(wav16))
                r = subprocess.run(workers.command("listen", "parakeet", speech_dir, wav16, out), cwd=workers.workdir(),
                                   timeout=600, capture_output=True, creationflags=m.NO_WINDOW)
                if r.returncode != 0:
                    raise RuntimeError(r.stderr.decode("utf-8", "replace")[-400:])
                words = json.loads(out.read_text(encoding="utf-8"))
                heard = " ".join(w["text"] for w in words)
                if "honey" not in heard.lower():
                    raise RuntimeError(f"heard: {heard!r}")
                return {"heard": heard}
        check("listen", listen)

    ok = all(r["ok"] or not r["required"] for r in results.values())
    summary = {"ok": ok, "checks": results}
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if out:
        out.write_text(text, encoding="utf-8")
    if sys.stdout:
        try:
            print(text)
        except Exception:
            pass
    return 0 if ok else 1


def free_port():          # pragma: no cover - kept for scripts
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
