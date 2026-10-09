"""What the app is made of, for the About and licences screen. Keep in step
with THIRD_PARTY_LICENSES.md."""
import sys
from pathlib import Path

from .config import FROZEN, ROOT
from .translate.llamacpp import NOTICE, POLICY_URL, TERMS_URL

SOURCE_URL = "https://github.com/kywatsoke/factopia"

MODELS = [
    {"name": "Kokoro-82M", "role": "Voice", "licence": "Apache 2.0",
     "url": "https://huggingface.co/hexgrad/Kokoro-82M"},
    {"name": "Parakeet TDT 0.6B v2 by NVIDIA", "role": "Speech to text", "licence": "CC BY 4.0",
     "url": "https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2"},
    {"name": "TranslateGemma by Google", "role": "Translation", "licence": "Gemma Terms of Use",
     "url": TERMS_URL, "notice": NOTICE, "policy": POLICY_URL},
]

SOFTWARE = [
    ("kokoro-onnx", "Runs the voice", "MIT", "https://github.com/thewh1teagle/kokoro-onnx"),
    ("ONNX Runtime", "Runs the voice model", "MIT", "https://github.com/microsoft/onnxruntime"),
    ("phonemizer", "Pronunciation", "GPL-3.0-or-later", "https://github.com/bootphon/phonemizer"),
    ("eSpeak NG", "Pronunciation", "GPL-3.0-or-later", "https://github.com/espeak-ng/espeak-ng"),
    ("sherpa-onnx", "Runs speech to text", "Apache 2.0", "https://github.com/k2-fsa/sherpa-onnx"),
    ("llama.cpp", "Runs translation", "MIT", "https://github.com/ggml-org/llama.cpp"),
    ("FFmpeg", "Reads and writes video", "GPL (this build)", "https://ffmpeg.org"),
    ("FriBiDi", "Burmese text shaping", "LGPL-2.1-or-later", "https://github.com/fribidi/fribidi"),
    ("Pillow", "Draws captions", "MIT-CMU", "https://github.com/python-pillow/Pillow"),
    ("fontTools", "Checks fonts for letters", "MIT", "https://github.com/fonttools/fonttools"),
    ("NumPy", "Audio and video frames", "BSD-3-Clause", "https://numpy.org"),
    ("soundfile and libsndfile", "Audio files", "BSD-3-Clause, LGPL-2.1", "https://github.com/bastibe/python-soundfile"),
    ("pywebview", "The app window", "BSD-3-Clause", "https://github.com/r0x0r/pywebview"),
    ("Python", "Runtime", "PSF-2.0", "https://www.python.org"),
    ("PyInstaller", "Packs the app", "GPL-2.0 with bootloader exception", "https://pyinstaller.org"),
]


def licences_folder():
    if FROZEN:
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        for candidate in (base / "licenses", Path(sys.executable).resolve().parent.parent / "Resources" / "licenses"):
            if candidate.is_dir():
                return candidate
    return ROOT


def info():
    return {"models": MODELS,
            "software": [{"name": n, "role": r, "licence": lic, "url": u} for n, r, lic, u in SOFTWARE],
            "source": SOURCE_URL, "licences_folder": str(licences_folder())}
