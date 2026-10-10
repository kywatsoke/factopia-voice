"""NVIDIA Parakeet TDT 0.6B v2 (CC BY 4.0) through sherpa-onnx (Apache 2.0).
English only. Chosen in the 2.1 spike: fastest, most accurate, word timings."""
from ..engines.base import ModelFile
from .base import Listener, install_archive, pieces, read_mono

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
    size_mb = 480

    def ready(self, models_dir):
        return all((models_dir / FOLDER / p).is_file() for p in PARTS)

    def install(self, models_dir, on_progress):
        if not self.ready(models_dir):
            install_archive(models_dir, ARCHIVE, FOLDER, PARTS, on_progress)

    def transcribe(self, wav_path, models_dir, on_progress):
        import sherpa_onnx

        from ..captions import words_from_tokens
        base = models_dir / FOLDER
        recogniser = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(base / PARTS[0]), decoder=str(base / PARTS[1]), joiner=str(base / PARTS[2]),
            tokens=str(base / PARTS[3]), num_threads=4, model_type="nemo_transducer")
        samples, rate = read_mono(wav_path)
        words = []
        for start, end in pieces(samples, rate, CHUNK_SECONDS):
            stream = recogniser.create_stream()
            stream.accept_waveform(rate, samples[start:end])
            recogniser.decode_stream(stream)
            words += words_from_tokens(list(stream.result.tokens), list(stream.result.timestamps), start / rate)
            on_progress(int(end * 100 / len(samples)), "Listening")
        return words
