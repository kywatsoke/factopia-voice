# Changelog

All notable changes to Factopia Voice. Versions follow MAJOR.MINOR.PATCH.

## 2.2.1 - 2026-10-09

Repository set up on GitHub, with documentation and automatic testing.

- The code now lives in a private GitHub repository. Each version is published
  on its Releases page as a ready-to-run zip.
- Tests run automatically on Linux and Windows for every change, and on macOS
  for each release.
- New README with installing, updating and troubleshooting; new guides for
  development, testing, decisions and the roadmap in the docs folder.
- Subtitle files are named with their language (for example `_zh.srt`), so a
  Chinese and an English export of one video no longer look alike.
- Exports from a project whose name has no English letters (a Chinese or
  Burmese file name) are called `captions_…` or `video_…` instead of
  `voiceover_…`.
- Burmese captions are no longer drawn scrambled on computers whose Pillow
  lacks text shaping (Windows today): the preview and video export explain
  the problem and point to the SRT export instead.
- Speech recognition passes text as UTF-8, so error messages with non-English
  text cannot break it on Windows.
- The licence register is now `THIRD_PARTY_LICENSES.md`; the app itself is
  marked private, all rights reserved (`LICENSE`).
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
