"""The contract for a speech-to-text engine, and the parts every engine
shares: unpacking a downloaded model archive and cutting a long recording
into pieces at quiet moments."""
import shutil
import tarfile
from abc import ABC, abstractmethod

from ..downloads import fetch


class Listener(ABC):
    id = ""
    name = ""
    license = ""
    languages = ()
    size_mb = 0

    @abstractmethod
    def ready(self, models_dir):
        """True when the model files are on disk."""

    @abstractmethod
    def install(self, models_dir, on_progress):
        """Download the model files. on_progress(percent, detail)."""

    @abstractmethod
    def transcribe(self, wav_path, models_dir, on_progress):
        """Return [{"text", "start"}] words with start times in seconds."""


def install_archive(models_dir, archive, folder, parts, on_progress):
    """Download a .tar.bz2 model archive and keep only the files in parts."""
    fetch([archive], models_dir,
          lambda done, total, name: on_progress(min(95, int(done * 95 / max(total, 1))),
                                                f"Downloading the speech model: {done >> 20} of {total >> 20} MB"))
    on_progress(96, "Unpacking the speech model")
    path = models_dir / archive.name
    shutil.rmtree(models_dir / folder, ignore_errors=True)
    with tarfile.open(path, "r:bz2") as tar:
        wanted = [m for m in tar.getmembers() if m.isfile() and m.name.split("/")[-1] in parts
                  and m.name.startswith(folder + "/")]
        tar.extractall(models_dir, members=wanted, filter="data")
    path.unlink(missing_ok=True)
    if not all((models_dir / folder / p).is_file() for p in parts):
        raise IOError("The speech model did not unpack correctly. Start the captions again to retry.")


def read_mono(wav_path):
    import soundfile as sf
    samples, rate = sf.read(str(wav_path), dtype="float32", always_2d=False)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return samples, rate


def pieces(samples, rate, seconds):
    """(start, end) sample ranges of about the given length, each cut at the
    quietest moment in the last five seconds so no word is split."""
    import numpy as np
    position, total = 0, len(samples)
    while position < total:
        end = min(total, position + int(seconds * rate))
        if end < total:
            lo, win = max(position + rate, end - 5 * rate), rate // 5
            energy = [float(np.abs(samples[i:i + win]).mean()) for i in range(lo, end, win)]
            end = lo + int(np.argmin(energy)) * win + win // 2
        yield position, end
        position = end
