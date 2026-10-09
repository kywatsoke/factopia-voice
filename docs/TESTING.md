# Testing

Two layers: automated tests that run on every push, and a manual checklist
run on the release zip before a version is called done.

## Automated tests

63 tests, run with pytest (command in [DEVELOPMENT.md](DEVELOPMENT.md)).

| File | Covers |
| --- | --- |
| `test_text.py` | Script cleaning, pause tags, pronunciation dictionary, word count, file names |
| `test_audio.py` | Silence trimming, loudness, WAV and MP3 output |
| `test_pipeline.py` | Script to clip end to end with a fake engine: pauses, speed, dictionary, learned pace, refusals, deleting |
| `test_server.py` | Local API, audio range requests, bad input, refusing other sites, files outside the output folder |
| `test_captions.py` | Word timing, line grouping, alignment to a script, tidying, SRT format |
| `test_render.py` | Fonts and letter coverage, caption drawing and wrapping (Chinese and Burmese too), video burn-in |
| `test_languages.py` | Language detection, Burmese syllables, SRT reading, sentence and clause splitting |
| `test_translate.py` | The Ollama translator against a fake Ollama: setup, official prompt, quality choice, caption and text translation, 2.1 projects |

A fake voice engine (`tests/conftest.py`) and a fake Ollama server stand in
for the models, so no test needs a download, a GPU or the internet. The real
models are only exercised by the manual checklist below.

## Manual release checklist

Run on the release zip, unzipped into a new folder, on macOS and on Windows.
Note the date, machine and result in the verification record.

**First start**
- [ ] The launcher opens; uv and Python install; the voice model downloads.
- [ ] The app window opens and the Studio shows the voice as ready.

**Studio**
- [ ] A 75-word script becomes an MP3 of about 30 seconds; it plays and downloads.
- [ ] A blank line and `[pause 1]` give audible pauses.
- [ ] A pronunciation fix changes how the word is said.
- [ ] The clip appears in the Library with its script.

**Captions**
- [ ] A 60-second MP4 imports; the speech model downloads on first use.
- [ ] Captions appear with sensible timings; pasting the script gives its exact wording.
- [ ] Editing, splitting and joining lines work; the preview follows style changes.
- [ ] SRT export opens in CapCut or a video player.
- [ ] The burned-in MP4 plays with captions where the preview showed them.

**Translate** (Ollama installed and open)
- [ ] Set up translation downloads the model and reports ready.
- [ ] English to Chinese, English to Burmese and back give readable text.
- [ ] Translate captions makes a new project; Chinese and Burmese lines wrap
      and render with real letters (no empty boxes).
- [ ] An SRT file loads and translates.

**Upgrade**
- [ ] The `data` folder from the previous version, moved into the new folder,
      opens with its settings, dictionary, Library and projects intact.

## Verification record

| Version | Date | Machine | Result |
| --- | --- | --- | --- |
| 2.2.1 | 9 Oct 2026 | GitHub Actions: Ubuntu, Windows Server, macOS | Automated tests pass on all three. Found: Pillow's Mac and Windows wheels have no raqm text shaping, so Burmese burn-in is refused there (Linux has it) |
| 2.2.0 | 9 Oct 2026 | Linux cloud, stand-in translation model | Automated tests and interface pass. Real TranslateGemma not yet run |
| 2.1.0 | 7 Oct 2026 | MacBook, Apple silicon | Voiceover, speech to text, exact-script captions, SRT and burned-in export pass |
| 2.0.0 | 7 Oct 2026 | MacBook, Apple silicon | Voiceover from a clean folder passes |
| 2.0.0 | 6 Oct 2026 | Linux cloud | Pass |
| any | | Windows, by hand | Not yet run |
