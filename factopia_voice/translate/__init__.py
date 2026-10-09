"""Translator registry. Two engines run the same TranslateGemma model:

- builtin: llama.cpp inside the installed app; the model downloads in the app.
- ollama:  the separate Ollama app, for people who already use it.

"auto" (the default) uses the built-in engine when it is present."""
from ..config import profile_store
from . import llamacpp, ollama
from .base import Translator
from .llamacpp import BuiltinTranslator
from .ollama import OllamaTranslator

REGISTRY = {BuiltinTranslator.id: BuiltinTranslator, OllamaTranslator.id: OllamaTranslator}
ENGINES = {"auto": "Automatic", "builtin": "Built in (no extra app)", "ollama": "Ollama app"}


def engine_choice(profile=None):
    choice = (profile or profile_store.load()).get("translation_engine", "auto")
    if choice not in REGISTRY:
        choice = "builtin" if llamacpp.server_command() else "ollama"
    return choice


def qualities(engine_id):
    if engine_id == "ollama":
        return {k: {"model": m, "size": size} for k, (m, size) in ollama.MODELS.items()}
    return {k: {"model": spec.label, "size": llamacpp.size_label(spec.size)} for k, spec in llamacpp.MODELS_AVAILABLE.items()}


def get_translator(translator_id=None):
    profile = profile_store.load()
    cls = REGISTRY.get(translator_id) or REGISTRY[engine_choice(profile)]
    return cls(profile.get("translation_quality", "standard"))


def shutdown():
    llamacpp.SERVER.stop()
