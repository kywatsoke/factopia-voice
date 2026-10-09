"""Speech-to-text registry. To add an engine: write listeners/<name>.py with
the languages it reads, and register it here."""
from .base import Listener
from .parakeet import ParakeetListener
from .sensevoice import SenseVoiceListener

REGISTRY = {ParakeetListener.id: ParakeetListener, SenseVoiceListener.id: SenseVoiceListener}


def create_listener(listener_id="parakeet"):
    return REGISTRY[listener_id]()


def listener_for(language):
    """The recogniser for a spoken language, or None when none reads it yet."""
    for cls in REGISTRY.values():
        if language in cls.languages:
            return cls()
    return None
