# Changelog

All notable changes to Factopia Voice. Versions follow MAJOR.MINOR.PATCH.

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

## 2.0.1 - 2026-10-07

- Added an automated test suite (31 tests) covering script handling, audio
  assembly, the generation pipeline and the local server's safety checks.
- Added this changelog and a third-party licence register (LICENSES.md).

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
