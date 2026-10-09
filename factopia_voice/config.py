"""Paths and small JSON stores.

Where things live depends on how the app runs:

- Installed (the .dmg or Setup.exe): settings, projects and downloaded models
  go in the per-user app folder (Application Support on a Mac, AppData\\Local
  on Windows); the files people make go in Documents/Factopia Voice.
- From source (the launchers): everything stays in data/ next to the code,
  as in 2.x.
- FACTOPIA_VOICE_DATA overrides both (tests use it).

Updating the program never touches any of these folders."""
import json
import os
import sys
import threading
from pathlib import Path

APP_NAME = "Factopia Voice"
FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(__file__).resolve().parent.parent
WEB = Path(__file__).resolve().parent / "web"
PORT = int(os.environ.get("FACTOPIA_VOICE_PORT") or 8760)


def user_data_dir():
    """The per-user folder for settings, projects and models."""
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local") / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share") / "factopia-voice"


def documents_dir():
    """The user's Documents folder, including when Windows moves it (for example into OneDrive)."""
    if sys.platform == "win32":
        try:
            import ctypes
            import uuid
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                            ("Data4", ctypes.c_ubyte * 8)]

            u = uuid.UUID("FDD39AD0-238F-46AF-ADB4-6C85480369C7")       # FOLDERID_Documents
            guid = GUID(u.fields[0], u.fields[1], u.fields[2], (ctypes.c_ubyte * 8).from_buffer_copy(u.bytes[8:]))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) == 0:
                path = out.value
                ctypes.windll.ole32.CoTaskMemFree(out)
                if path:
                    return Path(path)
        except Exception:
            pass
    docs = Path.home() / "Documents"
    return docs if docs.is_dir() or sys.platform in ("darwin", "win32") else Path.home()


def _locate():
    custom = os.environ.get("FACTOPIA_VOICE_DATA")
    if custom:
        return Path(custom), Path(custom) / "output", "custom"
    if FROZEN:
        return user_data_dir(), documents_dir() / APP_NAME, "installed"
    return ROOT / "data", ROOT / "data" / "output", "portable"


DATA, OUTPUT, LAYOUT = _locate()
LOCATIONS = DATA / "locations.json"          # where the models were moved to, if they were


def _models_dir():
    try:
        moved = json.loads(LOCATIONS.read_text(encoding="utf-8")).get("models")
        if moved:
            return Path(moved)
    except (OSError, ValueError, AttributeError):
        pass
    return DATA / "models"


MODELS = _models_dir()
CACHE = DATA / "cache"
PROJECTS = DATA / "projects"
LOGS = DATA / "logs"

DEFAULT_PROFILE = {
    "engine": "kokoro",
    "voice": "am_michael",
    "speed": 1.0,          # 0.8 - 1.3
    "pause": 0.35,         # seconds of silence at a blank line or [pause]
    "format": "mp3",       # mp3 | wav
    "max_seconds": 50,     # target ceiling shown in the editor
    "wps": 2.6,            # words per second at speed 1.0; recalibrated after each clip
    "translation_quality": "standard",   # standard (TranslateGemma 4B) | high (12B)
    "translation_engine": "auto",        # auto | builtin | ollama
    "acceleration": "auto",              # auto | off (processor only)
    "check_updates": True,
    "terms_accepted": "",                # date the model terms were agreed on the welcome screen
}


def ensure_dirs():
    for d in (DATA, MODELS, OUTPUT, CACHE, PROJECTS):
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
