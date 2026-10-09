# Building the installers

The **Installers** workflow (`.github/workflows/installers.yml`) does all of
this on GitHub's Mac and Windows machines. Build by hand only to debug.

| Output | Built on | Contains |
| --- | --- | --- |
| `dist/Factopia-Voice-Mac.dmg` | macOS, Apple silicon | `Factopia Voice.app` (arm64, macOS 13+), an Applications link, a first-open note |
| `dist/Factopia-Voice-Windows-Setup.exe` | Windows x64 | Per-user Inno Setup installer, WebView2 bootstrapper when missing |

## Steps

Run from the repository root with a Python 3.12 environment:

```bash
uv venv --python 3.12 .venv-build
uv pip install --python .venv-build/bin/python -r requirements.txt -r packaging/requirements-build.txt
PY=.venv-build/bin/python            # Windows: .venv-build/Scripts/python.exe

$PY packaging/make_icons.py          # build/icon.png, .icns, .ico
$PY packaging/fetch_llama.py         # build/vendor/llama: llama-server and its libraries
$PY packaging/build_fribidi.py       # build/vendor/fribidi (Windows: in a Visual Studio developer shell)
$PY packaging/collect_licenses.py    # build/vendor/licenses and SOURCES.md
$PY -m PyInstaller packaging/factopia_voice.spec --noconfirm --distpath dist --workpath build/pyinstaller
$PY packaging/finish_app.py          # adds llama.cpp, FriBiDi and licences; makes the .dmg or Setup.exe
```

Then check the packed app:

```bash
"dist/Factopia Voice.app/Contents/MacOS/Factopia Voice" --self-test result.json   # Mac
"dist/Factopia Voice/Factopia Voice.exe" --self-test result.json                 # Windows
$PY packaging/report_selftest.py result.json "local"
```

With `FV_SELFTEST_VOICE` and `FV_SELFTEST_SPEECH` set to a folder made by
`packaging/fetch_test_models.py`, the self-test also speaks a sentence and
hears it back.

## Files

| File | Job |
| --- | --- |
| `vendor.py` | Pinned versions: llama.cpp release, FriBiDi, the WebView2 bootstrapper link |
| `requirements-build.txt` | PyInstaller, pywebview, meson and ninja, pinned |
| `entry.py` | The packed app's entry point |
| `factopia_voice.spec` | PyInstaller recipe (which packages and data files go in) |
| `fetch_llama.py` | Downloads the llama.cpp release for this system (Metal on Mac, Vulkan with processor fallback on Windows) |
| `build_fribidi.py` | Builds FriBiDi from source, named the way Pillow looks for it |
| `collect_licenses.py` | Gathers licence texts and where to get the source of GPL and LGPL parts |
| `finish_app.py` | Adds the vendor parts after PyInstaller, signs the Mac app ad hoc, makes the installer |
| `windows/installer.iss` | Inno Setup script: per-user install, Start menu and desktop icons, uninstall asks about the models |
| `make_icons.py` | Draws the app icon in every size |
| `fetch_test_models.py`, `report_selftest.py`, `ci_run.sh` | Helpers for the workflow |

## Changing a bundled part

1. Change the pin in `vendor.py` or `requirements-build.txt`.
2. Run the Installers workflow and read its notices: each self-test check is
   listed with its result.
3. Record the change in `THIRD_PARTY_LICENSES.md` and, for an engine, in
   `docs/DECISIONS.md`.

## Signing

The apps are not signed with a paid certificate, so macOS and Windows warn
the first time (the README explains the one click). The Mac app is signed
ad hoc, which Apple silicon requires to run at all. A paid Apple Developer ID
(notarisation) or a Windows code-signing certificate would remove the
warnings; nothing else would change.
