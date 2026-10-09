"""Checking GitHub for a newer version (at most once a day, only when allowed
in Settings). Nothing is sent except the request itself."""
import json
import os
import re
import time
import urllib.request

from . import __version__
from .config import CACHE

REPO = os.environ.get("FACTOPIA_VOICE_RELEASES", "kywatsoke/factopia")
API = os.environ.get("FACTOPIA_VOICE_RELEASES_API", f"https://api.github.com/repos/{REPO}/releases?per_page=20")
CACHE_FILE = CACHE / "update.json"
DAY = 24 * 3600


def parse(version):
    """'v3.0.1' -> (3, 0, 1, 1, 0); '3.0.0-beta.2' -> (3, 0, 0, 0, 2). Releases sort after their betas."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)(?:-[a-z]+\.?(\d+))?", (version or "").strip().lower())
    if not m:
        return (0, 0, 0, 0, 0)
    pre = m.group(4)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if pre is not None else 1, int(pre or 0))


def check(force=False):
    if not force:
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() - cached.get("checked", 0) < DAY and cached.get("current") == __version__:
                return cached
        except (OSError, ValueError):
            pass
    current = parse(__version__)
    want_betas = current[3] == 0
    try:
        req = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json", "User-Agent": "FactopiaVoice"})
        with urllib.request.urlopen(req, timeout=8) as r:
            releases = json.loads(r.read())
    except Exception:
        return {"current": __version__, "error": "Could not check for updates.", "newer": False}
    candidates = [r for r in releases if not r.get("draft") and (want_betas or not r.get("prerelease"))]
    best = max(candidates, key=lambda r: parse(r.get("tag_name")), default=None)
    result = {"current": __version__, "checked": time.time(), "newer": False}
    if best:
        result.update(latest=best["tag_name"].lstrip("v"), url=best.get("html_url", ""),
                      newer=parse(best["tag_name"]) > current)
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(result), encoding="utf-8")
    except OSError:
        pass
    return result
