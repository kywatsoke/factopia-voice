"""Download the voice and speech models into one folder, for the installer
self-test (the workflow caches the folder between runs). Also keeps the
Chinese recording that comes with SenseVoice as zh-test.wav.

    python packaging/fetch_test_models.py <folder>
"""
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from factopia_voice.downloads import fetch  # noqa: E402
from factopia_voice.engines.kokoro import KokoroEngine  # noqa: E402
from factopia_voice.listeners import sensevoice  # noqa: E402
from factopia_voice.listeners.parakeet import ParakeetListener  # noqa: E402


def main():
    folder = Path(sys.argv[1]).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    fetch(KokoroEngine().files(), folder)
    ParakeetListener().install(folder, lambda pct, detail=None: None)
    listener = sensevoice.SenseVoiceListener()
    if not listener.ready(folder) or not (folder / "zh-test.wav").is_file():
        fetch([sensevoice.ARCHIVE], folder)          # install() below unpacks it and removes it
        with tarfile.open(folder / sensevoice.ARCHIVE.name, "r:bz2") as tar:
            member = tar.getmember(sensevoice.FOLDER + "/test_wavs/zh.wav")
            (folder / "zh-test.wav").write_bytes(tar.extractfile(member).read())
        (folder / sensevoice.FOLDER / "tokens.txt").unlink(missing_ok=True)   # make install() unpack again
    listener.install(folder, lambda pct, detail=None: None)
    print("Test models ready in", folder, sorted(p.name for p in folder.iterdir()))


if __name__ == "__main__":
    main()
