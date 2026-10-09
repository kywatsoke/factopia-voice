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
- The on-screen caption reader (2.2) and translation (2.3) will write to the
  same caption track, so the editor, styling and export need no changes.

## Translation (2.2)

- `languages.py` holds what differs between English, Chinese and Burmese:
  detection, how words join, sentence and clause marks, and where a line may
  break (words, characters, Burmese syllables).
- `translate/ollama.py` implements the Translator contract with TranslateGemma
  through Ollama's local API, using the model's official prompt. Ollama is a
  separate app: it handles the GPU, the download and keeping the model loaded.
- Caption translation groups lines into sentences, translates each with its
  context, then spreads the result back over the sentence's time.
- A translated track is a new project that links (not copies) the video.

## Why this shape

- **Cross-platform by default.** The interface is HTML, so there is no separate
  Mac and Windows GUI to maintain. A phone can later use the same interface
  over Wi-Fi, without an Android app.
- **Engines are plug-ins.** `engines/base.py` defines four methods
  (`files`, `load`, `voices`, `synthesize`). Kokoro is one file. A better model
  later is one new file plus one line in `engines/__init__.py`. Nothing else
  changes, and old clips keep a record of which engine made them.
- **Translation has a reserved slot.** The pipeline already calls
  `translate/` before speech. Registering a translator switches it on.
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

**Translation.** Add `translate/<name>.py` implementing `Translator`, register
it in `translate/__init__.py`, and add a language picker that sends
`target_language` to `/api/generate`. Offline candidates: Argos Translate
(MIT/CC0, about 30 languages) or NLLB-200 through CTranslate2 (200 languages,
non-commercial licence).

**Phone access.** Bind the server to the local network behind a PIN and show
the address as a QR code. Kept out of 2.0 on purpose: it widens exposure.

**A packaged installer.** PyInstaller or Briefcase can wrap this folder into a
.app and .exe once the feature set settles.

## Resources (measured)

Kokoro 82M on a 2-core cloud CPU, no GPU: 24 seconds of audio in about 10
seconds, about 1.1 GB of memory while running, 354 MB of model files on disk.
A recent laptop should be faster.

## Security

The server listens on 127.0.0.1 only, rejects requests whose Host or Origin is
not the app itself, and serves audio only from `data/output`.
