"""Factopia Voice: an offline voiceover, captions and translation studio."""
__version__ = "3.0.0-beta.1"

from . import shaping as _shaping

_shaping.enable()          # before anything imports PIL.ImageFont; see shaping.py
