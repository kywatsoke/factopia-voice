"""Model downloads: progress, resume after an interrupted connection, and an
integrity check when the expected SHA-256 is known."""
import hashlib
import os
import time
import urllib.error
import urllib.request

USER_AGENT = "FactopiaVoice"


def missing(files, folder):
    return [f for f in files if not ((folder / f.name).exists() and (folder / f.name).stat().st_size >= f.size * 0.98)]


def fetch(files, folder, on_progress=lambda done, total, name: None):
    """Download every file in `files` (ModelFile) that is not in `folder` yet."""
    todo = missing(files, folder)
    total = sum(f.size for f in todo)
    base = 0
    for f in todo:
        fetch_one(f.url, folder / f.name, f.size, getattr(f, "sha256", None),
                  lambda done, size, b=base, n=f.name: on_progress(b + done, total, n))
        base += f.size


def fetch_one(url, dest, size=0, sha256=None, on_progress=lambda done, total: None, attempts=6):
    """Download one file to `dest`, continuing a partial .part file where possible."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for attempt in range(attempts):
        have = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": USER_AGENT}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                if have and r.status != 206:          # the server ignored the range: start again
                    have = 0
                length = int(r.headers.get("Content-Length") or 0)
                total = size or (have + length)
                with open(part, "ab" if have else "wb") as out:
                    done = have
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
                        done += len(chunk)
                        on_progress(done, total)
            break
        except urllib.error.HTTPError as e:
            if e.code == 416 and part.exists():      # already complete
                break
            if e.code in (401, 403, 404) or attempt == attempts - 1:
                raise IOError(f"The download failed ({e.code}). Check the connection and try again.")
        except (urllib.error.URLError, OSError, TimeoutError):
            if attempt == attempts - 1:
                raise IOError("The download keeps stopping. Check the connection and try again; it will continue "
                              "where it left off.")
        time.sleep(min(30, 2 ** attempt))
    got = part.stat().st_size if part.exists() else 0
    if size and got < size * 0.98:
        raise IOError(f"The download of {dest.name} is incomplete. Try again; it will continue where it left off.")
    if sha256:
        digest = hashlib.sha256()
        with open(part, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 22), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != sha256.lower():
            part.unlink(missing_ok=True)
            raise IOError(f"The downloaded {dest.name} is damaged. Try again.")
    os.replace(part, dest)
    return dest
