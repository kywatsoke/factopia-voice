"""The clip history: every generated voiceover with the script that made it."""
import time
import uuid

from .config import OUTPUT, library_store

MAX_ITEMS = 500


def items():
    return [e for e in library_store.load() if (OUTPUT / e.get("file", "")).is_file()]


def add(entry):
    with library_store.lock:
        data = library_store.load()
        entry = {"id": uuid.uuid4().hex[:12], "created": time.strftime("%Y-%m-%d %H:%M"), **entry}
        data.insert(0, entry)
        library_store.save(data[:MAX_ITEMS])
    return entry


def delete(item_id):
    with library_store.lock:
        data = library_store.load()
        for e in data:
            if e.get("id") == item_id:
                f = OUTPUT / e.get("file", "")
                if f.is_file() and f.parent == OUTPUT:
                    f.unlink()
        library_store.save([e for e in data if e.get("id") != item_id])
