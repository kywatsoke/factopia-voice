"""Speech recognition inside a helper process (see workers.py).

    <app> --fv-worker listen <listener> <models_dir> <wav> <out.json>
"""
import json
from pathlib import Path

from . import create_listener


def run(listener_id, models_dir, wav, out):
    out = Path(out)
    progress = Path(str(out) + ".progress")

    def report(pct, detail=None):
        progress.write_text(str(int(pct)), encoding="utf-8")

    words = create_listener(listener_id).transcribe(Path(wav), Path(models_dir), report)
    out.write_text(json.dumps(words), encoding="utf-8")
