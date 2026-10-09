"""Speech-to-text registry. To add an engine: write listeners/<name>.py, register it here."""
from .base import Listener
from .parakeet import ParakeetListener

REGISTRY = {ParakeetListener.id: ParakeetListener}


def create_listener(listener_id="parakeet"):
    return REGISTRY[listener_id]()
