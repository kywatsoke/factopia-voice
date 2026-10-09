# Development

How the repository is laid out, how to run and test the app from source, and
how a release is published.

## Repository layout

```
factopia/                     (github.com/kywatsoke/factopia)
├── factopia_voice/           the app (see ARCHITECTURE.md for each module)
│   └── web/                  the interface: index.html, app.css, *.js
├── tests/                    automated tests (pytest)
├── docs/                     architecture, decisions, roadmap, testing, channel
├── scripts/package.sh        builds the release zip
├── .github/workflows/        tests on every push; release on a version tag
├── Start Factopia Voice (Mac).command
├── Start Factopia Voice (Windows).bat
├── requirements.txt          what the app needs
├── requirements-dev.txt      what the tests need on top
├── CHANGELOG.md
├── THIRD_PARTY_LICENSES.md
├── LICENSE
└── README.md
```

`data/` is created next to the code on first start and is never committed
(see `.gitignore`).

## Run from source

Install [uv](https://docs.astral.sh/uv/) once, then from the repository folder:

```bash
uv run --python 3.12 --no-project --with-requirements requirements.txt python -m factopia_voice
```

This is exactly what the launchers do. The first run downloads Python 3.12,
the packages and the voice model.

### Settings through environment variables

| Variable | Default | Use |
| --- | --- | --- |
| `FACTOPIA_VOICE_DATA` | `data/` next to the code | Keep data elsewhere, for example to share one data folder between versions |
| `FACTOPIA_VOICE_PORT` | `8760` | When another program uses the port |
| `FACTOPIA_VOICE_NO_WINDOW` | unset | Start the server without opening a window |
| `FACTOPIA_VOICE_BROWSER` | unset | `default` opens the normal browser instead of a Chrome or Edge app window |
| `FACTOPIA_VOICE_OLLAMA` | `http://127.0.0.1:11434` | Where Ollama listens |
| `FACTOPIA_VOICE_FFMPEG` | the bundled ffmpeg | Use another ffmpeg binary |

## Tests

```bash
uv run --python 3.12 --no-project --with-requirements requirements.txt \
   --with-requirements requirements-dev.txt pytest -q
```

The suite uses a fake voice engine and a fake Ollama server, so it downloads
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

`.github/workflows/tests.yml` runs the tests with Python 3.12:

| Event | Linux | Windows | macOS |
| --- | --- | --- | --- |
| Push to `main` | yes | yes | no |
| Pull request, version tag, manual run ("Run workflow" on the Actions tab) | yes | yes | yes |

macOS minutes count ten times against the 2,000 free minutes a month for
private repositories, so the Mac runs only when it matters. A version tag
runs all three before the release is built. Usage is on GitHub under
Settings > Billing and plans.

## Making a release

1. Update `__version__` in `factopia_voice/__init__.py`.
2. Add a section to `CHANGELOG.md` headed `## <version> - <date>`. The release
   notes are taken from that section, so write it for the user.
3. Update `THIRD_PARTY_LICENSES.md` if a dependency or model changed.
4. Commit and push to `main`, and wait for the Tests run to pass.
5. On GitHub, open **Actions > Release > Run workflow** and run it on `main`.
   It runs the tests on all three platforms, builds
   `FactopiaVoice-<version>.zip` with `scripts/package.sh`, creates the tag
   `v<version>`, and publishes the zip on the Releases page with the changelog
   section as notes. It refuses to run if that version was already released.
   (Pushing a tag such as `v2.2.1` from a computer with git does the same.)
6. Download the zip and run it through the manual checklist in
   [TESTING.md](TESTING.md) on the Mac (and Windows when available).

The zip holds only what is needed to run the app: the `factopia_voice`
folder, the two launchers, `requirements.txt`, the README, changelog, licence
and licence register. The folders marked `export-ignore` in `.gitattributes`
are left out.

To build the zip locally: `scripts/package.sh` (writes to `dist/`).
