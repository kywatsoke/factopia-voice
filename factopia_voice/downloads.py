"""One-time model download with resumable-safe temp files and progress."""
import urllib.request


def missing(files, folder):
    return [f for f in files if not ((folder / f.name).exists() and (folder / f.name).stat().st_size >= f.size * 0.98)]


def fetch(files, folder, on_progress=lambda done, total, name: None):
    todo = missing(files, folder)
    total = sum(f.size for f in todo)
    done = 0
    for f in todo:
        tmp = folder / (f.name + ".part")
        req = urllib.request.Request(f.url, headers={"User-Agent": "FactopiaVoice"})
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as out:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                on_progress(done, total, f.name)
        if tmp.stat().st_size < f.size * 0.98:
            tmp.unlink(missing_ok=True)
            raise IOError(f"Download of {f.name} was incomplete. Check the connection and start again.")
        tmp.replace(folder / f.name)
