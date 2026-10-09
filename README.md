# Factopia Voice

Voiceovers, captions and translation, made on your own computer. Free, with
no account, no subscription and no uploads. Made for the Factopia Gist
YouTube channel and shared with friends.

| Screen | What it does |
| --- | --- |
| **Studio** | Paste a script, get a voiceover (MP3 or WAV) in a natural English voice, "Michael". |
| **Captions** | Import a video or audio file; speech becomes timed caption lines you can edit, style with any installed font, and export as a subtitle file (SRT) or burned into the video. |
| **Translate** | English, Chinese and Burmese in every direction, for text, caption tracks and SRT files. |
| **Library** | Every clip you made, with its script. Play, reuse, caption. |
| **Pronunciation** | Fix how a word is said once; every later clip uses the fix. |
| **Settings** | Translation, performance, storage, updates, about and licences. |

Version 3.0.0-beta.1 (test version). See [CHANGELOG.md](CHANGELOG.md) for what changed.

---

## Download and install

Go to [**Releases**](../../releases) and download the file for your computer:

| Computer | File |
| --- | --- |
| Mac with Apple silicon (M1 or later), macOS 13 or later | `Factopia-Voice-Mac.dmg` |
| Windows 10 or 11, 64-bit | `Factopia-Voice-Windows-Setup.exe` |

**Mac**
1. Open the `.dmg` and drag **Factopia Voice** onto **Applications**.
2. Open Applications and double-click **Factopia Voice**.
3. The first time only, macOS says it cannot check the app, because it is
   shared free without a paid Apple certificate. Click **Done**, open
   **System Settings > Privacy & Security**, scroll down, click
   **Open Anyway** next to Factopia Voice, and confirm. The very first start
   can take up to a minute while macOS checks the app; later starts are quick.

**Windows**
1. Double-click `Factopia-Voice-Windows-Setup.exe`.
2. If a blue "Windows protected your PC" box appears, click **More info**,
   then **Run anyway**. It installs for you only; no administrator password.
3. Click **Next** and **Install**. Factopia Voice is in the Start menu and,
   if you ticked it, on the desktop.

**First start.** A welcome screen lists the free AI models the app uses.
Tick **I agree** and press **Agree and continue**; the voice downloads
(about 340 MB) and the Studio is ready. The other models download the first
time you need them, inside the app:

| Feature | Download | When |
| --- | --- | --- |
| Voiceover | Kokoro voice, about 340 MB | After the welcome screen |
| Captions | Parakeet speech to text, about 480 MB | The first time you make captions |
| Translation | TranslateGemma 4B by Google, about 2.5 GB | The first time you translate |

No sign-in anywhere. After a model is downloaded, its feature works offline.

**What your computer needs:** 8 GB of memory (16 GB is comfortable for
translation), and about 4 GB of free disk for all three models. A graphics
chip or card is used when there is one, but none is needed.

## How to use it

**Studio.** Paste the script and press **Generate voiceover**
(or Ctrl/Cmd + Enter). A blank line adds a short pause; `[pause 0.8]` adds an
exact pause in seconds. The word count and estimated length update as you
type.

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

## Where your files are

| What | Mac | Windows |
| --- | --- | --- |
| The files you make (voiceovers, subtitles, videos) | `Documents/Factopia Voice` | `Documents\Factopia Voice` |
| Settings, captions projects, downloaded models | `~/Library/Application Support/Factopia Voice` | `%LOCALAPPDATA%\Factopia Voice` |
| The app | `Applications/Factopia Voice` | `%LOCALAPPDATA%\Programs\Factopia Voice` |

**Settings > Storage** shows how much each part uses, removes a model you no
longer need, and can move the models to another drive.

**Coming from version 2.x?** On the welcome screen (or later in Settings),
choose **Bring in your earlier work** and pick your old Factopia Voice
folder. Your clips, captions projects, pronunciation fixes and downloaded
models are copied in.

**Updating.** The app checks once a day for a new version (you can turn this
off in Settings) and shows a link when there is one. Install the new version
over the old one; your files and models stay.

**Uninstalling.** Mac: drag the app to the Bin; to free the models' space,
also delete `~/Library/Application Support/Factopia Voice`. Windows: Settings
> Apps > Factopia Voice > Uninstall; it asks whether to remove the models too.
Your own files in Documents are never removed.

## When something goes wrong

| What you see | What to do |
| --- | --- |
| Mac: "Open Anyway" does not appear | Open the app once first (it is refused), then look again in Privacy & Security. |
| Translation is slow | The first sentence loads the model (up to a minute). After that, a sentence takes a few seconds with a graphics chip, longer on the processor alone. |
| Chinese or Burmese captions show empty boxes | The font has no letters for that language; the app refuses such fonts. Pick another font. |
| A download stopped | Press the button again; it continues where it stopped. |
| Something else | **Settings > About > Open log folder**, and send the newest log file with a description. |

Quit with **Settings > Quit Factopia Voice**, or close the window.

---

## For development

One Python package with a web interface served on `127.0.0.1`, shown in its
own window. It also runs from source, without installing:

```bash
# Run from source (needs uv: https://docs.astral.sh/uv/)
uv run --python 3.12 --no-project --with-requirements requirements.txt python -m factopia_voice --browser

# Run the tests (no model downloads)
uv run --python 3.12 --no-project --with-requirements requirements.txt \
   --with-requirements requirements-dev.txt pytest -q
```

Every push runs the tests on Linux, Windows and macOS. The **Installers**
workflow builds the `.dmg` and `Setup.exe`, starts them on GitHub's Mac and
Windows machines, and checks them. **Actions > Release > Run workflow**
publishes a release with both installers.

| Document | Read it for |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the parts fit and where to add an engine, a listener or a translator |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Repository layout, settings, conventions, building installers, making a release |
| [docs/TESTING.md](docs/TESTING.md) | Automated tests, the release checklist, what has been verified where |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why each engine and design choice was made |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Releases, backlog and the link to the live project plan |
| [packaging/README.md](packaging/README.md) | How the installers are put together |
| [docs/channel/](docs/channel/) | The Factopia Short package skill used to write each Short |
| [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) | Every model and library, its licence and what it allows |

## Licence

Copyright (C) 2026 Kywat Soke.

Factopia Voice is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version. It is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; see [LICENSE](LICENSE) for details.

The models and libraries it uses keep their own licences, listed in
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Voiceovers, captions and
translations you make are yours to publish.
