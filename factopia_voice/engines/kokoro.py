"""Kokoro-82M (Apache 2.0) through ONNX Runtime. CPU only, no GPU needed."""
from .base import Engine, ModelFile, Voice

_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
_LANGS = {
    "a": ("en-us", "English (US)"), "b": ("en-gb", "English (UK)"),
    "e": ("es", "Spanish"), "f": ("fr-fr", "French"), "h": ("hi", "Hindi"),
    "i": ("it", "Italian"), "j": ("ja", "Japanese"), "p": ("pt-br", "Portuguese (BR)"),
    "z": ("cmn", "Mandarin Chinese"),
}
_NOTES = {
    "am_michael": "Warm, steady narrator", "am_fenrir": "Deep and dramatic",
    "am_puck": "Upbeat and energetic", "am_onyx": "Low and serious",
    "af_heart": "Clear and friendly", "af_bella": "Lively", "af_nicole": "Soft, close-mic",
    "bm_george": "Documentary style", "bm_fable": "Storyteller", "bf_emma": "Polished",
}


class KokoroEngine(Engine):
    id = "kokoro"
    name = "Kokoro 82M"
    license = "Apache 2.0"

    def __init__(self):
        self._k = None
        self._voices = []

    def files(self):
        return [
            ModelFile("kokoro-v1.0.onnx", _BASE + "kokoro-v1.0.onnx", 325_532_387),
            ModelFile("voices-v1.0.bin", _BASE + "voices-v1.0.bin", 28_214_398),
        ]

    def load(self, models_dir):
        from kokoro_onnx import Kokoro
        self._k = Kokoro(str(models_dir / "kokoro-v1.0.onnx"), str(models_dir / "voices-v1.0.bin"))
        out = []
        for vid in sorted(self._k.get_voices()):
            lang = _LANGS.get(vid[0])
            if not lang or len(vid) < 4 or vid[2] != "_":
                continue
            out.append(Voice(vid, vid[3:].replace("_", " ").title(), lang[0], lang[1],
                             "female" if vid[1] == "f" else "male", _NOTES.get(vid, "")))
        self._voices = out
        self.loaded = True

    def voices(self):
        return list(self._voices)

    def synthesize(self, text, voice_id, speed):
        v = self.voice(voice_id)
        if v is None:
            raise ValueError(f"Unknown voice: {voice_id}")
        samples, rate = self._k.create(text, voice=voice_id, speed=float(speed), lang=v.language)
        return samples.astype("float32"), int(rate)
