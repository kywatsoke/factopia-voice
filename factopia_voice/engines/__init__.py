"""Engine registry. To add an engine: write engines/<name>.py, then add it here."""
from .base import Engine, ModelFile, Voice
from .kokoro import KokoroEngine

REGISTRY = {KokoroEngine.id: KokoroEngine}


def create_engine(engine_id):
    if engine_id not in REGISTRY:
        raise ValueError(f"Unknown engine: {engine_id}")
    return REGISTRY[engine_id]()
