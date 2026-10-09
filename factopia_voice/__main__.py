"""Start Factopia Voice.

    python -m factopia_voice            the app in its own window
    python -m factopia_voice --browser  the app in the web browser instead

The installed app runs the same code. It also starts itself with
--fv-worker (helper processes) and --self-test (build checks)."""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request

from .net import open_url


def _redirect_output():
    """The installed app has no terminal: keep what it prints in a log file."""
    from .config import LOGS
    try:
        LOGS.mkdir(parents=True, exist_ok=True)
        log = LOGS / "factopia-voice.log"
        if log.exists() and log.stat().st_size > 5_000_000:
            log.replace(LOGS / "factopia-voice.old.log")
        stream = open(log, "a", encoding="utf-8", buffering=1, errors="replace")
        sys.stdout = sys.stderr = stream
    except OSError:
        pass


def _answering(port):
    try:
        with open_url(f"http://127.0.0.1:{port}/api/state", timeout=1.5) as r:
            return b'"version"' in r.read()
    except Exception:
        return False


def _port_free(port):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _app_browsers():
    """Chrome or Edge can show the interface in a clean window (no tabs, no address bar)."""
    if sys.platform == "darwin":
        return ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"]
    if sys.platform == "win32":
        roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        tails = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"]
        return [os.path.join(r, t) for t in tails for r in roots if r]
    return []


def open_browser_window(url):
    import webbrowser
    if os.environ.get("FACTOPIA_VOICE_NO_WINDOW"):
        return
    if os.environ.get("FACTOPIA_VOICE_BROWSER") != "default":
        for exe in _app_browsers():
            if os.path.exists(exe):
                try:
                    subprocess.Popen([exe, f"--app={url}", "--window-size=1180,820"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except OSError:
                    pass
    webbrowser.open(url)


def _post(url):
    try:
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"})
        open_url(req, timeout=2).close()
    except Exception:
        pass


def run_native(url):
    """The interface in the app's own window. Returns when the window closes."""
    import webview

    from . import shell
    from .config import APP_NAME, DATA
    webview.settings.update({"OPEN_EXTERNAL_LINKS_IN_BROWSER": True, "ALLOW_DOWNLOADS": True})
    window = webview.create_window(APP_NAME, url, width=1180, height=820, min_size=(940, 640),
                                   background_color="#f5f3ee", text_select=True)
    shell.attach(window)
    webview.start(private_mode=False, storage_path=str(DATA / "window"),
                  debug=bool(os.environ.get("FACTOPIA_VOICE_DEBUG")))


def _watchdog(server):
    """In a browser tab there is no window to close: stop when the page has
    been gone for a minute (it checks in every 10 seconds)."""
    from . import shell
    while True:
        time.sleep(15)
        if shell.last_seen and time.time() - shell.last_seen > 60:
            server.shutdown()
            return


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--fv-worker"]:
        from .workers import main as worker_main
        return worker_main(argv[1:])
    if argv[:1] == ["--self-test"]:
        from .selftest import main as selftest_main
        return selftest_main(argv[1:])

    from .config import FROZEN, PORT
    if FROZEN:
        _redirect_output()
    from . import __version__

    from .config import DATA
    running_file = DATA / "running.json"
    try:
        last_port = int(json.loads(running_file.read_text(encoding="utf-8")).get("port") or 0)
    except (OSError, ValueError, AttributeError):
        last_port = 0
    for port in dict.fromkeys(p for p in (PORT, last_port) if p):
        if _answering(port):
            print("Factopia Voice is already running; bringing its window forward.")
            _post(f"http://127.0.0.1:{port}/api/focus")
            return 0

    from . import shell, storage
    from .config import ensure_dirs
    ensure_dirs()
    storage.finish_move()
    from .server import begin, make_server
    from .translate import shutdown as stop_translation
    try:
        server = make_server(PORT if _port_free(PORT) else 0)
    except OSError:
        sys.exit("Factopia Voice could not open its local port. Set FACTOPIA_VOICE_PORT to another number.")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    print(f"Factopia Voice {__version__} is running at {url}", flush=True)
    try:                                     # so a second start finds this copy even on another port
        running_file.write_text(json.dumps({"port": server.server_address[1], "pid": os.getpid()}), encoding="utf-8")
    except OSError:
        pass
    begin()

    want_window = "--browser" not in argv and os.environ.get("FACTOPIA_VOICE_WINDOW") != "browser"
    try:
        if want_window:
            try:
                run_native(url)
                return 0
            except Exception as e:                       # no window toolkit: use the browser instead
                print(f"The app window could not open ({e}); using the web browser.", flush=True)
                shell.MODE = "browser"
        open_browser_window(url)
        if FROZEN:
            threading.Thread(target=_watchdog, args=(server,), daemon=True).start()
        else:
            print("Keep this window open while you work. Use Quit in the app, or close this window, to stop.\n")
        while serving.is_alive():               # until Quit in the app (or the watchdog) stops the server
            serving.join(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        stop_translation()
        server.shutdown()
        try:
            running_file.unlink()
        except OSError:
            pass
        print("Factopia Voice stopped.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
