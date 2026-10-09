"""Download the voice and speech models into one folder, for the installer
self-test (the workflow caches the folder between runs).

    python packaging/fetch_test_models.py <folder>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from factopia_voice.downloads import fetch  # noqa: E402
from factopia_voice.engines.kokoro import KokoroEngine  # noqa: E402
from factopia_voice.listeners.parakeet import ParakeetListener  # noqa: E402


def main():
    folder = Path(sys.argv[1]).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    fetch(KokoroEngine().files(), folder)
    ParakeetListener().install(folder, lambda pct, detail=None: None)
    print("Test models ready in", folder, sorted(p.name for p in folder.iterdir()))


if __name__ == "__main__":
    main()
