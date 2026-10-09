"""Pinned versions of the parts the installers bundle beyond Python packages.
Change a version here, then run the Installers workflow and the manual checks."""
LLAMA_TAG = "b11515"                       # llama.cpp release (llama-server for translation)
FRIBIDI_VERSION = "1.0.17"                 # FriBiDi, for Burmese text shaping in Pillow
WEBVIEW2_BOOTSTRAPPER = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"

# Which llama.cpp release file to use on each system (matched by these words).
LLAMA_ASSETS = {
    "darwin": ("macos", "arm64"),          # Metal, Apple silicon
    "win32": ("win", "vulkan", "x64"),     # Vulkan with processor fallback
    "linux": ("ubuntu", "x64"),
}
