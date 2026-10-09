"""The contract for a translator. The pipeline and the captions editor call
only this, so the engine behind it can change without touching them."""
from abc import ABC, abstractmethod

# Google's official TranslateGemma prompt.
PROMPT = ("You are a professional {sl} ({sc}) to {tl} ({tc}) translator. Your goal is to accurately convey the "
          "meaning and nuances of the original {sl} text while adhering to {tl} grammar, vocabulary, and cultural "
          "sensitivities.\nProduce only the {tl} translation, without any additional explanations or commentary. "
          "Please translate the following {sl} text into {tl}:\n\n\n{text}")
_PAIRS = {'"': '"', "'": "'", "“": "”", "‘": "’", "「": "」"}


def prompt_for(text, source, target):
    from ..languages import LANGUAGES
    s, t = LANGUAGES[source], LANGUAGES[target]
    return PROMPT.format(sl=s["name"], sc=s["code"], tl=t["name"], tc=t["code"], text=text.strip())


def clean_output(out):
    """The model sometimes wraps the whole answer in quotes; take them off."""
    out = (out or "").strip()
    if len(out) >= 2 and _PAIRS.get(out[0]) == out[-1] and out[0] not in out[1:-1] and out[-1] not in out[1:-1]:
        out = out[1:-1].strip()
    if not out:
        raise RuntimeError("The translation came back empty. Try again.")
    return out


class Translator(ABC):
    id = ""
    name = ""

    @abstractmethod
    def status(self):
        """{"ready": bool, "step": str, "message": str} describing whether translation can run now."""

    @abstractmethod
    def setup(self, on_progress):
        """Do whatever is needed to become ready (download the model, start the engine)."""

    @abstractmethod
    def translate(self, text, source, target):
        """Return the translated text. source and target are codes from languages.LANGUAGES."""

    def translate_many(self, texts, source, target, on_progress=lambda done, total: None):
        out = []
        for i, text in enumerate(texts):
            out.append(self.translate(text, source, target) if text.strip() else text)
            on_progress(i + 1, len(texts))
        return out

    def stop(self):
        """Free memory held by the engine, if any."""
