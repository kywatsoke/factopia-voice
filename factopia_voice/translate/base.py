"""The contract for a translator. None ships in version 2.0; the pipeline already
calls this interface, so adding translation later needs no changes elsewhere."""
from abc import ABC, abstractmethod


class Translator(ABC):
    id = ""
    name = ""

    @abstractmethod
    def languages(self):
        """Return [(source_code, target_code), ...] pairs this translator supports."""

    @abstractmethod
    def translate(self, text, source, target):
        """Return the translated text."""
