"""Fetch the pinned llama.cpp release for this system into build/vendor/llama:
llama-server and the libraries it needs, nothing else."""
import json
import os
import shutil
import sys
import urllib.request
import zipfile
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vendor import LLAMA_ASSETS, LLAMA_TAG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "build" / "llama-download"
OUT = ROOT / "build" / "vendor" / "llama"
API = f"https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{LLAMA_TAG}"
LIBS = (".dylib", ".dll", ".so", ".metal")


def pick(assets):
    words = LLAMA_ASSETS["linux" if sys.platform.startswith("linux") else sys.platform]
    avoid = () if "vulkan" in words else ("vulkan", "rocm", "cuda", "hip", "sycl", "openvino", "kompute")
    for a in assets:
        name = a["name"].lower()
        if name.endswith((".zip", ".tar.gz")) and all(w in name for w in words) and not any(x in name for x in avoid) \
                and "cudart" not in name:
            return a
    sys.exit(f"No llama.cpp file matches {words}: {[a['name'] for a in assets]}")


def main():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "FactopiaVoice-build"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(API, headers=headers), timeout=60) as r:
        asset = pick(json.loads(r.read())["assets"])
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    archive = WORK / asset["name"]
    print("Downloading", asset["name"], flush=True)
    urllib.request.urlretrieve(asset["browser_download_url"], archive)
    unpacked = WORK / "unpacked"
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(unpacked)
    else:
        with tarfile.open(archive) as t:
            t.extractall(unpacked, filter="data")
    exe = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    server = next(unpacked.rglob(exe))
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    for f in server.parent.iterdir():
        if f.is_file() and (f.name == exe or f.suffix in LIBS or ".so." in f.name or f.name.upper().startswith("LICENSE")):
            shutil.copy2(f, OUT / f.name, follow_symlinks=True)
    if sys.platform != "win32":
        os.chmod(OUT / exe, 0o755)
    (OUT / "SOURCE.txt").write_text(f"llama.cpp {LLAMA_TAG} ({asset['name']})\n"
                                    f"https://github.com/ggml-org/llama.cpp/releases/tag/{LLAMA_TAG}\n", encoding="utf-8")
    print("llama.cpp ready:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
