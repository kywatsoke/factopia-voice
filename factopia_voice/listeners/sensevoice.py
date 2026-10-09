"""SenseVoice Small by Alibaba's FunAudioLLM team (FunASR Model Licence 1.1)
through sherpa-onnx (Apache 2.0). Chinese: Mandarin, and Cantonese too.
Chosen in the 3.0 spike (docs/DECISIONS.md): on a Mac processor it read the
test Chinese about ten times faster than real time with 1-2% of characters
wrong, writes Simplified Chinese with punctuation and numbers, and gives a
time for every character. Whisper large-v3-turbo was as accurate but about
ten times slower; the September 2025 SenseVoice update has no punctuation.

SenseVoice reads one utterance at a time: given half a minute with several
sentences and pauses it skips some of them. So the Silero voice activity
detector (MIT) first finds each stretch of speech, and each is read alone."""
from ..downloads import fetch
from ..engines.base import ModelFile
from .base import Listener, install_archive, read_mono

FOLDER = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
ARCHIVE = ModelFile(FOLDER + ".tar.bz2",
                    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/" + FOLDER + ".tar.bz2",
                    163_002_883, "7d1efa2138a65b0b488df37f8b89e3d91a60676e416f515b952358d83dfd347e")
PARTS = ("model.int8.onnx", "tokens.txt", "LICENSE")
VAD = ModelFile("silero_vad.onnx", "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx",
                643_854, "9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6")
PAD = (0.25, 0.15)            # seconds of sound kept before and after each stretch of speech


class SenseVoiceListener(Listener):
    id = "sensevoice"
    name = "SenseVoice Small"
    license = "FunASR Model Licence 1.1"
    languages = ("zh",)
    size_mb = 160

    def ready(self, models_dir):
        return all((models_dir / FOLDER / p).is_file() for p in PARTS + (VAD.name,))

    def install(self, models_dir, on_progress):
        if self.ready(models_dir):
            return
        if not all((models_dir / FOLDER / p).is_file() for p in PARTS):
            install_archive(models_dir, ARCHIVE, FOLDER, PARTS, on_progress)
        on_progress(98, "Downloading the speech detector")
        fetch([VAD], models_dir / FOLDER)

    def transcribe(self, wav_path, models_dir, on_progress):
        import sherpa_onnx

        from ..captions import words_from_tokens
        base = models_dir / FOLDER
        recogniser = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(base / PARTS[0]), tokens=str(base / PARTS[1]), language="zh", use_itn=True, num_threads=4)
        samples, rate = read_mono(wav_path)
        if rate != 16000:
            raise ValueError("SenseVoice needs 16 kHz sound.")
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(base / VAD.name)
        config.silero_vad.threshold = 0.4
        config.silero_vad.min_silence_duration = 0.3
        config.silero_vad.min_speech_duration = 0.2
        config.silero_vad.max_speech_duration = 20
        config.sample_rate = rate
        vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)
        window, total, words = config.silero_vad.window_size, len(samples), []

        def read_speech():
            while not vad.empty():
                segment = vad.front
                start = max(0, segment.start - int(PAD[0] * rate))
                end = min(total, segment.start + len(segment.samples) + int(PAD[1] * rate))
                vad.pop()
                stream = recogniser.create_stream()
                stream.accept_waveform(rate, samples[start:end])
                recogniser.decode_stream(stream)
                words.extend(words_from_tokens(list(stream.result.tokens), list(stream.result.timestamps), start / rate))

        for i in range(0, total, window):
            vad.accept_waveform(samples[i:i + window])
            read_speech()
            if i % (rate * 10) < window:
                on_progress(int(i * 100 / total), "Listening")
        vad.flush()
        read_speech()
        on_progress(100, "Listening")
        return sorted(words, key=lambda w: w["start"])
