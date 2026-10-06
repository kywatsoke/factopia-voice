"""Test set-up: a throwaway data folder and a fake speech engine, so the suite
runs in seconds without downloading any model."""
import os
import socket
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="fv-test-")
_sock = socket.socket()
_sock.bind(("127.0.0.1", 0))
_port = _sock.getsockname()[1]
_sock.close()
os.environ["FACTOPIA_VOICE_DATA"] = _tmp
os.environ["FACTOPIA_VOICE_PORT"] = str(_port)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from factopia_voice import config
from factopia_voice.engines.base import Engine, Voice

RATE = 24000
SECONDS_PER_WORD = 0.4


class FakeEngine(Engine):
    """Speaks a steady tone: 0.4 s per word at speed 1.0, with silence at both ends."""
    id, name, license = "fake", "Fake", "test"
    loaded = True

    def __init__(self):
        self.spoken = []

    def files(self):
        return []

    def load(self, models_dir):
        pass

    def voices(self):
        return [Voice("am_michael", "Michael", "en-us", "English (US)", "male", "test voice")]

    def synthesize(self, text, voice_id, speed):
        self.spoken.append(text)
        n = int(RATE * SECONDS_PER_WORD * len(text.split()) / float(speed))
        tone = 0.3 * np.sin(np.linspace(0, 440 * 2 * np.pi * n / RATE, n, dtype="float32"))
        pad = np.zeros(RATE // 5, dtype="float32")
        return np.concatenate([pad, tone, pad]).astype("float32"), RATE


@pytest.fixture()
def clean_data():
    config.ensure_dirs()
    for store in (config.profile_store, config.dictionary_store, config.library_store):
        store.path.unlink(missing_ok=True)
    for f in config.OUTPUT.glob("*"):
        f.unlink()
    yield config


@pytest.fixture()
def studio(clean_data):
    from factopia_voice.pipeline import Studio
    s = Studio()
    s.engine = FakeEngine()
    s.status = {"phase": "ready", "percent": 100, "detail": ""}
    return s
