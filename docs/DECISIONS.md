# Decisions

Each entry records what was chosen, why, and what it costs. Newest first.
Add an entry whenever an engine, a licence or the shape of the app changes,
so a later change can be judged against the reason for the first.

## 2026-10-09 · Translation: English and Chinese only

- **Chosen:** translation between English and Chinese, either way. Burmese
  translation is removed from the Translate screen, caption translation and
  the engines; Burmese captions (SRT import, editing, styling, burn-in)
  stay.
- **Why:** real samples from TranslateGemma 4B and 12B gave wrong key words
  and stray words from other languages in Burmese, while Chinese was good.
  The user, who reads Burmese, judged it not usable.
- **Next for Burmese:** a natural, non-robotic Burmese voice is wanted
  (decided the same day); no suitable offline voice is known yet.

## 2026-10-09 · 3.0: installers for people who are not technical

- **Chosen:** the same Python app packed with PyInstaller into a Mac `.app`
  (Apple silicon, macOS 13+) in a `.dmg`, and a Windows 10/11 folder in a
  per-user Inno Setup installer. Its own window through pywebview (WebKit on
  Mac, WebView2 on Windows), with the browser as fallback. Built and checked
  by GitHub Actions on real Mac and Windows machines.
- **Why:** friends should install it like any app: no Python, no terminal, no
  administrator password. Keeping one Python core and one web interface
  avoids rewriting anything per platform.
- **Cost:** installers of a few hundred MB; not signed with a paid
  certificate, so each system warns once (Apple Developer ID US$99 a year
  would remove the Mac warning). Intel Macs are not built.

## 2026-10-09 · Translation built in: llama.cpp with a public model mirror

- **Chosen:** llama.cpp's `llama-server` (MIT) ships inside the app and runs
  TranslateGemma 4B as a GGUF file (Q4_K_M, 2.49 GB) downloaded from the
  public Hugging Face mirror `mradermacher/translategemma-4b-it-GGUF`, pinned
  by revision and SHA-256. Ollama remains an option in Settings.
- **Why:** no second app and no Hugging Face sign-in (Google's own copy is
  gated). Gemma's terms allow redistribution with the terms passed on; the
  app shows them on the welcome screen before any download.
- **Cost:** the mirror is a third party: the pinned checksum guards against a
  changed file, and a different mirror can be pinned if it disappears.
- **Quality, measured 9 October 2026** on GitHub's machines, same sentences:
  both sizes translate English and Chinese well. Burmese is weak in both: the
  4B mistranslated key words ("honey", "Venus") and let Greek and Chinese
  words in; the 12B (7.3 GB, about 4x slower) was better on some lines but
  still got "honey", "octopus" and "shark" wrong and let an Arabic word in.
  4B stays the default (the user's choice); Burmese output needs a Burmese
  speaker to check it before publishing.

## 2026-10-09 · FriBiDi built from source and shipped with the app

- **Chosen:** FriBiDi (LGPL-2.1-or-later) built in CI and loaded before
  Pillow looks for it (`factopia_voice/shaping.py`).
- **Why:** Pillow's Mac and Windows wheels enable Burmese shaping (raqm)
  only when FriBiDi can be found, and they do not include it. Verified in CI:
  raqm is on in the packed Mac app.

## 2026-10-09 · Graphics chip first, processor always as fallback

- **Chosen:** translation tries the graphics chip (Metal on Mac, Vulkan on
  Windows) and restarts on the processor if that fails; video export tries
  the hardware encoder (VideoToolbox, NVENC, Quick Sync, AMF) after a test
  encode, with x264 as fallback. Voice and speech to text stay on the
  processor: they are already faster than real time.
- **Why:** speed where it matters, without a broken driver ever stopping work.

## 2026-10-09 · Files in the usual per-user places

- **Chosen:** the installed app keeps settings, projects and models in
  Application Support (Mac) or `%LOCALAPPDATA%` (Windows), and puts the files
  people make in Documents/Factopia Voice. Running from source keeps the 2.x
  `data/` folder.
- **Why:** an installed app cannot write inside itself; Documents is where
  people look; large models must not sync with a roaming profile.

## 2026-10-09 · Open source (GPL-3.0-or-later) in a public repository

- **Chosen:** the app's own code is licensed GPL-3.0-or-later and the
  repository `kywatsoke/factopia-voice` is public. It was started fresh from a
  history rewritten to GitHub's no-reply address, so no personal email is
  published; the earlier private repository is kept only as a backup. Tests run on Linux, Windows
  and macOS for every push. The Release workflow, started from the Actions
  tab, builds the downloads and tags the version.
- **Why:** the app is shared free with friends, and two parts of the voice
  engine (phonemizer, espeak-ng) are GPL, so anyone who receives the app is
  entitled to its source. Publishing it settles that, lets friends download
  without a GitHub account, and makes GitHub's build machines free.
  Alternatives were a private repository with a separate public download
  repository, or sharing installers privately; both still owe the source.
- **Cost:** anyone can read and reuse the code under the GPL. A paid
  closed-source version would need the GPL parts replaced.

## 2026-10-09 · On-screen caption reader postponed

- **Chosen:** translation first; the OCR reader for burned-in captions waits.
- **Why:** it is the heaviest component (OCR models, frame sampling, area
  selection), and the translation it would feed was not built yet.
- **Cost:** captions burned into a video cannot be lifted out yet. SRT files
  and speech recognition cover most cases.

## 2026-10-09 · Translation: TranslateGemma through Ollama

- **Chosen:** Google's TranslateGemma, 4B (3.3 GB) as standard and 12B
  (8.1 GB) as high quality, run by the free Ollama app through its local API,
  with the model's official prompt.
- **Why:** it covers English, Chinese and Burmese in every direction in one
  model; Google claims no rights in its outputs; Ollama handles the GPU, the
  download and keeping the model in memory on both Mac and Windows.
  NLLB-200 was ruled out because its licence is non-commercial.
- **Cost:** translation needs a second app installed, and the Gemma Terms of
  Use and Prohibited Use Policy apply. Burmese quality is unproven until it is
  judged on real output.

## 2026-10-09 · A translated track is a new project

- **Chosen:** translating captions creates a new project that hard-links the
  original video and keeps its timings; the original is untouched.
- **Why:** the English track stays available, both can be exported side by
  side, and linking avoids a second copy of a large video.

## 2026-10-09 · No Burmese voice yet

- **Chosen:** Burmese is supported for text and captions only.
- **Why:** no offline Burmese voice with a licence that allows a monetised
  channel was found.

## 2026-10-07 · Captions are drawn by the app, not by ffmpeg

- **Chosen:** Pillow draws each caption; numpy blends it onto frames piped
  through ffmpeg. The preview and the export share the code.
- **Why:** any installed font works, the preview matches the export exactly,
  and Chinese and Burmese can be checked for missing letters before export.
- **Cost:** burning in is slower than ffmpeg's own subtitle filter. Burmese
  needs Pillow's raqm text shaping, which its Mac and Windows wheels only
  enable when the FriBiDi library is present (found 9 Oct 2026); until it is
  supplied, Burmese burn-in is refused there.

## 2026-10-07 · ffmpeg bundled through imageio-ffmpeg

- **Chosen:** the ffmpeg binary that ships inside the imageio-ffmpeg package.
- **Why:** nothing extra for the user to install on either platform.
- **Cost:** it is a GPL build. Fine for personal use; a paid closed-source
  release would need an LGPL build. Recorded in THIRD_PARTY_LICENSES.md.

## 2026-10-07 · Speech to text: Parakeet TDT 0.6B v2

- **Chosen:** NVIDIA Parakeet TDT 0.6B v2 (CC BY 4.0) through sherpa-onnx, in
  a separate worker process.
- **Why:** in the spike it was the fastest (8.1x real time on a 2-core CPU)
  and most accurate (1.6% word errors, clean and noisy) of the models tried,
  and it gives word timings. Whisper base, small and turbo were slower, less
  accurate, and gave no word timings through this runtime.
- **Cost:** English only. Other languages need a second listener. The worker
  process frees its 1.1 GB when it finishes.

## 2026-10-06 · Voice: Kokoro 82M, voice "Michael"

- **Chosen:** the Kokoro-82M model (Apache 2.0) through kokoro-onnx, voice
  `am_michael`.
- **Why:** small enough to run on any laptop CPU, offline, licence allows a
  monetised channel, and the voice was picked by ear from samples.
- **Cost:** the tone was rated about 60% natural; improving it is on the
  backlog. Its text-to-phoneme step (phonemizer, espeak-ng) is GPL.

## 2026-10-06 · One Python core with a local web interface

- **Chosen:** a Python package serving an HTML interface on `127.0.0.1`,
  opened in a Chrome or Edge app window; started by uv launchers.
- **Why:** one interface for macOS and Windows (and a phone later) instead of
  two native ones; uv installs Python itself, so the user installs nothing.
- **Cost:** a terminal window stays open while the app runs.

## 2026-10-06 · Data kept apart from code

- **Chosen:** everything the app learns or makes lives in `data/`.
- **Why:** updating the app is replacing the code; settings, the dictionary,
  clips, projects and models carry over. Older data folders must keep working.
