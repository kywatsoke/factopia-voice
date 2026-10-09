"""The caption track: timed lines of text. Speech recognition, a known script
and (later) on-screen text all end up in this one shape."""
import difflib
import re

LENGTHS = {"short": (18, 3), "medium": (32, 6), "long": (84, 16)}   # (max characters, max words) per line
_ENDS = ".!?\u2026"


def word_ends(words, limit):
    """Give each word an end time: the next word's start, unless a pause follows."""
    out = []
    for i, w in enumerate(words):
        natural = w["start"] + 0.25 + 0.06 * len(w["text"])
        nxt = words[i + 1]["start"] if i + 1 < len(words) else limit
        end = nxt if nxt - w["start"] <= 1.0 else natural     # a long gap is a pause, not a long word
        out.append({"text": w["text"], "start": round(w["start"], 3),
                    "end": round(max(w["start"] + 0.05, min(end, limit)), 3)})
    return out


def words_from_tokens(tokens, starts, offset=0.0):
    """Join recogniser word pieces (a leading space starts a new word) into words."""
    words = []
    for token, start in zip(tokens, starts):
        if token.startswith(" ") or not words:
            if token.strip():
                words.append({"text": token.strip(), "start": float(start) + offset})
        else:
            words[-1]["text"] += token
    return words


def _key(word):
    return re.sub(r"[^\w']", "", word.lower().replace("\u2019", "'"))


def align(script, words):
    """Put the script's exact words on the recogniser's timings. Words the
    recogniser heard differently are spaced evenly between their neighbours."""
    target = script.split()
    if not target or not words:
        return words
    matcher = difflib.SequenceMatcher(None, [_key(w) for w in target], [_key(w["text"]) for w in words], autojunk=False)
    times = [None] * len(target)
    for a, b, size in matcher.get_matching_blocks():
        for k in range(size):
            times[a + k] = (words[b + k]["start"], words[b + k]["end"])
    if sum(t is not None for t in times) < 0.5 * len(target):
        return words                       # the script is for some other recording
    first, last = words[0]["start"], words[-1]["end"]
    i = 0
    while i < len(target):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(target) and times[j] is None:
            j += 1
        left = times[i - 1][1] if i else first
        right = times[j][0] if j < len(target) else last
        step = max(0.0, right - left) / (j - i)
        for k in range(i, j):
            times[k] = (left + step * (k - i), left + step * (k - i + 1))
        i = j
    return [{"text": t, "start": round(s, 3), "end": round(max(e, s + 0.05), 3)} for t, (s, e) in zip(target, times)]


def group(words, length="short"):
    """Break words into caption lines at sentence ends, pauses and the length limit."""
    max_chars, max_words = LENGTHS.get(length, LENGTHS["short"])
    lines, current = [], []

    def flush():
        if current:
            lines.append({"start": current[0]["start"], "end": current[-1]["end"],
                          "text": " ".join(w["text"] for w in current)})
            current.clear()

    for w in words:
        if current:
            text = " ".join(x["text"] for x in current)
            prev = current[-1]
            if (len(text) + 1 + len(w["text"]) > max_chars or len(current) >= max_words
                    or w["start"] - prev["end"] > 0.6 or prev["text"][-1:] in _ENDS
                    or (prev["text"].endswith(",") and len(text) >= max_chars * 0.6)):
                flush()
        current.append(w)
    flush()
    merged = []                    # a single leftover word reads better on the line before it
    for line in lines:
        prev = merged[-1] if merged else None
        if (prev and " " not in line["text"] and prev["text"][-1:] not in _ENDS
                and line["start"] - prev["end"] <= 0.6 and len(prev["text"]) + 1 + len(line["text"]) <= max_chars + 10):
            prev["text"] += " " + line["text"]
            prev["end"] = line["end"]
        else:
            merged.append(line)
    return tidy(merged)


def tidy(lines, duration=None):
    """Sort, clamp and number lines so the track is always valid."""
    out = []
    for line in sorted(lines, key=lambda l: float(l.get("start", 0))):
        text = " ".join(str(line.get("text", "")).split())
        if not text:
            continue
        start = max(0.0, float(line.get("start", 0)))
        end = max(start + 0.1, float(line.get("end", start + 1)))
        if duration:
            start, end = min(start, max(0.0, duration - 0.1)), min(end, duration)
        out.append({"start": round(start, 2), "end": round(max(end, start + 0.1), 2), "text": text})
    for a, b in zip(out, out[1:]):
        if a["end"] > b["start"]:
            a["end"] = max(a["start"] + 0.05, b["start"])
    return out


def _stamp(seconds):
    ms = int(round(seconds * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt(lines):
    return "\n".join(f"{i}\n{_stamp(l['start'])} --> {_stamp(l['end'])}\n{l['text']}\n"
                     for i, l in enumerate(lines, 1))


# ---- subtitle files and translation helpers (2.2) ---------------------------
_TIME = re.compile(r"(\d+):(\d{1,2}):(\d{1,2})[,.](\d{1,3})")


def parse_srt(text):
    """Read an SRT subtitle file into caption lines. Tolerates missing numbers,
    Windows line endings, a byte-order mark and dots instead of commas."""
    text = text.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for block in re.split(r"\n\s*\n", text):
        rows = [r for r in block.strip().split("\n") if r.strip()]
        for k, row in enumerate(rows):
            if "-->" in row:
                a, b = row.split("-->", 1)
                ta, tb = _TIME.search(a), _TIME.search(b)
                if ta and tb:
                    sec = lambda m: int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4].ljust(3, "0")) / 1000
                    body = " ".join(re.sub(r"<[^>]+>|\{\\[^}]*\}", "", r).strip() for r in rows[k + 1:])
                    if body.strip():
                        lines.append({"start": sec(ta), "end": sec(tb), "text": body})
                break
    if not lines:
        raise ValueError("No subtitles were found in that file. Check it is an SRT file.")
    return tidy(lines)


def sentences(lines, lang="en", max_gap=1.0, max_seconds=9.0):
    """Group caption lines into whole sentences, so translation sees complete
    thoughts instead of fragments. Returns [{"start", "end", "text"}]."""
    from .languages import SENTENCE_END, join
    groups, current = [], []
    for line in lines:
        if current and (line["start"] - current[-1]["end"] > max_gap or line["end"] - current[0]["start"] > max_seconds):
            groups.append(current)
            current = []
        current.append(line)
        if line["text"].rstrip()[-1:] in SENTENCE_END:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return [{"start": g[0]["start"], "end": g[-1]["end"], "text": join([l["text"] for l in g], lang)} for g in groups]


def spread(text, start, end, lang):
    """Turn one translated sentence into caption lines no longer than the
    language's limit, splitting at clause marks first, and sharing the
    sentence's time in proportion to length."""
    from .languages import CLAUSE_MARKS, LANGUAGES, segments, valid
    limit = LANGUAGES[valid(lang)]["max_chars"]
    text = " ".join(text.split())
    if len(text) <= limit:
        return [{"start": start, "end": end, "text": text}]
    pieces, buf = [], ""
    for seg in segments(text):
        buf += seg
        if seg.rstrip()[-1:] in CLAUSE_MARKS:
            pieces.append(buf)
            buf = ""
    if buf:
        pieces.append(buf)
    chunks, cur = [], ""
    for piece in pieces:                       # whole clauses where they fit
        if cur and len(cur) + len(piece) > limit:
            chunks.append(cur)
            cur = ""
        cur += piece
    if cur:
        chunks.append(cur)
    final = []
    for chunk in chunks:                       # a clause that is still too long is cut at break points
        if len(chunk) <= limit * 1.25:
            final.append(chunk)
            continue
        cur = ""
        for seg in segments(chunk):
            if cur and len(cur) + len(seg) > limit:
                final.append(cur)
                cur = ""
            cur += seg
        if cur:
            final.append(cur)
    final = [c.strip() for c in final if c.strip()]
    total = sum(len(c) for c in final) or 1
    out, t = [], start
    for i, chunk in enumerate(final):
        nxt = end if i == len(final) - 1 else round(t + (end - start) * len(chunk) / total, 2)
        out.append({"start": round(t, 2), "end": nxt, "text": chunk})
        t = nxt
    return out
