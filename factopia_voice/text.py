"""Script preparation: clean-up, the pronunciation dictionary, and pause markers."""
import re

_PAUSE = re.compile(r"\[\s*pause(?:\s+(\d+(?:\.\d+)?))?\s*s?\s*\]", re.I)
_BLANK = re.compile(r"\n[ \t]*\n+")
_SWAPS = {"’": "'", "‘": "'", "“": '"', "”": '"', "—": ", ",
          "–": ", ", "…": "...", " ": " "}


def normalize(text):
    for a, b in _SWAPS.items():
        text = text.replace(a, b)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", text).strip()


def apply_dictionary(text, entries):
    """Replace whole words (any letter case) with their 'say it as' spelling."""
    for e in sorted(entries, key=lambda e: -len(e.get("word", ""))):
        word, say = (e.get("word") or "").strip(), (e.get("say") or "").strip()
        if word and say:
            text = re.sub(r"(?<!\w)" + re.escape(word) + r"(?!\w)", lambda m: say, text, flags=re.I)
    return text


def segments(text, default_pause):
    """Split a script into ("speech", text) and ("pause", seconds) parts.
    A blank line or [pause] gives the default pause; [pause 0.8] gives 0.8 seconds."""
    out = []
    for i, block in enumerate(_BLANK.split(normalize(text))):
        if i:
            out.append(("pause", default_pause))
        pos = 0
        for m in _PAUSE.finditer(block):
            piece = block[pos:m.start()].strip()
            if piece:
                out.append(("speech", " ".join(piece.split())))
            out.append(("pause", min(5.0, float(m.group(1))) if m.group(1) else default_pause))
            pos = m.end()
        piece = block[pos:].strip()
        if piece:
            out.append(("speech", " ".join(piece.split())))
    while out and out[0][0] == "pause":
        out.pop(0)
    while out and out[-1][0] == "pause":
        out.pop()
    return out


def word_count(text):
    return len(re.findall(r"[^\W_]+(?:['\-][^\W_]+)*", _PAUSE.sub(" ", text)))


def title_of(text, words=7):
    parts = _PAUSE.sub(" ", normalize(text)).split()
    return " ".join(parts[:words]) + ("..." if len(parts) > words else "")


def slug(text, fallback="voiceover"):
    """A safe file name from the first words. Text with no Latin letters or
    digits (Chinese, Burmese) gets the fallback name."""
    s = re.sub(r"[^a-z0-9]+", "-", " ".join(_PAUSE.sub(" ", text).lower().split()[:6])).strip("-")
    return s[:48] or fallback
