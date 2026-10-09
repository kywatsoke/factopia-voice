"""Helper processes. Speech recognition runs in its own process so its memory
(about 1 GB) is returned when it finishes and its runtime never clashes with
the voice engine's. The installed app has no separate Python, so the app
starts itself again with --fv-worker; from source it runs this module.

Progress and errors travel through small files next to the output, not through
stdout, because the installed Windows app has no console."""
import sys
import traceback
from pathlib import Path

from .config import FROZEN, ROOT


def command(*args):
    if FROZEN:
        return [sys.executable, "--fv-worker", *map(str, args)]
    return [sys.executable, "-m", "factopia_voice.workers", *map(str, args)]


def workdir():
    return str(ROOT)


def main(argv):
    kind, rest = argv[0], argv[1:]
    out = Path(rest[-1])
    try:
        if kind == "ping":
            out.write_text("pong", encoding="utf-8")
        elif kind == "listen":
            from .listeners.worker import run
            run(*rest)
        else:
            raise ValueError(f"Unknown worker: {kind}")
        return 0
    except Exception as e:
        traceback.print_exc()
        Path(str(out) + ".error").write_text(f"{type(e).__name__}: {e}", encoding="utf-8")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
