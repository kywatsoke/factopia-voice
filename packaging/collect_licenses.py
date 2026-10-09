"""Gather the licence texts of everything the installers bundle into
build/vendor/licenses, plus SOURCES.md saying where the source code of the
GPL and LGPL parts is. Run in the same Python that builds the app."""
import importlib.metadata as md
import platform
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vendor import FRIBIDI_VERSION, LLAMA_TAG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "build" / "vendor"
OUT = VENDOR / "licenses"
NAMES = re.compile(r"(LICEN[CS]E|COPYING|NOTICE|AUTHORS)", re.I)
BUILD_ONLY = {"pip", "setuptools", "wheel", "meson", "ninja"}


def version(name):
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return "not installed"


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    for dist in md.distributions():
        name = dist.metadata["Name"]
        if not name or name.lower() in BUILD_ONLY:
            continue
        target = OUT / f"{name}-{dist.version}"
        found = [f for f in (dist.files or []) if NAMES.search(f.name) and f.suffix not in (".py", ".pyc")]
        for f in found:
            src = Path(dist.locate_file(f))
            if src.is_file():
                target.mkdir(exist_ok=True)
                shutil.copy2(src, target / f.name)
        if not found:
            target.mkdir(exist_ok=True)
            meta = dist.metadata
            classifiers = [c for c in (meta.get_all("Classifier") or []) if c.startswith("License")]
            (target / "LICENSE-INFO.txt").write_text(
                f"{name} {dist.version}\nLicense: {meta.get('License-Expression') or meta.get('License') or ''}\n"
                + "\n".join(classifiers) + f"\nHome page: {meta.get('Home-page') or meta.get('Project-URL') or ''}\n",
                encoding="utf-8")
    for src, dest in ((ROOT / "LICENSE", "Factopia Voice LICENSE.txt"),
                      (ROOT / "THIRD_PARTY_LICENSES.md", "THIRD_PARTY_LICENSES.md"),
                      (VENDOR / "fribidi" / "COPYING", f"FriBiDi-{FRIBIDI_VERSION}/COPYING")):
        if src.is_file():
            (OUT / dest).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, OUT / dest)
    for lic in (VENDOR / "llama").glob("LICENSE*") if (VENDOR / "llama").is_dir() else []:
        (OUT / f"llama.cpp-{LLAMA_TAG}").mkdir(exist_ok=True)
        shutil.copy2(lic, OUT / f"llama.cpp-{LLAMA_TAG}" / lic.name)

    (OUT / "SOURCES.md").write_text(f"""# Where to get the source code

Factopia Voice bundles the parts below unchanged. Their source code, for the
exact versions in this build, is available here.

| Part | Version | Licence | Source |
| --- | --- | --- | --- |
| Factopia Voice | see the app's About screen | see Factopia Voice LICENSE.txt | https://github.com/kywatsoke/factopia |
| phonemizer | {version('phonemizer')} | GPL-3.0-or-later | https://pypi.org/project/phonemizer/{version('phonemizer')}/#files |
| eSpeak NG (inside espeakng-loader) | espeakng-loader {version('espeakng-loader')} | GPL-3.0-or-later | https://github.com/thewh1teagle/espeakng-loader and https://github.com/espeak-ng/espeak-ng |
| FFmpeg (inside imageio-ffmpeg) | imageio-ffmpeg {version('imageio-ffmpeg')} | GPL (this build) | https://github.com/imageio/imageio-ffmpeg (build notes) and https://ffmpeg.org/download.html#get-sources |
| FriBiDi | {FRIBIDI_VERSION} | LGPL-2.1-or-later | https://github.com/fribidi/fribidi/releases/tag/v{FRIBIDI_VERSION} |
| libsndfile (inside soundfile) | soundfile {version('soundfile')} | LGPL-2.1-or-later | https://github.com/libsndfile/libsndfile |
| llama.cpp | {LLAMA_TAG} | MIT | https://github.com/ggml-org/llama.cpp/releases/tag/{LLAMA_TAG} |
| PyInstaller bootloader | {version('pyinstaller')} | GPL-2.0 with bootloader exception | https://github.com/pyinstaller/pyinstaller |
| Python | {platform.python_version()} | PSF-2.0 | https://www.python.org/downloads/source/ |

The FriBiDi library is a separate file in the app (libfribidi.dylib or
fribidi-0.dll) and can be replaced with another build of the same version.

The AI models are not part of the installer. The app downloads them when
first needed; their terms are shown on the welcome screen and in Settings >
About and licences.
""", encoding="utf-8")
    print(f"Licences gathered: {len(list(OUT.iterdir()))} entries in {OUT}")


if __name__ == "__main__":
    main()
