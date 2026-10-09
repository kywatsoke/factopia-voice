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
    assert llamacpp.SERVER.mode == "gpu" and "graphics chip" in t.status()["message"]


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
    assert t.translate("Hi", "en", "zh") == "[Chinese] Hi"
    assert llamacpp.SERVER.mode == "cpu"


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

    def log_message(self, *a):
        pass

    def do_GET(self):
        rng = self.headers.get("Range")
        RangeFile.requests.append(rng)
        start = int(rng[6:].split("-")[0]) if rng else 0
        body = self.data[start:]
        self.send_response(206 if rng else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def file_server():
    RangeFile.data = bytes(range(256)) * 4000
    RangeFile.requests = []
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
