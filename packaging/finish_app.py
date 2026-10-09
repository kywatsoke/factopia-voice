"""After PyInstaller: add llama.cpp, FriBiDi and the licence texts to the app,
then make the installer: Factopia-Voice-Mac.dmg or Factopia-Voice-Windows-Setup.exe
in dist/. Run from the repository root after packaging/factopia_voice.spec."""
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vendor import WEBVIEW2_BOOTSTRAPPER  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VENDOR = ROOT / "build" / "vendor"
VERSION = re.search(r'__version__ = "([^"]+)"', (ROOT / "factopia_voice" / "__init__.py").read_text())[1]
NUMERIC = re.match(r"\d+\.\d+\.\d+", VERSION)[0]

MAC_NOTE = """Factopia Voice for Mac (Apple silicon)

1. Drag Factopia Voice onto the Applications folder.
2. Open Applications and double-click Factopia Voice.
3. The first time, macOS says it cannot check the app for malware, because
   it is shared for free without an Apple developer certificate. Click Done.
   Then open System Settings > Privacy & Security, scroll down to the
   message about Factopia Voice, click Open Anyway, and confirm.

Step 3 is only needed once.
"""


def run(*args, **kw):
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run([str(a) for a in args], check=True, **kw)


def copy_vendor(base, licences):
    for part in ("llama", "fribidi"):
        src = VENDOR / part
        if not src.is_dir():
            sys.exit(f"Missing {src}: run packaging/fetch_llama.py and packaging/build_fribidi.py first.")
        shutil.rmtree(base / part, ignore_errors=True)
        shutil.copytree(src, base / part, symlinks=False)
    shutil.rmtree(licences, ignore_errors=True)
    shutil.copytree(VENDOR / "licenses", licences)


def is_macho(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca")
    except OSError:
        return False


def mac():
    app = DIST / "Factopia Voice.app"
    frameworks = app / "Contents" / "Frameworks"
    copy_vendor(frameworks, app / "Contents" / "Resources" / "licenses")
    for part in ("llama", "fribidi"):
        for f in sorted((frameworks / part).iterdir()):
            if f.is_file() and is_macho(f):
                run("codesign", "--force", "--sign", "-", "--timestamp=none", f)
    run("codesign", "--force", "--deep", "--sign", "-", "--timestamp=none", app)
    run("codesign", "--verify", "--deep", "--strict", "--verbose=2", app)
    stage = ROOT / "build" / "dmg"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    run("ditto", app, stage / app.name)
    os.symlink("/Applications", stage / "Applications")
    (stage / "How to open the first time.txt").write_text(MAC_NOTE, encoding="utf-8")
    dmg = DIST / "Factopia-Voice-Mac.dmg"
    dmg.unlink(missing_ok=True)
    run("hdiutil", "create", "-volname", "Factopia Voice", "-srcfolder", stage, "-ov", "-format", "UDZO",
        "-imagekey", "zlib-level=9", dmg)
    print(f"Built {dmg} ({dmg.stat().st_size / 1e6:.0f} MB)")


def find_iscc():
    found = shutil.which("ISCC") or shutil.which("iscc")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        for name in ("Inno Setup 7", "Inno Setup 6", r"Programs\Inno Setup 7", r"Programs\Inno Setup 6"):
            candidate = Path(base or "") / name / "ISCC.exe"
            if candidate.is_file():
                return str(candidate)
    sys.exit("Inno Setup (ISCC.exe) not found.")


def windows():
    folder = DIST / "Factopia Voice"
    internal = folder / "_internal"
    copy_vendor(internal, internal / "licenses")
    bootstrapper = VENDOR / "MicrosoftEdgeWebview2Setup.exe"
    if not bootstrapper.exists():
        urllib.request.urlretrieve(WEBVIEW2_BOOTSTRAPPER, bootstrapper)
    run(find_iscc(), f"/DAppVersion={VERSION}", f"/DNumericVersion={NUMERIC}",
        str(ROOT / "packaging" / "windows" / "installer.iss"))
    setup = DIST / "Factopia-Voice-Windows-Setup.exe"
    print(f"Built {setup} ({setup.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    mac() if sys.platform == "darwin" else windows()
