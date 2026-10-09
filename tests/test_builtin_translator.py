import dataclasses
import hashlib
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from factopia_voice import config, downloads
from factopia_voice.translate import get_translator, llamacpp

FAKE = Path(__file__).with_name("fake_llama_server.py")


@pytest.fixture()
def builtin(monkeypatch, tmp_path, clean_data):
    log = tmp_path / "llama.log"
    monkeypatch.setenv("FACTOPIA_VOICE_LLAMA_SERVER", json.dumps([sys.executable, str(FAKE)]))
    monkeypatch.setenv("FAKE_LLAMA_LOG", str(log))
    llamacpp.SERVER.stop()
    t = llamacpp.BuiltinTranslator("standard")
    t.spec = dataclasses.replace(t.spec, size=0, sha256="")      # tiny stand-in files count as the model
    t.path.parent.mkdir(parents=True, exist_ok=True)
    t.path.unlink(missing_ok=True)
    yield t, log
    llamacpp.SERVER.stop()
    t.path.unlink(missing_ok=True)


def log_lines(log):
    return [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []


def test_status_asks_for_the_download_then_is_ready(builtin):
    t, _ = builtin
    st = t.status()
    assert st["ready"] is False and st["step"] == "download" and "TranslateGemma 4B" in st["message"]
    t.path.write_bytes(b"x" * 10)
    assert t.status()["ready"] is True


def test_missing_engine_is_explained(builtin, monkeypatch):
    t, _ = builtin
    monkeypatch.setattr(llamacpp, "server_command", lambda: None)
    st = t.status()
    assert st["step"] == "engine" and "Ollama" in st["message"]


def test_translates_with_the_official_prompt_on_the_graphics_chip(builtin):
    t, log = builtin
    t.path.write_bytes(b"model")
    assert t.translate("Honey never spoils.", "en", "my") == "[Burmese] Honey never spoils."
    assert t.translate("same", "en", "en") == "same"
    entries = log_lines(log)
    launch = next(e["args"] for e in entries if "args" in e)
    prompt = next(e["prompt"] for e in entries if "prompt" in e)
    assert launch[launch.index("-ngl") + 1] == "99" and "--device" not in launch
    assert prompt.startswith("<start_of_turn>user\nYou are a professional English (en) to Burmese (my) translator.")
    assert prompt.endswith("<end_of_turn>\n<start_of_turn>model\n")
    assert llamacpp.SERVER.mode == "gpu" and "Fake GPU" in t.status()["message"]
    t.translate("again", "en", "my")
    assert len([e for e in log_lines(log) if "args" in e]) == 1          # the engine stays loaded


def test_processor_only_setting_and_gpu_failure_fall_back_to_the_processor(builtin, monkeypatch):
    t, log = builtin
    t.path.write_bytes(b"model")
    profile = config.profile_store.load()
    config.profile_store.save({**profile, "acceleration": "off"})
    assert t.translate("Hi", "en", "zh") == "[Chinese] Hi"
    assert llamacpp.SERVER.mode == "cpu"
    launch = [e["args"] for e in log_lines(log) if "args" in e][-1]
    assert launch[launch.index("-ngl") + 1] == "0" and launch[launch.index("--device") + 1] == "none"

    llamacpp.SERVER.stop()
    config.profile_store.save({**profile, "acceleration": "auto"})
    monkeypatch.setenv("FAKE_LLAMA_FAIL_GPU", "1")
    before = len([e for e in log_lines(log) if "args" in e])
    assert t.translate("Hi", "en", "zh") == "[Chinese] Hi"
    assert t.translate("Again", "en", "zh") == "[Chinese] Again"
    assert llamacpp.SERVER.mode == "cpu" and "processor" in t.status()["message"]
    assert len([e for e in log_lines(log) if "args" in e]) == before + 1     # no restart on every sentence


def test_engine_choice(builtin, monkeypatch):
    profile = config.profile_store.load()
    assert get_translator().id == "builtin"
    monkeypatch.setattr(llamacpp, "server_command", lambda: None)
    assert get_translator().id == "ollama"
    config.profile_store.save({**profile, "translation_engine": "builtin"})
    assert get_translator().id == "builtin"


class RangeFile(BaseHTTPRequestHandler):
    data = b""
    requests = []
    cut = 0             # when set, the first response stops after this many bytes

    def log_message(self, *a):
        pass

    def do_GET(self):
        rng = self.headers.get("Range")
        RangeFile.requests.append(rng)
        start = int(rng[6:].split("-")[0]) if rng else 0
        body = self.data[start:]
        self.send_response(206 if rng else 200)
        self.send_header("Content-Length", str(len(body)))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{len(self.data) - 1}/{len(self.data)}")
        self.end_headers()
        if RangeFile.cut:
            body, RangeFile.cut = body[:RangeFile.cut], 0
            self.wfile.write(body)
            self.close_connection = True
            return
        self.wfile.write(body)


@pytest.fixture()
def file_server():
    RangeFile.data = bytes(range(256)) * 4000
    RangeFile.requests = []
    RangeFile.cut = 0
    server = HTTPServer(("127.0.0.1", 0), RangeFile)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/model.gguf"
    server.shutdown()


def test_download_continues_a_partial_file_and_checks_it(tmp_path, file_server):
    data = RangeFile.data
    dest = tmp_path / "model.gguf"
    dest.with_name("model.gguf.part").write_bytes(data[:300_000])
    seen = []
    downloads.fetch_one(file_server, dest, len(data), hashlib.sha256(data).hexdigest(), lambda d, t: seen.append((d, t)))
    assert dest.read_bytes() == data and RangeFile.requests == ["bytes=300000-"]
    assert seen[-1] == (len(data), len(data))
    with pytest.raises(IOError, match="damaged"):
        downloads.fetch_one(file_server, tmp_path / "other.gguf", len(data), "0" * 64)
    assert not (tmp_path / "other.gguf").exists() and not (tmp_path / "other.gguf.part").exists()


def test_setup_downloads_the_model_and_notes_the_terms(builtin, monkeypatch, file_server):
    t, _ = builtin
    spec = t.spec
    monkeypatch.setattr(type(spec), "url", property(lambda self: file_server))
    steps = []
    t.setup(lambda pct, detail: steps.append(pct))
    assert t.installed() and steps[-1] == 100
    about = (t.path.parent / "ABOUT.txt").read_text(encoding="utf-8")
    assert "ai.google.dev/gemma/terms" in about and spec.repo in about


def test_download_that_ends_early_continues_instead_of_finishing(tmp_path, file_server, monkeypatch):
    monkeypatch.setattr(downloads.time, "sleep", lambda s: None)
    data = RangeFile.data
    RangeFile.cut = 400_000
    dest = tmp_path / "voice.onnx"
    downloads.fetch_one(file_server, dest)                   # size unknown to the caller
    assert dest.read_bytes() == data and RangeFile.requests == [None, "bytes=400000-"]


def test_engine_stops_when_idle_after_the_first_translation(builtin):
    t, _ = builtin
    t.path.write_bytes(b"model")
    t.translate("Hi", "en", "zh")
    assert llamacpp.SERVER.timer is not None and llamacpp.SERVER.timer.is_alive()


def test_graphics_failure_while_translating_moves_to_the_processor(builtin, monkeypatch):
    t, log = builtin
    t.path.write_bytes(b"model")
    monkeypatch.setenv("FAKE_LLAMA_FAIL_GPU_TRANSLATE", "1")
    monkeypatch.setattr(llamacpp.SERVER, "gpu_failed", False)
    assert t.translate("Hi", "en", "zh") == "[Chinese] Hi"
    assert llamacpp.SERVER.mode == "cpu" and llamacpp.SERVER.gpu_failed
    assert t.translate("Again", "en", "zh") == "[Chinese] Again"          # stays on the processor
    launches = [e["args"][e["args"].index("-ngl") + 1] for e in log_lines(log) if "args" in e]
    assert launches == ["99", "0"]                    # graphics chip first, then the processor, once
    assert [e["gpu"] for e in log_lines(log) if "gpu" in e] == [False, False]
    llamacpp.SERVER.gpu_failed = False


@pytest.mark.skipif(sys.platform == "win32", reason="the Windows job object is checked on Windows by the self-test")
def test_engine_ends_when_the_app_ends(tmp_path):
    import subprocess
    import time
    code = (
        "import sys, os; sys.path.insert(0, %r)\n"
        "from factopia_voice.translate import llamacpp\n"
        "p = llamacpp._spawn(['sleep', '61.25'], open(%r, 'ab'))\n"
        "print(p.pid, flush=True); os._exit(0)\n"
    ) % (str(Path(__file__).resolve().parent.parent), str(tmp_path / "log"))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    watcher = int(out.stdout.split()[0])

    def alive():
        listed = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
        return any("sleep 61.25" in line for line in listed.splitlines()), any(
            line.strip().startswith(f"{watcher} ") for line in listed.splitlines())

    deadline = time.time() + 15
    while time.time() < deadline and any(alive()):
        time.sleep(0.3)
    assert alive() == (False, False)
