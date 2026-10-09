import pytest
import soundfile as sf

from factopia_voice import library


def test_generate_writes_a_clip_and_a_library_entry(studio, clean_data):
    clip = studio.generate("Honey never spoils. It really does not.", fmt="wav")
    path = clean_data.OUTPUT / clip["file"]
    assert path.is_file() and clip["file"].startswith("honey-never-spoils")
    assert clip["words"] == 7 and clip["voice"] == "Michael" and clip["format"] == "wav"
    assert abs(sf.info(str(path)).duration - clip["seconds"]) < 0.06
    assert [c["id"] for c in library.items()] == [clip["id"]]


def test_pauses_have_exactly_the_requested_length(studio):
    plain = studio.generate("one two three four", fmt="wav", pause=0.5)
    paused = studio.generate("one two [pause 1.5] three four", fmt="wav", pause=0.5)
    blank = studio.generate("one two\n\nthree four", fmt="wav", pause=0.5)
    # each spoken part keeps a 0.04 s pad at both ends, so a split adds 0.08 s
    assert abs(paused["seconds"] - plain["seconds"] - 1.5 - 0.08) < 0.06
    assert abs(blank["seconds"] - plain["seconds"] - 0.5 - 0.08) < 0.06


def test_speed_changes_length(studio):
    slow = studio.generate("one two three four five six", fmt="wav", speed=0.8)
    fast = studio.generate("one two three four five six", fmt="wav", speed=1.3)
    assert slow["seconds"] > fast["seconds"] * 1.4


def test_dictionary_is_applied_before_speaking(studio, clean_data):
    clean_data.dictionary_store.save([{"word": "Qatar", "say": "KUH-tar"}])
    studio.generate("Qatar is small.", fmt="wav")
    assert studio.engine.spoken[-1] == "KUH-tar is small."


def test_settings_are_remembered_and_pace_is_learned(studio, clean_data):
    script = " ".join(["word"] * 20)
    studio.generate(script, speed=1.1, pause=0.2, fmt="wav")
    profile = clean_data.profile_store.load()
    assert (profile["speed"], profile["pause"], profile["format"]) == (1.1, 0.2, "wav")
    # the fake voice speaks 2.5 words a second; the estimate moves from 2.6 toward it
    assert 2.5 < profile["wps"] < 2.6


def test_out_of_range_settings_are_clamped(studio):
    clip = studio.generate("one two three", speed=9, pause=-4, fmt="ogg")
    assert clip["speed"] == 1.3 and clip["pause"] == 0.0 and clip["format"] == "mp3"


def test_empty_script_is_refused(studio):
    with pytest.raises(ValueError):
        studio.generate("  [pause]  ")


def test_translation_is_refused_until_translation_is_set_up(studio, monkeypatch):
    from factopia_voice.translate import ollama
    monkeypatch.setattr(ollama, "BASE", "http://127.0.0.1:9")
    with pytest.raises(ValueError, match="Set up translation"):
        studio.generate("hello there", target_language="my")


def test_not_ready_is_reported(studio):
    studio.status = {"phase": "loading", "percent": 0, "detail": ""}
    with pytest.raises(RuntimeError):
        studio.generate("hello")


def test_delete_removes_file_and_entry(studio, clean_data):
    clip = studio.generate("delete me please", fmt="wav")
    library.delete(clip["id"])
    assert not (clean_data.OUTPUT / clip["file"]).exists() and library.items() == []
