"""Translate a fixed sample with the built-in engine and write a Markdown report.

Used by the "Translation sample" workflow so the real model's English, Chinese
and Burmese output can be judged without a Mac. Expects the model file in the
data folder and FACTOPIA_VOICE_LLAMA_SERVER pointing at llama-server.

    python scripts/translation_sample.py --out report.md [--quality standard]
"""
import argparse
import hashlib
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from factopia_voice.languages import LANGUAGES  # noqa: E402
from factopia_voice.translate import llamacpp  # noqa: E402

ENGLISH = [
    "Honey never spoils. Archaeologists have found 3,000-year-old honey in Egyptian tombs that was still safe to eat.",
    "Octopuses have three hearts, and two of them stop beating when they swim.",
    "A day on Venus is longer than its year.",
    "Bananas are berries, but strawberries are not.",
    "Sharks existed before trees. They have been swimming in the oceans for more than 400 million years.",
    "The Eiffel Tower can grow about 15 centimetres taller in summer, because heat makes the iron expand.",
    "This jellyfish can live forever. When it is injured, it turns back into a polyp and starts its life again.",
    "So what happens next? Let's find out.",
]
CHINESE = [
    "蜂蜜永远不会变质。考古学家在埃及古墓中发现了三千年前的蜂蜜，至今仍然可以食用。",
    "光从太阳到达地球大约需要八分钟。",
    "人体中最小的骨头位于耳朵里。",
    "竹子是世界上生长最快的植物之一，有些品种一天可以长近一米。",
]


def run(translator, texts, source, target, rows):
    out = []
    for text in texts:
        started = time.time()
        try:
            result = translator.translate(text, source, target)
        except Exception as e:          # keep going; the report shows the failure
            result = f"(failed: {e})"
        seconds = time.time() - started
        rows.append((source, target, text, result, seconds))
        out.append(result)
        print(f"{source}->{target} {seconds:5.1f}s  {result[:70]}", flush=True)
    return out


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quality", default="standard")
    args = ap.parse_args()

    translator = llamacpp.BuiltinTranslator(args.quality)
    if not translator.installed():
        sys.exit(f"Model not found at {translator.path}")
    version = subprocess.run(llamacpp.server_command() + ["--version"], capture_output=True, text=True)
    rows = []
    started = time.time()
    burmese = run(translator, ENGLISH, "en", "my", rows)
    run(translator, ENGLISH, "en", "zh", rows)
    run(translator, CHINESE, "zh", "my", rows)
    run(translator, CHINESE, "zh", "en", rows)
    run(translator, [b for b in burmese if not b.startswith("(failed")], "my", "en", rows)
    total = time.time() - started
    mode = llamacpp.SERVER.mode
    translator.stop()

    said = [l for l in (version.stdout + version.stderr).splitlines() if "version" in l.lower()]
    engine_version = said[0].strip() if said else "unknown"
    names = {k: v["name"] for k, v in LANGUAGES.items()}
    lines = [f"# Translation sample: {translator.spec.label}", "",
             f"- Model file: `{translator.spec.file}` from `{translator.spec.repo}`, {translator.path.stat().st_size:,} bytes",
             f"- SHA-256: `{sha256(translator.path)}`",
             f"- Engine: llama-server `{engine_version}`"
             f" on the {'graphics chip' if mode == 'gpu' else 'processor'}",
             f"- Machine: {platform.platform()}, {platform.machine()}",
             f"- {len(rows)} translations in {total:.0f} s", ""]
    for (source, target) in dict.fromkeys((r[0], r[1]) for r in rows):
        lines += [f"## {names[source]} to {names[target]}", "", "| # | Source | Translation | Seconds |", "| --- | --- | --- | --- |"]
        for i, r in enumerate([r for r in rows if (r[0], r[1]) == (source, target)], 1):
            cell = lambda s: s.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {i} | {cell(r[2])} | {cell(r[3])} | {r[4]:.1f} |")
        lines.append("")
    lines.append("Burmese to English uses the model's own English-to-Burmese output above (a round trip).")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
