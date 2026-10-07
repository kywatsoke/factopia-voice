"""Find the fonts installed on this computer so captions can use any of them."""
import json
import os
import sys
from pathlib import Path

from .config import CACHE

PREFERRED = [("Arial Black", ""), ("Impact", ""), ("Helvetica Neue", "Bold"), ("Arial", "Bold"),
             ("Segoe UI", "Bold"), ("DejaVu Sans", "Bold"), ("Liberation Sans", "Bold")]
_fonts = None


def folders():
    home = Path.home()
    if sys.platform == "darwin":
        return [Path("/System/Library/Fonts"), Path("/Library/Fonts"), home / "Library/Fonts"]
    if sys.platform == "win32":
        return [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
                Path(os.environ.get("LOCALAPPDATA", str(home))) / "Microsoft/Windows/Fonts"]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), home / ".fonts", home / ".local/share/fonts"]


def scan():
    from PIL import ImageFont
    found = {}
    for folder in folders():
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                continue
            for index in range(24 if path.suffix.lower() == ".ttc" else 1):
                try:
                    family, style = ImageFont.truetype(str(path), 20, index=index).getname()
                except Exception:
                    break
                if not family or family.startswith(".") or "LastResort" in family:
                    continue
                style = "" if (style or "").lower() == "regular" else (style or "")
                found.setdefault(f"{family}|{style}", {"id": f"{family}|{style}", "family": family, "style": style,
                                                      "label": f"{family} {style}".strip(), "path": str(path), "index": index})
    return sorted(found.values(), key=lambda f: (f["family"].lower(), f["style"].lower()))


def all_fonts(refresh=False):
    global _fonts
    cache = CACHE / "fonts.json"
    if _fonts is None and not refresh and cache.is_file():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if data and all(os.path.exists(f["path"]) for f in data[:5]):
                _fonts = data
        except Exception:
            pass
    if _fonts is None or refresh:
        _fonts = scan()
        try:
            CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(_fonts), encoding="utf-8")
        except OSError:
            pass
    return _fonts


def find(font_id):
    fonts = all_fonts()
    by_id = {f["id"]: f for f in fonts}
    if font_id in by_id:
        return by_id[font_id]
    for family, style in PREFERRED:
        if f"{family}|{style}" in by_id:
            return by_id[f"{family}|{style}"]
    if not fonts:
        raise RuntimeError("No fonts were found on this computer.")
    return fonts[0]


def default_id():
    return find("")["id"]
