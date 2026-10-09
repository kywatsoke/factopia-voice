"""Build FriBiDi (LGPL-2.1-or-later) from its release source into
build/vendor/fribidi, named the way Pillow looks for it (see shaping.py).
Needs meson and ninja; on Windows run inside a Visual Studio developer shell."""
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vendor import FRIBIDI_VERSION  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "fribidi-src"
OUT = ROOT / "build" / "vendor" / "fribidi"
URL = f"https://github.com/fribidi/fribidi/releases/download/v{FRIBIDI_VERSION}/fribidi-{FRIBIDI_VERSION}.tar.xz"


def run(*args, **kw):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run([str(a) for a in args], check=True, **kw)


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    archive = WORK / "fribidi.tar.xz"
    urllib.request.urlretrieve(URL, archive)
    with tarfile.open(archive) as tar:
        tar.extractall(WORK, filter="data")
    src = WORK / f"fribidi-{FRIBIDI_VERSION}"
    env = dict(os.environ)
    if sys.platform == "darwin":
        env["MACOSX_DEPLOYMENT_TARGET"] = "11.0"
    run(sys.executable, "-m", "mesonbuild.mesonmain", "setup", src / "build", src, "--buildtype=release",
        "-Ddocs=false", "-Dtests=false", "-Dbin=false", "-Ddefault_library=shared", env=env)
    run(sys.executable, "-m", "mesonbuild.mesonmain", "compile", "-C", src / "build", env=env)
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    built = src / "build" / "lib"
    if sys.platform == "darwin":
        lib = next(p for p in built.glob("libfribidi*.dylib") if not p.is_symlink())
        target = OUT / "libfribidi.dylib"
        shutil.copy2(lib, target)
        run("install_name_tool", "-id", "@rpath/libfribidi.dylib", target)
        run("codesign", "--force", "--sign", "-", target)
    elif sys.platform == "win32":
        lib = next(built.glob("*fribidi*.dll"))
        shutil.copy2(lib, OUT / "fribidi-0.dll")
    else:
        sys.exit("FriBiDi is only bundled for macOS and Windows (Pillow on Linux has it).")
    shutil.copy2(src / "COPYING", OUT / "COPYING")
    print("FriBiDi ready:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
