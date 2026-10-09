# Changelog

All notable changes to Factopia Voice. Versions follow MAJOR.MINOR.PATCH.

## 3.0.0-beta.2 - 2026-10-09

Fixes the first start on a Mac, where the voice download stopped every time.

- Downloads (the voice, speech and translation models) and the update check
  now use the certificates the computer itself trusts (macOS Keychain,
  Windows certificate store). The Python inside the installed app could not
  find a certificate list of its own, so every secure download failed and
  was reported as a broken connection.
- The start-up error screen has **Try again** and **Open log folder**
  buttons; there is no need to quit and reopen the app.
- The log now records why each download attempt failed.
- Each installer is now checked on GitHub's Mac and Windows machines with a
  real download, not only with models that were already there.

## 3.0.0-beta.1 - 2026-10-09

Easy install: a real app for Mac and Windows, for people who are not
technical. A test version, published as a pre-release.

- Installers: `Factopia-Voice-Mac.dmg` for Apple silicon Macs (macOS 13 or
  later) and `Factopia-Voice-Windows-Setup.exe` for Windows 10 and 11. No
  Python, no terminal, no administrator password on Windows.
- The app opens in its own window. Opening it again brings the window forward.
- First start: a welcome screen lists the AI models and their terms, with one
  "Agree and continue". Models download inside the app when first needed,
  with progress and resume after a broken connection; the translation model
  is also checked against its published checksum.
- Translation is built in: TranslateGemma 4B runs on llama.cpp inside the
  app, downloaded without any sign-in. Ollama stays available as an option.
- Translation now covers English and Chinese only. Burmese translation is
  removed: its quality was not good enough with either model size. Burmese
  captions still work (import an SRT, edit, style, export).
- Burmese captions are drawn correctly on Mac and Windows: the app now
  carries the FriBiDi text-shaping library.
- Speed: translation uses the Mac's graphics chip or a Windows graphics card
  when there is one, video export uses the computer's video encoder, and
  both fall back to the processor by themselves. Settings > Performance shows
  what is used, with a switch to use the processor only.
- Files in the usual places: what you make goes to Documents/Factopia Voice;
  settings, projects and models to the per-user app folder. Settings >
  Storage shows sizes, removes models and moves them to another drive.
  "Bring in your earlier work" copies everything from a 2.x folder.
- Settings > Updates checks once a day for a new version (can be turned off).
- Settings > About and licences lists every model and component with its
  licence, and links to the source code.
- In the app window, "Show in Finder/folder" replaces downloads: files are
  already saved in your Documents folder.
- Factopia Voice is open source (GPL-3.0-or-later).
- Each installer is built and started on GitHub's Mac and Windows machines,
  which check text shaping, the engines, the window, a spoken sentence heard
  back by speech recognition, and installing the installer itself.

## 2.2.1 - 2026-10-09

Repository set up on GitHub, with documentation and automatic testing.

- Factopia Voice is now open source under GPL-3.0-or-later, in a public GitHub
  repository. Each version is published on its Releases page as a
  ready-to-run zip.
- Tests run automatically on Linux, Windows and macOS for every change.
- New README with installing, updating and troubleshooting; new guides for
  development, testing, decisions and the roadmap in the docs folder.
- Subtitle files are named with their language (for example `_zh.srt`), so a
  Chinese and an English export of one video no longer look alike.
- Exports from a project whose name has no English letters (a Chinese or
  Burmese file name) are called `captions_…` or `video_…` instead of
  `voiceover_…`.
- Burmese captions are no longer drawn scrambled on computers whose Pillow
  lacks text shaping (Mac and Windows today): the preview and video export explain
  the problem and point to the SRT export instead.
- Speech recognition passes text as UTF-8, so error messages with non-English
  text cannot break it on Windows.
- The licence register is now `THIRD_PARTY_LICENSES.md`; the app's own licence
  is in `LICENSE`.
- Automated tests: 63 (was 61).

## 2.2.0 - 2026-10-09

Translation between English, Chinese and Burmese, in every direction.

- Translate screen: paste text, pick the languages (or let the app detect the
  source), translate, copy, or send an English result to the Studio.
- Caption translation: translate a caption track into a new project that keeps
  the video and timings. Lines are translated as whole sentences for context,
  then split at clause marks to fit the screen.
- Subtitle files: load an SRT into a project, or on its own, to translate it.
  Chinese files in GB18030 encoding are read too.
- Each project has a language. Chinese and Burmese captions wrap between
  characters and syllables, get a font that has their letters, and fonts
  without those letters are refused instead of drawing empty boxes.
- Engine: Google's TranslateGemma (4B standard, 12B high quality) run locally
  by Ollama. Translation needs the free Ollama app; everything else does not.
- The on-screen caption reader is postponed.
- Automated tests: 61 (was 44).

## 2.1.0 - 2026-10-07

Captions: the reverse of the voiceover.

- Captions screen: import a video or audio file (mp4, mov, mp3, wav and
  similar) or start from a clip in the Library.
- English speech to timed caption lines, offline after a one-time 460 MB
  model download (Parakeet TDT 0.6B v2). Recognition runs in its own process
  and frees its memory when done.
- Exact wording: paste the script, or start from a Library clip, and the
  captions use the script's words on the recognised timings.
- Caption editor: change text and timing, split, join, add and delete lines;
  three line lengths (short, medium, sentences).
- Styling with any font installed on the computer: size, colours, outline,
  background box, position, width, capitals. The preview is drawn by the same
  code as the export. The last style used becomes the default.
- Export a subtitle file (SRT) or a copy of the video with captions burned in.
  ffmpeg is bundled; nothing extra to install.
- Large files are streamed to and from disk instead of held in memory.
- Automated tests: 44 (was 31).
- Verified on macOS (Apple silicon) on 7 October 2026: voiceover, speech to
  text, exact-script captions, SRT and burned-in video export.

## 2.0.1 - 2026-10-07

- Added an automated test suite (31 tests) covering script handling, audio
  assembly, the generation pipeline and the local server's safety checks.
- Added this changelog and a third-party licence register (LICENSES.md, now
  THIRD_PARTY_LICENSES.md).

## 2.0.0 - 2026-10-06

First release on the modular architecture.

- Studio: script editor with word count, length estimate against a target,
  speed and pause controls, MP3 or WAV output.
- Library of generated clips with their scripts.
- Pronunciation dictionary applied to every clip.
- One voice (Michael, US English) on the Kokoro 82M engine, fully offline
  after the first start.
- Pluggable engine interface; reserved slot for translation.
- Launchers for macOS and Windows.
- Verified on Linux (6 Oct 2026) and macOS on Apple silicon (7 Oct 2026).
  Not yet verified on Windows.

## 1.0.0 - 2026-10-06

Single-file prototype with 27 selectable English voices. Superseded by 2.0.0.
