# PyInstaller recipe for the installed app (macOS .app and Windows folder).
# Run from the repository root:  pyinstaller packaging/factopia_voice.spec --noconfirm
# llama.cpp, FriBiDi and the licence texts are added afterwards by
# packaging/finish_app.py, so PyInstaller does not rewrite their library paths.
import os
import re
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821  (SPECPATH is set by PyInstaller)
BUILD = os.path.join(ROOT, "build")
VERSION = re.search(r'__version__ = "([^"]+)"', open(os.path.join(ROOT, "factopia_voice", "__init__.py")).read())[1]
NUMERIC = re.match(r"\d+\.\d+\.\d+", VERSION)[0]

datas = [(os.path.join(ROOT, "factopia_voice", "web"), "factopia_voice/web")]
binaries = []
hiddenimports = ["factopia_voice.workers", "factopia_voice.listeners.worker", "factopia_voice.selftest"]
for package in ("kokoro_onnx", "espeakng_loader", "phonemizer", "sherpa_onnx", "webview"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h
datas += collect_data_files("imageio_ffmpeg", include_py_files=False)

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "packaging", "entry.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "PyQt5", "PyQt6", "PySide6", "gi"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Factopia Voice",
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64" if sys.platform == "darwin" else None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(BUILD, "icon.icns" if sys.platform == "darwin" else "icon.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Factopia Voice")  # noqa: F821

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="Factopia Voice.app",
        icon=os.path.join(BUILD, "icon.icns"),
        bundle_identifier="io.github.kywatsoke.factopiavoice",
        version=NUMERIC,
        info_plist={
            "CFBundleDisplayName": "Factopia Voice",
            "CFBundleName": "Factopia Voice",
            "CFBundleShortVersionString": NUMERIC,
            "CFBundleVersion": NUMERIC,
            "LSMinimumSystemVersion": "13.0",
            "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.video",
            "NSHumanReadableCopyright": f"Factopia Voice {VERSION}",
        },
    )
