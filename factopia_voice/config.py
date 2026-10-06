"""Paths and small JSON stores. Everything the app learns lives in the data folder,
so updating the program never touches the user's settings, dictionary or clips."""
import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("FACTOPIA_VOICE_DATA") or ROOT / "data")
MODELS = DATA / "models"
OUTPUT = DATA / "output"
CACHE = DATA / "cache"
WEB = Path(__file__).resolve().parent / "web"
PORT = int(os.environ.get("FACTOPIA_VOICE_PORT") or 8760)

DEFAULT_PROFILE = {
    "engine": "kokoro",
    "voice": "am_michael",
    "speed": 1.0,          # 0.8 - 1.3
    "pause": 0.35,         # seconds of silence at a blank line or [pause]
    "format": "mp3",       # mp3 | wav
    "max_seconds": 50,     # target ceiling shown in the editor
    "wps": 2.6,            # words per second at speed 1.0; recalibrated after each clip
}


def ensure_dirs():
    for d in (DATA, MODELS, OUTPUT, CACHE):
        d.mkdir(parents=True, exist_ok=True)


class JsonStore:
    """A JSON file with atomic writes and a lock."""

    def __init__(self, path, default):
        self.path = Path(path)
        self.default = default
        self.lock = threading.RLock()

    def load(self):
        with self.lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return json.loads(json.dumps(self.default))
            if isinstance(self.default, dict) and isinstance(data, dict):
                return {**self.default, **data}
            return data if isinstance(data, type(self.default)) else json.loads(json.dumps(self.default))

    def save(self, data):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
            return data


profile_store = JsonStore(DATA / "profile.json", DEFAULT_PROFILE)
dictionary_store = JsonStore(DATA / "dictionary.json", [])
library_store = JsonStore(DATA / "library.json", [])
