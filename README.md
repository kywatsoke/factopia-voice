# Factopia Voice

An offline voiceover, captions and translation studio for the Factopia Gist
YouTube channel.
Everything runs on your own computer: no subscription, no upload, no credits.

| Screen | What it does |
| --- | --- |
| **Studio** | Paste a script, get a voiceover (MP3 or WAV) in the channel voice, "Michael". |
| **Captions** | Import a video or audio file; speech becomes timed caption lines you can edit, style with any installed font, and export as a subtitle file (SRT) or burned into the video. |
| **Translate** | English, Chinese and Burmese in every direction, for text, caption tracks and SRT files. |
| **Library** | Every clip you made, with its script. Play, download, reuse, caption. |
| **Pronunciation** | Fix how a word is said once; every later clip uses the fix. |
| **Settings** | Target length, translation quality, folders, Quit. |

Version 2.2.1. Runs on macOS (verified on an Apple silicon MacBook) and
Windows (not yet verified). See [CHANGELOG.md](CHANGELOG.md) for what changed.

---

## Install and start

1. Open the [latest release](../../releases/latest) and download
   `FactopiaVoice-<version>.zip`.
2. Unzip it anywhere you like, for example in your Documents folder.
3. Start it:
   - **Mac:** double-click `Start Factopia Voice (Mac).command`.
     The first time, macOS says it cannot verify the file, because it was
     downloaded and is not from the App Store. Click **Done**, open
     **System Settings > Privacy & Security**, scroll down, click
     **Open Anyway** next to the file's name, and confirm. (On macOS 14 or
     older: right-click the file, choose **Open**, then **Open** again.)
   - **Windows:** double-click `Start Factopia Voice (Windows).bat`.
     If a blue "Windows protected your PC" box appears, click
     **More info**, then **Run anyway**.

The first start needs the internet and takes a few minutes. It installs a
small helper ([uv](https://docs.astral.sh/uv/)) that sets up Python for the
app, then downloads the voice model (about 340 MB). After that the Studio
works offline.

The app opens in its own window when Chrome or Edge is installed, otherwise
in your default browser. Keep the black terminal window open while you work.

### Extra one-time downloads

| Feature | Download | When |
| --- | --- | --- |
| Voiceover | Kokoro voice model, about 340 MB | First start |
| Captions | Parakeet speech model, about 460 MB | First time you make captions |
| Translation | The free [Ollama](https://ollama.com) app, then TranslateGemma: 3.3 GB (standard) or 8.1 GB (high quality) | When you press **Set up translation** |

For translation, install Ollama and open it once. Then press
**Set up translation** on the Translate screen; the app checks Ollama and
downloads the model. Choose standard or high quality in **Settings**.

### What your computer needs

- A Mac or Windows PC from the last several years. No graphics card needed.
- About 3 GB of free memory for voiceovers and captions; 8 GB or more of
  memory for translation (16 GB for the high-quality model).
- About 2 GB of disk, plus 3.3 GB or 8.1 GB for a translation model.

## How to use it

**Studio.** Paste the script and press **Generate voiceover**
(or Ctrl/Cmd + Enter). A blank line adds a short pause; `[pause 0.8]` adds an
exact pause in seconds. The word count and estimated length update as you
type, against the target length set in Settings.

**Captions.** Drop in a video or audio file, or press **Captions** on a
Library clip. Pasting the script gives captions with your exact wording on
the recognised timings. Edit, split and join lines, pick a font and style,
then export an SRT file or a captioned copy of the video. Speech recognition
is English only for now.

**Translate.** Paste text, pick the languages (or let the app detect the
source) and press Translate. In Captions, **Translate captions** makes a new
project in the other language with the same timings; the original stays as
it was. You can also load an SRT subtitle file to translate it.

**Pronunciation.** If the voice says a name wrong, type the word and how
to say it (for example `Turritopsis` → `tur-ih-TOP-sis`), press **Listen** to
check, then **Save**.

## Your files

Everything you create is in the `data` folder inside the app folder:

| Path | Contents |
| --- | --- |
| `data/output` | Voiceovers, subtitle files and captioned videos |
| `data/projects` | Imported files and their captions, one folder per project |
| `data/models` | Downloaded models (safe to keep between versions) |
| `data/profile.json` | Voice, speed, pause, file type, translation quality |
| `data/dictionary.json` | Pronunciation fixes |
| `data/library.json` | Clip history |

**Updating to a new version:** quit the app, unzip the new version, and move
the `data` folder from the old app folder into the new one. Older data
folders open unchanged. **Settings > Open clips folder** shows where the
files are.

**Another voice:** this version uses one voice. To try another, quit the app,
open `data/profile.json` in a text editor and change `"voice"` (for example
`am_fenrir`, `am_puck`, `af_heart`, `bm_george`), then start again.

## When something goes wrong

| What you see | What to do |
| --- | --- |
| "Port 8760 is being used by another program" | Another copy may be running: use Quit in it. Otherwise restart the computer. |
| The window does not open | Go to http://127.0.0.1:8760 in a browser while the terminal window is open. |
| Translate says Ollama is not running | Open the Ollama app, then press **Check again** on the Translate screen. |
| Chinese or Burmese captions show empty boxes | The font has no letters for that language; the app refuses such fonts. Pick another font, or install one (Noto Sans SC, Noto Sans Myanmar). |
| Mac: "Open Anyway" does not appear | In Terminal, run `xattr -dr com.apple.quarantine ` followed by a space, drag the app folder onto the Terminal window, and press Return. Then double-click the launcher again. |
| Burmese captions cannot be burned into the video | On Mac and Windows the drawing library lacks the text shaping (FriBiDi) that Burmese needs, so the app refuses rather than draw scrambled letters. Export the SRT and add it in CapCut. A fix is next on the roadmap. |
| The terminal shows an error and stops | Copy the text in the terminal window; it says what failed. |

Quit with **Settings > Quit Factopia Voice**, or close the terminal window.

---

## For development

The app is one Python package with a web interface, served on
`127.0.0.1` only. No build step; the launchers run the source as it is.

```bash
# Run from source (needs uv: https://docs.astral.sh/uv/)
uv run --python 3.12 --no-project --with-requirements requirements.txt python -m factopia_voice

# Run the tests (63 tests, a few seconds, no model downloads)
uv run --python 3.12 --no-project --with-requirements requirements.txt \
   --with-requirements requirements-dev.txt pytest -q
```

Every push to GitHub runs the tests on Linux and Windows; pull requests,
version tags and manual runs add macOS. **Actions > Release > Run workflow**
builds the release zip and publishes it on the Releases page.

| Document | Read it for |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the parts fit and where to add an engine, a listener or a translator |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Repository layout, settings, coding conventions, making a release |
| [docs/TESTING.md](docs/TESTING.md) | Automated tests, the manual release checklist, what has been verified where |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why each engine and design choice was made |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Releases, backlog and the link to the live project plan |
| [docs/channel/](docs/channel/) | The Factopia Short package skill used to write each Short |
| [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) | Every model and library, its licence and what it allows |

## Licence

Private project, all rights reserved; see [LICENSE](LICENSE).
The models and libraries it uses keep their own licences, listed in
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Voiceovers, captions and
translations you make are yours to publish. Selling the app itself would need
the GPL components named there replaced first.
