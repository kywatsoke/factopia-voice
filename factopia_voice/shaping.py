"""Burmese needs complex text shaping (letters reordered and joined as they are
drawn). Pillow does it with its built-in raqm layout, but on macOS and Windows
raqm only works when the FriBiDi library can be found, and Pillow's wheels do
not include it. The installed app ships FriBiDi; this makes Pillow find it.

Pillow looks for FriBiDi once, when PIL._imagingft is first imported, by bare
file name: "libfribidi.dylib" on macOS (dlopen also searches the current
folder) and "fribidi" / "fribidi-0" on Windows (LoadLibrary first reuses a
library of that name that is already loaded). So: load our copy, step into its
folder, import PIL._imagingft, step back. Must run before anything imports
PIL.ImageFont, which is why the package imports this module first."""
import ctypes
import os
import sys
from pathlib import Path

NAMES = {"darwin": "libfribidi.dylib", "win32": "fribidi-0.dll"}
loaded = None          # path of the FriBiDi library in use, if this module supplied it


def _candidates():
    name = NAMES.get(sys.platform)
    if not name:
        return []
    found = []
    custom = os.environ.get("FACTOPIA_VOICE_FRIBIDI")
    if custom:
        found.append(Path(custom))
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        found += [base / "fribidi" / name, base / name,
                  Path(sys.executable).resolve().parent.parent / "Frameworks" / "fribidi" / name,
                  Path(sys.executable).resolve().parent.parent / "Resources" / "fribidi" / name]
    return [p for p in found if p.is_file()]


def enable():
    """Make Pillow's raqm layout use the bundled FriBiDi. Safe to call more than once."""
    global loaded
    if loaded or "PIL._imagingft" in sys.modules:
        return loaded
    for lib in _candidates():
        try:
            if sys.platform == "win32":
                ctypes.WinDLL(str(lib))
            else:
                ctypes.CDLL(str(lib), mode=getattr(os, "RTLD_GLOBAL", 0))
        except OSError:
            continue
        here = os.getcwd()
        try:
            os.chdir(lib.parent)
            from PIL import _imagingft  # noqa: F401  (finds FriBiDi now, once)
        except Exception:
            pass
        finally:
            os.chdir(here)
        loaded = str(lib)
        break
    return loaded


def status():
    """What the drawing library can do, for the self-test and the About screen."""
    try:
        from PIL import features
        return {"raqm": bool(features.check("raqm")), "fribidi": features.version("fribidi"),
                "harfbuzz": features.version("harfbuzz"), "bundled_fribidi": loaded}
    except Exception as e:          # pragma: no cover
        return {"raqm": False, "error": str(e), "bundled_fribidi": loaded}
