"""Translator registry. TranslateGemma on Ollama covers English, Chinese and
Burmese in every direction. Register another Translator subclass to add an engine."""
from ..config import profile_store
from .base import Translator
from .ollama import MODELS as QUALITIES, OllamaTranslator

REGISTRY = {OllamaTranslator.id: OllamaTranslator}


def get_translator(translator_id=None):
    cls = REGISTRY.get(translator_id) or next(iter(REGISTRY.values()))
    return cls(profile_store.load().get("translation_quality", "standard"))
