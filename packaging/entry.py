"""Entry point for the packed app (PyInstaller)."""
import sys

from factopia_voice.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
