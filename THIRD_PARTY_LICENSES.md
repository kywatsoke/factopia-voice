# Third-party licence register

Everything Factopia Voice downloads, installs or bundles, and what each
licence means for the project. Update this file whenever a dependency or
model is added or changed. Checked 7 October 2026; installer parts added
9 October 2026 (3.0); Chinese speech to text added 9 October 2026.

| Component | Role | Licence | Personal use | Distribute in a paid closed-source app |
| --- | --- | --- | --- | --- |
| Kokoro-82M model and voices | Speech model | Apache 2.0 | Yes | Yes, with notice |
| kokoro-onnx 0.6.1 | Runs the model | MIT | Yes | Yes, with notice |
| ONNX Runtime | Inference engine | MIT | Yes | Yes, with notice |
| NumPy | Arrays | BSD-3-Clause | Yes | Yes, with notice |
| soundfile | Audio file writing | BSD-3-Clause | Yes | Yes, with notice |
| libsndfile (inside soundfile) | Audio codecs | LGPL-2.1 | Yes | Yes, if kept as a replaceable library |
| phonemizer 3.4 | Text to phonemes | GPL-3.0-or-later | Yes | **No**, unless the whole app is released under the GPL |
| espeak-ng (via espeakng-loader) | Pronunciation engine behind phonemizer | GPL-3.0-or-later | Yes | **No**, same condition |
| Parakeet TDT 0.6B v2 model | English speech to text (2.1) | CC BY 4.0 | Yes | Yes, with attribution to NVIDIA |
| SenseVoice Small model (sherpa-onnx int8 conversion, 2024-07-17) | Chinese speech to text (3.0) | FunASR Model Open Source Licence 1.1 (Alibaba) | Yes | Not bundled: downloaded from the sherpa-onnx releases when first needed. The licence lets anyone use, copy, modify and share it, provided the source, author and model name are credited (the About screen does); it says the model is "provided for reference and learning purposes only" and gives no warranty. Check again before any commercial use |
| Silero VAD (silero_vad.onnx) | Finds the stretches of speech SenseVoice reads (3.0) | MIT | Yes | Yes, with notice |
| sherpa-onnx | Runs the speech-to-text models | Apache 2.0 | Yes | Yes, with notice |
| Pillow | Draws captions | MIT-CMU | Yes | Yes, with notice |
| imageio-ffmpeg | Locates the bundled ffmpeg | BSD-2-Clause | Yes | Yes, with notice |
| ffmpeg binary (inside imageio-ffmpeg) | Reads and writes video | GPL build (includes x264) | Yes | **Check before 3.0**: ship an LGPL build or meet the GPL's terms |
| TranslateGemma 4B / 12B models | Translation (2.2) | Gemma Terms of Use | Yes | Not bundled: the app downloads the GGUF conversion from the public mirror `mradermacher/translategemma-*-GGUF` on Hugging Face after the user agrees to the terms; Google claims no rights in outputs; Prohibited Use Policy applies |
| llama.cpp (llama-server) | Runs the translation model inside the app (3.0) | MIT | Yes | Yes, with notice |
| FriBiDi | Text shaping for Burmese on Mac and Windows (3.0) | LGPL-2.1-or-later | Yes | Yes, as a separate replaceable library (it is), with its source available |
| pywebview | The app window (3.0) | BSD-3-Clause | Yes | Yes, with notice |
| truststore | Checks downloads against the system's trusted certificates (3.0) | MIT | Yes | Yes, with notice |
| certifi | Fallback certificate list for downloads (3.0) | MPL-2.0 | Yes | Yes, unchanged, with notice |
| pythonnet, clr-loader (Windows) | Lets pywebview use WebView2 | MIT | Yes | Yes, with notice |
| PyObjC (Mac) | Lets pywebview use the Mac's WebKit | MIT | Yes | Yes, with notice |
| Microsoft Edge WebView2 Runtime (Windows) | Shows the window's contents | Microsoft software licence | Yes | Not bundled: the installer runs Microsoft's own bootstrapper when it is missing |
| PyInstaller bootloader | Starts the packed app | GPL-2.0 with a bootloader exception | Yes | Yes: the exception allows any licence for the packed app |
| Inno Setup | Makes the Windows installer | Inno Setup licence (free, modified BSD style) | Yes | Yes |
| Ollama | Runs the translation model (separate app the user installs) | MIT | Yes | Not bundled |
| fontTools | Checks which letters a font has | MIT | Yes | Yes, with notice |
| uv | Sets up Python on first start | Apache 2.0 or MIT | Yes | Not bundled |
| Python 3.12 | Runtime | PSF-2.0 | Yes | Yes |

## What this means

- **Using the app yourself, and publishing the audio it makes, is unaffected.**
  These licences cover the software, not the voiceovers.
- **Factopia Voice itself is free software under GPL-3.0-or-later** (decided
  9 October 2026), with its source public on GitHub. That fits the GPL parts
  it uses (phonemizer, espeak-ng, the GPL build of ffmpeg): anyone who gets
  the app can also get all of its source. A paid closed-source version is not
  planned; it would need those parts replaced.
- Licences shown are those declared by each package on 7 October 2026. This
  register is a working record, not legal advice.

## Planned components (not yet added)

| Component | Role | Licence to confirm at its spike |
| --- | --- | --- |
| Whisper models / whisper.cpp | Speech to text in more languages (Burmese) | MIT |
| RapidOCR with PaddleOCR models | On-screen caption reading | Apache 2.0 |
