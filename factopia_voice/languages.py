"""The caption languages (English, Chinese, Burmese) and the text rules that
differ between them (spaces between words, sentence endings, line breaks).
Translation covers English and Chinese only: Burmese output from the
translation model was not good enough (decided 9 October 2026)."""
import re

LANGUAGES = {
    "en": {"name": "English", "native": "English", "code": "en", "max_chars": 42, "joiner": " "},
    "zh": {"name": "Chinese", "native": "中文", "code": "zh-Hans", "max_chars": 16, "joiner": ""},
    "my": {"name": "Burmese", "native": "မြန်မာ", "code": "my", "max_chars": 36, "joiner": " "},
}
TRANSLATION = ("en", "zh")
NOT_TRANSLATED = "Translation works between English and Chinese."
SENTENCE_END = ".!?…。！？။"          # . ! ? … 。 ！ ？ ။
CLAUSE_MARKS = ",;:，、；：၊"           # , ; : ， 、 ； ： ၊
_HAN = re.compile(r"[㐀-鿿豈-﫿]")
_MYANMAR = re.compile(r"[က-႟ꩠ-ꩿꧠ-꧿]")
_LATIN = re.compile(r"[A-Za-z]")


def detect(text):
    """Guess the language of a piece of text from the letters it uses."""
    counts = {"zh": len(_HAN.findall(text)), "my": len(_MYANMAR.findall(text)), "en": len(_LATIN.findall(text)) / 4}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else "en"


def valid(code):
    return code if code in LANGUAGES else "en"


def check_translation(source, target):
    """Refuse a translation that does not go between English and Chinese."""
    if source not in TRANSLATION or target not in TRANSLATION:
        raise ValueError(NOT_TRANSLATED)


def join(parts, lang):
    """Join pieces of text the way the language writes them (Chinese has no spaces)."""
    sep = LANGUAGES[valid(lang)]["joiner"]
    out = ""
    for p in (p.strip() for p in parts):
        if not p:
            continue
        if out and sep == " " and not out.endswith(" "):
            out += " "
        out += p
    return out


# Myanmar syllables start at a consonant or independent vowel that is not stacked
# under the previous consonant (U+1039) and not killed by a following asat (U+103A).
_MY_START = re.compile(r"(?<![္])(?=[က-ဪဿ၌-၏](?![်္]))")
_CJK_CLOSE = set("，。、；：！？）」』》〉”’,.;:!?)")


def segments(text):
    """Split text into the smallest pieces a line may break between, so
    wrapping never cuts a word, a Chinese character pair rule or a Burmese syllable.
    Joining the pieces gives back the text exactly."""
    out, buf = [], ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == " ":
            buf += ch
            out.append(buf)
            buf = ""
        elif _HAN.match(ch):
            if buf and not buf.endswith(" ") and not _LATIN.match(buf[-1]):
                out.append(buf)
                buf = ""
            elif buf and _LATIN.match(buf[-1]):
                out.append(buf)
                buf = ""
            buf += ch
            while i + 1 < len(text) and text[i + 1] in _CJK_CLOSE:   # keep closing marks with their character
                i += 1
                buf += text[i]
            out.append(buf)
            buf = ""
        elif _MYANMAR.match(ch):
            if buf and _MY_START.match(text, i) and i > 0 and text[i - 1] != "္":
                out.append(buf)
                buf = ""
            buf += ch
        else:
            buf += ch
        i += 1
    if buf:
        out.append(buf)
    return [s for s in out if s]
