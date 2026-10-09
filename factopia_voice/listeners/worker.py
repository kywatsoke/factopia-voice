"""Runs speech recognition in its own process, so its memory (about 1 GB) is
returned when it finishes and its runtime never clashes with the voice engine's.

    python -m factopia_voice.listeners.worker <listener> <models_dir> <wav> <out.json>
"""
import json
import sys
from pathlib import Path

from . import create_listener


def main():
    listener_id, models_dir, wav, out = sys.argv[1:5]
    words = create_listener(listener_id).transcribe(
        Path(wav), Path(models_dir), lambda pct, detail: print(f"P {pct}", flush=True))
    Path(out).write_text(json.dumps(words), encoding="utf-8")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
