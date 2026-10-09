import json
import threading
import urllib.error
import urllib.request

import pytest

from conftest import FakeEngine
from factopia_voice import config


@pytest.fixture(scope="module")
def base():
    from factopia_voice import server
    config.ensure_dirs()
    server.studio.engine = FakeEngine()
    server.studio.status = {"phase": "ready", "percent": 100, "detail": ""}
    srv = server.make_server()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{config.PORT}"
    srv.shutdown()


def call(url, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def test_pages_and_state(base):
    assert call(base + "/")[0] == 200 and call(base + "/app.js")[0] == 200
    status, _, body = call(base + "/api/state")
    state = json.loads(body)
    assert status == 200 and state["status"]["phase"] == "ready" and state["voice"]["name"] == "Michael"


def test_generate_then_fetch_audio_with_ranges(base):
    status, _, body = call(base + "/api/generate", {"text": "one two three four five", "format": "wav"})
    clip = json.loads(body)
    assert status == 200
    url = base + "/audio/" + clip["file"]
    status, headers, data = call(url)
    assert status == 200 and headers["Content-Type"] == "audio/wav" and headers["Accept-Ranges"] == "bytes"
    status, headers, part = call(url, headers={"Range": "bytes=0-99"})
    assert status == 206 and len(part) == 100 and headers["Content-Range"] == f"bytes 0-99/{len(data)}"
    assert call(url, headers={"Range": f"bytes={len(data) + 5}-"})[0] == 416
    assert "attachment" in call(url + "?download=1")[1]["Content-Disposition"]


def test_bad_input_gives_a_clear_error(base):
    status, _, body = call(base + "/api/generate", {"text": "   "})
    assert status == 400 and "script" in json.loads(body)["error"]


def test_requests_from_other_sites_are_refused(base):
    assert call(base + "/api/generate", {"text": "hi"}, {"Origin": "http://evil.example"})[0] == 403
    assert call(base + "/api/state", headers={"Host": "evil.example"})[0] == 403


def test_files_outside_the_output_folder_are_not_served(base):
    config.profile_store.save(config.profile_store.load())
    assert call(base + "/audio/..%2Fprofile.json")[0] == 404
    assert call(base + "/audio/..%2F..%2Frequirements.txt")[0] == 404
    assert call(base + "/nothing-here")[0] == 404


def test_dictionary_is_cleaned(base):
    entries = [{"word": "Qatar", "say": "KUH-tar"}, {"word": "qatar", "say": "dup"}, {"word": "", "say": "x"}]
    _, _, body = call(base + "/api/dictionary", {"entries": entries})
    assert json.loads(body) == [{"word": "Qatar", "say": "KUH-tar"}]
    call(base + "/api/dictionary", {"entries": []})
