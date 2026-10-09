# Development

How the repository is laid out, how to run and test the app from source, and
how a release is published.

## Repository layout

```
factopia-voice/               (github.com/kywatsoke/factopia-voice)
├── factopia_voice/           the app (see ARCHITECTURE.md for each module)
│   └── web/                  the interface: index.html, app.css, *.js
├── tests/                    automated tests (pytest)
├── docs/                     architecture, decisions, roadmap, testing, channel
├── packaging/                builds the .dmg and Setup.exe (see packaging/README.md)
├── scripts/                  translation_sample.py (real-model report)
├── .github/workflows/        tests, installers, release, translation sample
├── Start Factopia Voice (Mac).command
├── Start Factopia Voice (Windows).bat
├── requirements.txt          what the app needs
├── requirements-dev.txt      what the tests need on top
├── CHANGELOG.md
├── THIRD_PARTY_LICENSES.md
├── LICENSE                   GPL-3.0
└── README.md
```

Run from source, the app keeps its files in `data/` next to the code (never
committed). The installed app uses the per-user folders in the README.

## Run from source

Install [uv](https://docs.astral.sh/uv/) once, then from the repository folder:

```bash
uv run --python 3.12 --no-project --with-requirements requirements.txt python -m factopia_voice --browser
```

The launchers in the repository do the same. Without `--browser` the app
tries its own window, which needs `pywebview` (in
`packaging/requirements-build.txt`). Built-in translation needs a
`llama-server` on PATH or `FACTOPIA_VOICE_LLAMA_SERVER`; otherwise choose
Ollama in Settings.

### Settings through environment variables

| Variable | Default | Use |
| --- | --- | --- |
| `FACTOPIA_VOICE_DATA` | `data/` next to the code | Keep data elsewhere, for example to share one data folder between versions |
| `FACTOPIA_VOICE_PORT` | `8760` | When another program uses the port |
| `FACTOPIA_VOICE_NO_WINDOW` | unset | Start the server without opening a window |
| `FACTOPIA_VOICE_BROWSER` | unset | `default` opens the normal browser instead of a Chrome or Edge app window |
| `FACTOPIA_VOICE_OLLAMA` | `http://127.0.0.1:11434` | Where Ollama listens |
| `FACTOPIA_VOICE_FFMPEG` | the bundled ffmpeg | Use another ffmpeg binary |
| `FACTOPIA_VOICE_LLAMA_SERVER` | the bundled one, then PATH | Command for llama-server (tests point it at a stand-in) |
| `FACTOPIA_VOICE_FRIBIDI` | the bundled one | Path of a FriBiDi library for Burmese shaping |
| `FACTOPIA_VOICE_RELEASES` | `kywatsoke/factopia-voice` | Repository the update check reads |
| `FACTOPIA_VOICE_DEBUG` | unset | More detail in the log |

## Tests

```bash
uv run --python 3.12 --no-project --with-requirements requirements.txt \
   --with-requirements requirements-dev.txt pytest -q
```

The suite uses a fake voice engine, a fake Ollama and a fake llama-server, so it downloads
no models and finishes in a few seconds. Tests that need a font for a
language, or an ffmpeg that can encode video, skip themselves when the
machine lacks it. [TESTING.md](TESTING.md) has the manual checklist for
releases.

## Conventions

- **No build step.** Plain Python, plain HTML, CSS and JavaScript. The
  launchers run the repository as it is.
- **Standard library first.** The server is `http.server`; add a package only
  when it saves real work, and record it in `THIRD_PARTY_LICENSES.md`.
- **Plug-ins behind small interfaces:** `engines/`, `listeners/`,
  `translate/`. A new model is a new file plus one line in that folder's
  `__init__.py`.
- **Data compatibility.** A data folder from any earlier 2.x version must open
  unchanged. Give new fields a default when loading (see `projects.load`), and
  add a test that loads the old shape.
- **Text files are UTF-8**, always opened with `encoding="utf-8"`. Windows
  does not default to it.
- **Words the user sees** are short, plain and say what to do next.
- **Licences.** Check a model's licence before writing code around it.
  Non-commercial models cannot be used for a monetised channel.

## Continuous integration

| Workflow | Runs | Does |
| --- | --- | --- |
| Tests | every push to `main`, pull requests | pytest on Linux, Windows and macOS |
| Installers | pull requests that touch the app or packaging, by hand | builds the `.dmg` and `Setup.exe`, self-tests the packed apps, installs them and tests again |
| Release | by hand, or a pushed `v*` tag | Tests and Installers, then a release with both installers |
| Translation sample | by hand | runs the real TranslateGemma on fixed sentences; the report goes to the `ci-reports` branch |

Each run's summary page lists the results as notices (test counts, each
self-test check, installer sizes), so the logs rarely need opening. The
repository is public, so GitHub's standard build machines are free.

## Making a release

1. Update `__version__` in `factopia_voice/__init__.py`. A hyphen
   (`3.0.0-beta.2`) makes a pre-release, offered only to people on a beta.
2. Add a section to `CHANGELOG.md` headed `## <version> - <date>`. The release
   notes are taken from that section, so write it for the user.
3. Update `THIRD_PARTY_LICENSES.md` if a dependency or model changed.
4. Merge to `main` and wait for Tests and Installers to pass.
5. On GitHub, open **Actions > Release > Run workflow** and run it on `main`.
   It runs the tests and builds and checks both installers, creates the tag
   `v<version>`, and publishes `Factopia-Voice-Mac.dmg` and
   `Factopia-Voice-Windows-Setup.exe` with the changelog section as notes.
   It refuses a version that was already released.
6. Install both and go through the checklist in [TESTING.md](TESTING.md).
