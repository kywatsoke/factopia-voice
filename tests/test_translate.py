"""Translation: the Ollama client against a stand-in Ollama server, and the
captions/text flows with a fake translator (no model download needed)."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from factopia_voice.translate import ollama


class FakeOllama(BaseHTTPRequestHandler):
    models = ["gemma3:4b"]
    prompts = []

    def log_message(self, *a):
        pass

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/tags":
            return self._json({"models": [{"name": m} for m in FakeOllama.models]})
        self.send_error(404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/pull":
            self.send_response(200)
            self.end_headers()
            for done in (0, 50, 100):
                self.wfile.write((json.dumps({"status": "pulling", "total": 100, "completed": done}) + "\n").encode())
            FakeOllama.models.append(body["model"] + ":latest" if ":" not in body["model"] else body["model"])
            self.wfile.write(b'{"status":"success"}\n')
            return
        if self.path == "/api/chat":
            prompt = body["messages"][0]["content"]
            FakeOllama.prompts.append(prompt)
            text = prompt.split("\n\n\n", 1)[1]
            return self._json({"message": {"role": "assistant", "content": f"“[{body['model']}] {text}”\n"}})
        self.send_error(404)


@pytest.fixture()
def fake_ollama(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(ollama, "BASE", f"http://127.0.0.1:{srv.server_address[1]}")
    FakeOllama.models[:] = ["gemma3:4b"]
    FakeOllama.prompts.clear()
    yield FakeOllama
    srv.shutdown()


def test_status_when_ollama_is_missing(monkeypatch):
    monkeypatch.setattr(ollama, "BASE", "http://127.0.0.1:9")
    monkeypatch.setattr(ollama, "find_ollama", lambda: None)
    st = ollama.OllamaTranslator().status()
    assert st["ready"] is False and st["step"] == "install" and "ollama.com" in st["message"]


def test_setup_downloads_the_model_then_translates_with_the_official_prompt(fake_ollama):
    t = ollama.OllamaTranslator("standard")
    assert t.status()["step"] == "download"
    seen = []
    t.setup(lambda pct, detail=None: seen.append(pct))
    assert t.status()["ready"] and max(p for p in seen if p is not None) == 100
    out = t.translate("Honey never spoils.", "en", "zh")
    assert out == "[translategemma:4b] Honey never spoils."            # quotes and trailing newline removed
    prompt = fake_ollama.prompts[-1]
    assert prompt.startswith("You are a professional English (en) to Chinese (zh-Hans) translator.")
    assert prompt.endswith("Please translate the following English text into Chinese:\n\n\nHoney never spoils.")
    assert t.translate("same", "en", "en") == "same" and len(fake_ollama.prompts) == 1


def test_high_quality_uses_the_larger_model(fake_ollama):
    fake_ollama.models.append("translategemma:12b")
    t = ollama.OllamaTranslator("high")
    assert t.status()["ready"] and t.translate("你好", "zh", "en").startswith("[translategemma:12b]")
    assert "Chinese (zh-Hans) to English (en)" in fake_ollama.prompts[-1]


# ---- flows with a fake translator -------------------------------------------
class FakeTranslator:
    def status(self):
        return {"ready": True, "step": "ready", "message": "ok"}

    def translate_many(self, texts, source, target, on_progress=lambda d, n: None):
        table = {"my": "ပျားရည်သည် ဘယ်တော့မှ မပုပ်ပါ။", "zh": "蜂蜜永远不会变质，考古学家在古墓里发现了三千年前的蜂蜜。", "en": "Honey never spoils."}
        out = []
        for i, t in enumerate(texts):
            out.append(table[target])
            on_progress(i + 1, len(texts))
        return out


def wait(job):
    for _ in range(200):
        if job["done"]:
            break
        time.sleep(0.05)
    assert job["error"] is None, job["error"]
    return job["result"]


def test_caption_translation_makes_a_new_project(clean_data, monkeypatch):
    from factopia_voice import projects
    monkeypatch.setattr(projects, "get_translator", lambda: FakeTranslator())
    srt = "1\n00:00:00,000 --> 00:00:01,000\nHoney never\n\n2\n00:00:01,000 --> 00:00:02,000\nspoils.\n\n3\n00:00:03,000 --> 00:00:05,000\nArchaeologists found honey.\n"
    original = projects.import_srt(srt, "honey.srt")
    assert original["language"] == "en" and len(original["lines"]) == 3 and original["has_video"] is False
    with pytest.raises(ValueError):
        projects.start_translate(original["id"], "en")
    result = wait(projects.start_translate(original["id"], "zh"))
    copy = projects.load(result["id"])
    assert result["sentences"] == 2 and copy["language"] == "zh" and copy["translated_from"] == original["id"]
    assert copy["name"] == "honey (Chinese)" and copy["style"]["uppercase"] is False
    assert copy["lines"][0]["start"] == 0.0 and copy["lines"][-1]["end"] == 5.0
    assert all(len(l["text"]) <= 20 for l in copy["lines"])
    assert projects.load(original["id"])["lines"] == original["lines"]          # original untouched


def test_text_translation_detects_the_source(clean_data, monkeypatch):
    from factopia_voice import projects
    monkeypatch.setattr(projects, "get_translator", lambda: FakeTranslator())
    result = wait(projects.start_translate_text("蜂蜜永远不会变质。\n\n第二段。", "auto", "en"))
    assert result == {"text": "Honey never spoils.\n\nHoney never spoils.", "source": "zh", "target": "en"}


def test_projects_from_2_1_open_as_english(clean_data):
    import json
    from factopia_voice import projects
    p = projects.import_srt("1\n00:00:00,000 --> 00:00:01,000\nHi\n", "old.srt")
    path = projects._folder(p["id"]) / "project.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["language"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert projects.load(p["id"])["language"] == "en"
    assert projects.update(p["id"], lines=[{"start": 0, "end": 1, "text": "Hi there"}])["language"] == "en"


def test_burmese_is_not_translated(clean_data, monkeypatch):
    from factopia_voice import languages, projects
    monkeypatch.setattr(projects, "get_translator", lambda: FakeTranslator())
    with pytest.raises(ValueError, match="English and Chinese"):
        projects.start_translate_text("ပျားရည်သည် ဘယ်တော့မှ မပုပ်ပါ။", "auto", "en")
    with pytest.raises(ValueError, match="English and Chinese"):
        projects.start_translate_text("Honey never spoils.", "en", "my")
    srt = "1\n00:00:00,000 --> 00:00:01,000\nပျားရည်သည် ဘယ်တော့မှ မပုပ်ပါ။\n"
    burmese = projects.import_srt(srt, "honey-my.srt")              # Burmese captions still work
    assert burmese["language"] == "my"
    with pytest.raises(ValueError, match="English and Chinese"):
        projects.start_translate(burmese["id"], "en")
    assert languages.TRANSLATION == ("en", "zh")
