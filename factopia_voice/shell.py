"""The window around the interface, and the few things only it can do:
folder pickers, showing a file in Finder or Explorer, bringing the window
forward. The interface asks for these through the local API."""
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

MODE = "browser"          # "native" (own window) or "browser"
_window = None
last_seen = None          # time of the last heartbeat from a browser window


def attach(window):
    global _window, MODE
    _window, MODE = window, "native"


def native():
    return MODE == "native" and _window is not None


def _hidden():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


def pick_folder():
    """Ask for a folder with the system's own dialog. None when cancelled or not possible."""
    if not native():
        return None
    import webview
    kind = getattr(getattr(webview, "FileDialog", None), "FOLDER", None)
    if kind is None:
        kind = getattr(webview, "FOLDER_DIALOG")
    chosen = _window.create_file_dialog(kind)
    if not chosen:
        return None
    return str(chosen[0] if isinstance(chosen, (list, tuple)) else chosen)


def reveal(path):
    """Show a file in Finder or Explorer, selected."""
    path = Path(path)
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif sys.platform == "win32":
        subprocess.Popen(["explorer", f"/select,{path}"], **_hidden())
    else:
        open_path(path.parent)


def open_path(path):
    """Open a folder (or file) with the system."""
    path = Path(path)
    if path.is_dir() or not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_url(url):
    if url.startswith("https://"):
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()


def focus():
    """Bring the window to the front (a second start of the app asks for this)."""
    if not native():
        return
    try:
        _window.restore()
        _window.show()
        _window.on_top = True
        _window.on_top = False
    except Exception:
        pass


def close():
    if native():
        try:
            _window.destroy()
        except Exception:
            pass
