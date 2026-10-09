"""The contract for a translator. The pipeline and the captions editor call
only this, so the engine behind it can change without touching them."""
from abc import ABC, abstractmethod


class Translator(ABC):
    id = ""
    name = ""

    @abstractmethod
    def status(self):
        """{"ready": bool, "message": str, ...} describing whether translation can run now."""

    @abstractmethod
    def setup(self, on_progress):
        """Do whatever is needed to become ready (start the engine, download the model)."""

    @abstractmethod
    def translate(self, text, source, target):
        """Return the translated text. source and target are codes from languages.LANGUAGES."""

    def translate_many(self, texts, source, target, on_progress=lambda done, total: None):
        out = []
        for i, text in enumerate(texts):
            out.append(self.translate(text, source, target) if text.strip() else text)
            on_progress(i + 1, len(texts))
        return out
