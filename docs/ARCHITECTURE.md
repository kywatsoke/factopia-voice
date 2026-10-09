# Factopia Voice: architecture

## Shape

One Python core, one local API, one web interface. The same code runs on macOS
and Windows; nothing is written per platform except the two small launchers.

```
 Web interface (factopia_voice/web)          what you see
        |  HTTP on 127.0.0.1 only
 Local API (server.py)                       thin: checks input, calls the pipeline
        |
 Pipeline (pipeline.py)                      the one path every clip takes
   script -> [translate] -> clean -> dictionary -> segments -> engine -> assemble -> file -> library
        |              |                 |                        |
 translate/        text.py           engines/                 audio.py, library.py
 (plug-in slot)    (rules)           (plug-in slot)           (export, history)
        |
 data/  profile.json  dictionary.json  library.json  output/  models/
```

## Captions (2.1)

```
 video or audio file ─ media.py (ffmpeg) ─ audio.wav ─ listeners/ (own process) ─ words with times
 Library clip + its script ───────────────────────────────────────┘            │
                                   captions.py: align to script, group into lines
                                                     │
                 projects.py: one folder per project (source, track, style), background jobs
                                                     │
                 render.py: preview frame  ·  SRT  ·  video with captions burned in
```

- `listeners/` mirrors `engines/`: one file per speech-to-text model. Parakeet
  (English) is the first; a multilingual model is another file.
- Recognition runs as a separate process (`listeners/worker.py`) so its memory
  is returned afterwards and its runtime cannot clash with the voice engine's.
- `render.py` draws captions with Pillow and blends them onto raw frames piped
  through ffmpeg. The preview and the export share that code.
- Translation (2.2) writes to the same caption track, and so would a future
  on-screen caption reader, so the editor, styling and export need no changes.

## Translation (2.2)

- `languages.py` holds what differs between English, Chinese and Burmese
  captions, and which languages are translated (English and Chinese, from 3.0):
  detection, how words join, sentence and clause marks, and where a line may
  break (words, characters, Burmese syllables).
- `translate/llamacpp.py` (3.0) implements the Translator contract with
  TranslateGemma run by the bundled llama-server, using the model's official
  prompt. `translate/ollama.py` does the same through the separate Ollama app.
- Caption translation groups lines into sentences, translates each with its
  context, then spreads the result back over the sentence's time.
- A translated track is a new project that links (not copies) the video.

## Where the code is

| Path | Job |
| --- | --- |
| `factopia_voice/__main__.py` | Starts the server and opens the window |
| `config.py` | Paths, settings, small JSON stores |
| `server.py` | Local HTTP API and static files; Host and Origin checks |
| `pipeline.py` | Script to voiceover: the Studio's one path |
| `text.py`, `audio.py`, `library.py`, `downloads.py` | Script rules, audio assembly, clip history, model downloads |
| `engines/` | Speech engines (Kokoro) |
| `listeners/` | Speech-to-text models (Parakeet), run in `worker.py` |
| `media.py` | ffmpeg: probe, extract audio, frames |
| `captions.py` | Word timing, alignment to a script, line grouping, SRT |
| `projects.py` | Caption projects on disk and their background jobs |
| `render.py`, `fonts.py` | Drawing captions; finding fonts that have the right letters |
| `languages.py` | English, Chinese, Burmese rules |
| `translate/` | Translators: TranslateGemma built in (llama.cpp) or through Ollama |
| `web/` | The interface: HTML, CSS, plain JavaScript |
| `shell.py`, `workers.py`, `jobs.py` | App window, helper processes, background jobs |
| `storage.py`, `updates.py`, `about.py`, `shaping.py`, `selftest.py` | Storage panel, update check, licences screen, Burmese shaping, build checks |
| `tests/` | Automated tests with a fake engine, a fake Ollama and a fake llama-server |

## The installed app (3.0)

```
 Factopia Voice.app / Factopia Voice.exe   (PyInstaller: Python + packages inside)
   __main__.py   one window (pywebview) or the browser; a second start brings it forward
   server.py     the same local API and interface as before, on a free port
   workers.py    the app starts itself with --fv-worker for speech recognition
   shaping.py    loads the bundled FriBiDi before Pillow, so Burmese is shaped
   translate/llamacpp.py   starts the bundled llama-server on demand (graphics chip,
                           else processor) and stops it after 10 idle minutes
   storage.py    sizes, removing models, moving models, importing a 2.x folder
   updates.py    once-a-day check of GitHub releases
   selftest.py   --self-test: the checks the Installers workflow runs
 bundled beside Python: llama/ (llama-server), fribidi/, licenses/
```

| Where | Installed (Mac / Windows) | From source |
| --- | --- | --- |
| Settings, projects, logs | `~/Library/Application Support/Factopia Voice` / `%LOCALAPPDATA%\Factopia Voice` | `data/` |
| Models | `models/` inside that folder, or wherever Settings moved them (`locations.json`) | `data/models` |
| Files people make | `Documents/Factopia Voice` | `data/output` |

`packaging/` holds the build: see [packaging/README.md](../packaging/README.md).

## Why this shape

- **Cross-platform by default.** The interface is HTML, so there is no separate
  Mac and Windows GUI to maintain. A phone can later use the same interface
  over Wi-Fi, without an Android app.
- **Engines are plug-ins.** `engines/base.py` defines four methods
  (`files`, `load`, `voices`, `synthesize`). Kokoro is one file. A better model
  later is one new file plus one line in `engines/__init__.py`. Nothing else
  changes, and old clips keep a record of which engine made them.
- **Translators are plug-ins too.** `translate/base.py` defines the contract
  (`status`, `setup`, `translate`, `translate_many`); the built-in engine and
  Ollama are one file each. The pipeline calls it before speech when a script is in
  another language.
- **Data is separate from code.** Everything learned or created is in `data/`.
  Updating the program is replacing the code folder.

## How it improves over time

| What | Where | How |
|---|---|---|
| Pronunciation | `data/dictionary.json` | Each fix is applied to all future clips |
| Timing estimates | `profile.wps` | Recalibrated from every finished clip |
| Voice settings | `data/profile.json` | Last speed, pause and format are kept |
| Voice quality | `engines/` | Swap or add a model without touching the rest |

## Adding things later

**More voices (same engine).** The engine already reports all 54 Kokoro voices.
Add a picker to the Studio panel that writes `profile.voice`.

**Another language.** Kokoro covers English, Spanish, French, Hindi, Italian,
Japanese, Portuguese and Mandarin. A language outside that list needs a second
engine file. Check the model licence first: some multilingual models are
non-commercial and cannot be used on a monetized channel.

**Another translation engine.** Add `translate/<name>.py` implementing
`Translator`, register it in `translate/__init__.py`. Check its licence and its
Burmese quality first; NLLB-200, for example, is non-commercial.

**Another caption language.** Add an entry to `languages.py` (line length,
how words join, where lines may break), a font list in `fonts.py`, and a
speech-to-text model for it in `listeners/`.

**The on-screen caption reader.** A new input that reads burned-in captions
with OCR and writes a caption track; everything after that is already built.
Postponed on 9 October 2026 because it is the heaviest component.

**Phone access.** Bind the server to the local network behind a PIN and show
the address as a QR code. Kept out of 2.0 on purpose: it widens exposure.

## Resources (measured)

| Part | Measured on | Speed | Memory | Disk |
| --- | --- | --- | --- | --- |
| Kokoro 82M voice | 2-core cloud CPU, no GPU | 24 s of audio in about 10 s | about 1.1 GB | 354 MB |
| Parakeet speech to text | 2-core cloud CPU | 8.1x real time; 1.6% word errors on the test clips | about 1.1 GB, freed when the worker exits | 460 MB |
| TranslateGemma 4B (llama.cpp, Q4_K_M) | 4-core cloud CPU, no GPU | about 12 s per sentence | llama-server's own process | 2.49 GB |

A recent laptop is faster than the cloud CPU.

## Security

The server listens on 127.0.0.1 only, rejects requests whose Host or Origin is
not the app itself, and serves audio only from `data/output`.
