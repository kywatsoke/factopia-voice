# Changelog

All notable changes to Factopia Voice. Versions follow MAJOR.MINOR.PATCH.

## Unreleased

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
