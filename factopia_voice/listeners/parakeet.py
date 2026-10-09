"""NVIDIA Parakeet TDT 0.6B v2 (CC BY 4.0) through sherpa-onnx (Apache 2.0).
English only. Chosen in the 2.1 spike: fastest, most accurate, word timings."""
import shutil
import tarfile

from ..downloads import fetch
from ..engines.base import ModelFile
from .base import Listener

FOLDER = "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
ARCHIVE = ModelFile(FOLDER + ".tar.bz2",
                    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/" + FOLDER + ".tar.bz2",
                    482_468_385)
PARTS = ("encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt")
CHUNK_SECONDS = 60


class ParakeetListener(Listener):
    id = "parakeet"
    name = "Parakeet TDT 0.6B v2"
    license = "CC BY 4.0"
    languages = ("en",)

    def ready(self, models_dir):
        return all((models_dir / FOLDER / p).is_file() for p in PARTS)

    def install(self, models_dir, on_progress):
        if self.ready(models_dir):
            return
        fetch([ARCHIVE], models_dir,
              lambda done, total, name: on_progress(min(95, int(done * 95 / max(total, 1))),
                                                    f"Downloading the speech model: {done >> 20} of {total >> 20} MB"))
        on_progress(96, "Unpacking the speech model")
        archive = models_dir / ARCHIVE.name
        shutil.rmtree(models_dir / FOLDER, ignore_errors=True)
        with tarfile.open(archive, "r:bz2") as tar:
            wanted = [m for m in tar.getmembers() if m.isfile() and m.name.split("/")[-1] in PARTS
                      and m.name.startswith(FOLDER + "/")]
            tar.extractall(models_dir, members=wanted, filter="data")
        archive.unlink(missing_ok=True)
        if not self.ready(models_dir):
            raise IOError("The speech model did not unpack correctly. Start the captions again to retry.")

    def transcribe(self, wav_path, models_dir, on_progress):
        import numpy as np
        import sherpa_onnx
        import soundfile as sf

        from ..captions import words_from_tokens
        base = models_dir / FOLDER
        recogniser = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(base / PARTS[0]), decoder=str(base / PARTS[1]), joiner=str(base / PARTS[2]),
            tokens=str(base / PARTS[3]), num_threads=4, model_type="nemo_transducer")
        samples, rate = sf.read(str(wav_path), dtype="float32", always_2d=False)
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        words, position, total = [], 0, len(samples)
        while position < total:
            end = min(total, position + CHUNK_SECONDS * rate)
            if end < total:                       # cut at the quietest moment near the boundary
                lo, win = max(position + rate, end - 5 * rate), rate // 5
                energy = [float(np.abs(samples[i:i + win]).mean()) for i in range(lo, end, win)]
                end = lo + int(np.argmin(energy)) * win + win // 2
            stream = recogniser.create_stream()
            stream.accept_waveform(rate, samples[position:end])
            recogniser.decode_stream(stream)
            words += words_from_tokens(list(stream.result.tokens), list(stream.result.timestamps), position / rate)
            position = end
            on_progress(int(position * 100 / total), "Listening")
        return words
