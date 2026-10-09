"""Start Factopia Voice: python -m factopia_voice"""
import os
import subprocess
import sys
import threading
import urllib.request
import webbrowser

from . import __version__
from .config import PORT, ensure_dirs

URL = f"http://127.0.0.1:{PORT}"


def already_running():
    try:
        with urllib.request.urlopen(URL + "/api/state", timeout=1.5) as r:
            return b'"version"' in r.read()
    except Exception:
        return False


def app_browsers():
    """Chrome or Edge can show the interface in its own clean window (no tabs, no address bar)."""
    if sys.platform == "darwin":
        return ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"]
    if sys.platform == "win32":
        roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        tails = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"]
        return [os.path.join(r, t) for t in tails for r in roots if r]
    return []


def open_window():
    if os.environ.get("FACTOPIA_VOICE_NO_WINDOW"):
        return
    if os.environ.get("FACTOPIA_VOICE_BROWSER") != "default":
        for exe in app_browsers():
            if os.path.exists(exe):
                try:
                    subprocess.Popen([exe, f"--app={URL}", "--window-size=1180,820"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except OSError:
                    pass
    webbrowser.open(URL)


def main():
    if already_running():
        print("Factopia Voice is already running. Opening its window.")
        return open_window()
    ensure_dirs()
    from .server import make_server, studio
    try:
        server = make_server()
    except OSError:
        sys.exit(f"Port {PORT} is being used by another program. Close it, or set FACTOPIA_VOICE_PORT to another number.")
    print(f"Factopia Voice {__version__} is running at {URL}")
    print("Keep this window open while you work. Use Quit in the app, or close this window, to stop.\n")
    studio.start()
    threading.Timer(0.6, open_window).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    print("Factopia Voice stopped.")


if __name__ == "__main__":
    main()
