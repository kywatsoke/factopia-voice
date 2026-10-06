import numpy as np
import soundfile as sf

from factopia_voice import audio


def test_trim_removes_dead_air_but_keeps_a_small_pad():
    rate = 24000
    clip = np.concatenate([np.zeros(rate), np.full(rate, 0.5), np.zeros(rate)]).astype("float32")
    out = audio.trim(clip, rate)
    assert abs(len(out) / rate - 1.08) < 0.01


def test_trim_leaves_pure_silence_alone():
    quiet = np.zeros(1000, dtype="float32")
    assert len(audio.trim(quiet, 24000)) == 1000


def test_normalize_sets_the_peak():
    out = audio.normalize(np.array([0.1, -0.2, 0.05], dtype="float32"))
    assert abs(float(np.abs(out).max()) - 0.89) < 1e-6
    assert float(np.abs(audio.normalize(np.zeros(4, dtype="float32"))).max()) == 0.0


def test_save_wav_and_mp3(tmp_path):
    rate = 24000
    tone = (0.3 * np.sin(np.linspace(0, 2000, rate * 2))).astype("float32")
    for fmt in ("wav", "mp3"):
        path = tmp_path / f"clip.{fmt}"
        audio.save(path, tone, rate, fmt)
        info = sf.info(str(path))
        assert info.samplerate == rate and abs(info.duration - 2.0) < 0.1
        assert info.format == ("WAV" if fmt == "wav" else "MP3")
