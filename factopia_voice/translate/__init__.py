"""Translator registry (empty in 2.0). Register a Translator subclass here to
switch the feature on, e.g. REGISTRY["argos"] = ArgosTranslator."""
from .base import Translator

REGISTRY = {}


def get_translator(translator_id=None):
    if not REGISTRY:
        return None
    cls = REGISTRY.get(translator_id) or next(iter(REGISTRY.values()))
    return cls()
