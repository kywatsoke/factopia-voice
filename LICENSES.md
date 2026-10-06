# Third-party licence register

Everything Factopia Voice downloads, installs or bundles, and what each
licence means for the project. Update this file whenever a dependency or
model is added or changed. Checked 7 October 2026.

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
| uv | Sets up Python on first start | Apache 2.0 or MIT | Yes | Not bundled |
| Python 3.12 | Runtime | PSF-2.0 | Yes | Yes |

## What this means

- **Using the app yourself, and publishing the audio it makes, is unaffected.**
  These licences cover the software, not the voiceovers.
- **Selling a closed-source app is blocked by two components today:** phonemizer
  and espeak-ng are GPL. Before a public release, either replace the
  text-to-phoneme step with a permissively licensed one, or release the app's
  own source under the GPL.
- Licences shown are those declared by each package on 7 October 2026. This
  register is a working record, not legal advice.

## Planned components (not yet added)

| Component | Role | Licence to confirm at its spike |
| --- | --- | --- |
| Whisper models / faster-whisper | Speech to text | MIT |
| RapidOCR with PaddleOCR models | On-screen caption reading | Apache 2.0 |
| ffmpeg | Video export | LGPL or GPL depending on the build |
| Translation engine | Caption translation | To be chosen |
