# Testing

Two layers: automated tests that run on every push, and a manual checklist
run on the release zip before a version is called done.

## Automated tests

70 tests, run with pytest (command in [DEVELOPMENT.md](DEVELOPMENT.md)).

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
| `test_builtin_translator.py` | The built-in engine against a fake llama-server: download step, official prompt, graphics chip first, processor fallback without restarting per sentence, resumable checked downloads |

A fake voice engine (`tests/conftest.py`), a fake Ollama server and a fake
llama-server (`tests/fake_llama_server.py`) stand in
for the models, so no test needs a download, a GPU or the internet. The real
models are only exercised by the manual checklist below.

## Installer checks on GitHub

The Installers workflow starts each packed app with `--self-test` and posts
every check on the run's summary page: version, text shaping (raqm with the
bundled FriBiDi), voice engine, speech engine, video tools and hardware
encoder, fonts, translation engine (llama-server), window toolkit, helper
process, local server, a sentence spoken by Kokoro and heard back by
Parakeet. Then it installs the installer (silently on Windows, from the
mounted `.dmg` on Mac), runs the self-test on the installed copy, and on
Windows uninstalls again.

What it cannot check: the first-open warnings, real windows and clicks,
WebView2 on a machine without it, a real graphics card. Those are in the
checklist below.

## Manual release checklist

Install the release on a Mac and a Windows PC that have never had Factopia
Voice. Note the date, machine and result in the verification record.

**Install and first start**
- [ ] The `.dmg` / `Setup.exe` downloads from Releases without a GitHub account.
- [ ] The first-open warning is passed with the steps in the README.
- [ ] The welcome screen shows the models and terms; Agree and continue
      downloads the voice with progress, and the Studio says the voice is ready.
- [ ] Opening the app a second time brings the window forward instead of a second copy.

**Studio**
- [ ] A 75-word script becomes an MP3 of about 30 seconds; it plays, and
      Show in Finder/folder opens Documents/Factopia Voice with the file selected.
- [ ] A blank line and `[pause 1]` give audible pauses.
- [ ] A pronunciation fix changes how the word is said.
- [ ] The clip appears in the Library with its script.

**Captions**
- [ ] A 60-second MP4 imports; the speech model downloads on first use.
- [ ] Captions appear with sensible timings; pasting the script gives its exact wording.
- [ ] Editing, splitting and joining lines work; the preview follows style changes.
- [ ] SRT export opens in CapCut or a video player.
- [ ] The burned-in MP4 plays with captions where the preview showed them;
      the export line names the encoder used.

**Translate** (built in, no Ollama)
- [ ] The first translation offers the 2.5 GB download, which continues after
      a broken connection and reports ready.
- [ ] Settings > Performance names the graphics chip or card while translating.
- [ ] English to Chinese, English to Burmese and back give readable text.
- [ ] Translate captions makes a new project; Burmese lines are shaped
      correctly (vowel signs in place) in the preview and the burned-in video.
- [ ] An SRT file loads and translates.

**Settings**
- [ ] Storage shows sizes; removing the speech model frees its space and it
      downloads again when next needed.
- [ ] Moving the models to another folder works, and the app uses them there.
- [ ] Bring in work from an earlier version copies a 2.x `data` folder's
      clips, projects, dictionary and models.
- [ ] Check now reports the newest release.

**Update and uninstall**
- [ ] Installing a newer version over the old one keeps files and models.
- [ ] Windows: uninstall asks about the models; Documents/Factopia Voice stays.

## Verification record

| Version | Date | Machine | Result |
| --- | --- | --- | --- |
| 3.0.0-beta.1 | 9 Oct 2026 | GitHub Actions: macOS (Apple silicon), Windows Server | See the Installers run; filled in when the beta is published |
| 3.0.0-beta.1 | 9 Oct 2026 | GitHub Actions: Ubuntu, real TranslateGemma 4B | English and Chinese good; Burmese poor (wrong words, stray Greek and Chinese tokens) |
| 2.2.1 | 9 Oct 2026 | GitHub Actions: Ubuntu, Windows Server, macOS | Automated tests pass on all three. Found: Pillow's Mac and Windows wheels have no raqm text shaping, so Burmese burn-in is refused there (Linux has it) |
| 2.2.0 | 9 Oct 2026 | Linux cloud, stand-in translation model | Automated tests and interface pass. Real TranslateGemma not yet run |
| 2.1.0 | 7 Oct 2026 | MacBook, Apple silicon | Voiceover, speech to text, exact-script captions, SRT and burned-in export pass |
| 2.0.0 | 7 Oct 2026 | MacBook, Apple silicon | Voiceover from a clean folder passes |
| 2.0.0 | 6 Oct 2026 | Linux cloud | Pass |
| any | | Windows, by hand | Not yet run |
