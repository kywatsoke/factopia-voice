import json
import shutil
import time

from factopia_voice import config, storage


def wait(job):
    deadline = time.time() + 30
    while not job["done"] and time.time() < deadline:
        time.sleep(0.05)
    assert job["done"] and not job["error"], job["error"]
    return job["result"]


def test_bringing_in_earlier_work_keeps_newer_files(clean_data, tmp_path):
    old = tmp_path / "FactopiaVoice-2.2" / "data"
    (old / "output").mkdir(parents=True)
    (old / "projects" / "abc").mkdir(parents=True)
    (old / "output" / "clip.mp3").write_bytes(b"old clip")
    (old / "output" / "only-old.mp3").write_bytes(b"x")
    (old / "projects" / "abc" / "project.json").write_text('{"name": "old"}', encoding="utf-8")
    (old / "profile.json").write_text(json.dumps({"speed": 1.1}), encoding="utf-8")
    (old / "dictionary.json").write_text(json.dumps([{"word": "Qatar", "say": "KUH-tar"}]), encoding="utf-8")

    config.OUTPUT.mkdir(parents=True, exist_ok=True)
    (config.OUTPUT / "clip.mp3").write_bytes(b"newer clip, edited")
    (config.PROJECTS / "abc").mkdir(parents=True, exist_ok=True)
    (config.PROJECTS / "abc" / "project.json").write_text('{"name": "edited since"}', encoding="utf-8")

    result = wait(storage.start_import(old.parent))           # the app folder is accepted too
    assert result["words"] == 1
    assert (config.OUTPUT / "clip.mp3").read_bytes() == b"newer clip, edited"
    assert (config.OUTPUT / "only-old.mp3").read_bytes() == b"x"
    assert "edited since" in (config.PROJECTS / "abc" / "project.json").read_text(encoding="utf-8")
    assert config.profile_store.load()["speed"] == 1.1
    wait(storage.start_import(old))                            # a second import changes nothing
    assert len([w for w in config.dictionary_store.load() if w["word"] == "Qatar"]) == 1
    shutil.rmtree(config.PROJECTS / "abc")
