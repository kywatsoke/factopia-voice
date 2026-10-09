"""The contract for a speech-to-text engine. Parakeet is the first; a
multilingual engine can be added as another file without touching the rest."""
from abc import ABC, abstractmethod


class Listener(ABC):
    id = ""
    name = ""
    license = ""
    languages = ()

    @abstractmethod
    def ready(self, models_dir):
        """True when the model files are on disk."""

    @abstractmethod
    def install(self, models_dir, on_progress):
        """Download the model files. on_progress(percent, detail)."""

    @abstractmethod
    def transcribe(self, wav_path, models_dir, on_progress):
        """Return [{"text", "start"}] words with start times in seconds."""
