"""Compare speech-to-text models on Chinese speech and write a Markdown report.

Used by the "Speech sample" workflow (spike for Chinese captions). It makes a
Chinese test recording with known text (Kokoro's Mandarin voice, phonemes from
misaki), adds the real human recordings shipped with the SenseVoice model, then
runs each candidate and reports speed, character error rate (after converting
to Simplified Chinese) and whether word or character timings come back.

    python scripts/stt_sample.py --work <folder> --out report.md
"""
import argparse
import json
import platform
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf

TEXT = [
    "蜂蜜永远不会变质。考古学家在埃及古墓中发现了三千年前的蜂蜜，至今仍然可以食用。",
    "章鱼有三颗心脏，其中两颗在它游泳的时候会停止跳动。",
    "金星上的一天比它的一年还要长。",
    "竹子是世界上生长最快的植物之一，有些品种一天可以长近一米。",
    "这种水母可以长生不老。它受伤以后，会变回水螅，重新开始生命。",
    "那么接下来会发生什么呢？我们一起去看看吧。",
]
RATE = 16000


def log(*a):
    print(*a, flush=True)


def make_kokoro_sample(work):
    """Mandarin speech with known text, from Kokoro's zf_xiaobei voice."""
    from kokoro_onnx import Kokoro
    from misaki import zh
    models = Path(work) / "kokoro"
    g2p = zh.ZHG2P()
    model = next(models.glob("kokoro-v1.*.onnx"))
    voices = next(models.glob("voices-v1.*.bin"))
    tts = Kokoro(str(model), str(voices))
    voice = "zf_xiaobei" if "zf_xiaobei" in tts.get_voices() else next(v for v in tts.get_voices() if v.startswith("zf_"))
    pieces = []
    for sentence in TEXT:
        phonemes, _ = g2p(sentence)
        audio, rate = tts.create(phonemes, voice=voice, speed=1.0, is_phonemes=True)
        pieces += [audio, np.zeros(int(rate * 0.4), dtype=np.float32)]
    audio = np.concatenate(pieces)
    out = Path(work) / "kokoro-zh.wav"
    sf.write(out, audio, rate)
    return out, "".join(TEXT), voice


def to16k(path, work):
    import imageio_ffmpeg
    out = Path(work) / (Path(path).stem + "-16k.wav")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(path), "-ac", "1",
                    "-ar", str(RATE), str(out)], check=True)
    return out


def simplified(text):
    import opencc
    return opencc.OpenCC("t2s").convert(text)


def chars(text):
    return [c for c in text if unicodedata.category(c)[0] in "LN"]


def cer(ref, hyp):
    r, h = chars(ref), chars(simplified(hyp))
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return d[len(h)] / max(1, len(r))


def run_sensevoice(folder, wav):
    import sherpa_onnx
    model = next(Path(folder).glob("model*.int8.onnx"), None) or next(Path(folder).glob("model*.onnx"))
    rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(model=str(model), tokens=str(Path(folder) / "tokens.txt"),
                                                         language="auto", use_itn=True, num_threads=4)
    samples, rate = sf.read(str(wav), dtype="float32")
    started = time.time()
    s = rec.create_stream()
    s.accept_waveform(rate, samples)
    rec.decode_stream(s)
    took = time.time() - started
    res = s.result
    timestamps = list(getattr(res, "timestamps", []) or [])
    return {"text": res.text, "seconds": took, "audio": len(samples) / rate,
            "timings": f"{len(timestamps)} token times" if timestamps else "none",
            "first_timings": [(t, round(float(x), 2)) for t, x in zip(list(res.tokens)[:6], timestamps[:6])]}


def run_whisper(size, wav):
    from faster_whisper import WhisperModel
    load = time.time()
    model = WhisperModel(size, device="cpu", compute_type="int8")
    loaded = time.time() - load
    started = time.time()
    segments, info = model.transcribe(str(wav), language="zh", word_timestamps=True, vad_filter=True,
                                      initial_prompt="以下是普通话的句子，使用简体中文。", beam_size=5)
    words, text = [], ""
    for seg in segments:
        text += seg.text
        words += [(w.word, round(w.start, 2), round(w.end, 2)) for w in (seg.words or [])]
    took = time.time() - started
    audio = sf.info(str(wav)).duration
    return {"text": text, "seconds": took, "audio": audio, "load": loaded,
            "timings": f"{len(words)} word times" if words else "none", "first_timings": words[:6]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--sensevoice", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    work = Path(args.work)
    samples = []
    try:
        wav, text, voice = make_kokoro_sample(work)
        samples.append(("Kokoro Mandarin (" + voice + "), known text", to16k(wav, work), text))
    except Exception as e:
        log("Kokoro sample failed:", type(e).__name__, e)
    for name in ("zh.wav", "yue.wav", "en.wav"):
        p = Path(args.sensevoice) / "test_wavs" / name
        if p.exists():
            samples.append((f"SenseVoice test recording {name} (human)", to16k(p, work), None))
    engines = [("SenseVoice-Small int8 (sherpa-onnx)", lambda w: run_sensevoice(args.sensevoice, w)),
               ("Whisper small int8 (faster-whisper)", lambda w: run_whisper("small", w)),
               ("Whisper large-v3-turbo int8 (faster-whisper)", lambda w: run_whisper("large-v3-turbo", w))]
    lines = [f"# Speech-to-text sample: Chinese", "",
             f"- Machine: {platform.platform()}, {platform.machine()}, processor only", ""]
    results = {}
    for label, wav, ref in samples:
        lines += [f"## {label}", ""]
        if ref:
            lines += [f"Reference: {ref}", ""]
        lines += ["| Engine | Text | Simplified CER | Speed (x real time) | Timings | First timings |", "| --- | --- | --- | --- | --- | --- |"]
        for name, fn in engines:
            try:
                r = fn(wav)
                speed = r["audio"] / max(r["seconds"], 1e-6)
                score = f"{cer(ref, r['text']) * 100:.1f}%" if ref else "-"
                lines.append(f"| {name} | {r['text'].strip()} | {score} | {speed:.1f}x | {r['timings']} | "
                             f"{json.dumps(r['first_timings'], ensure_ascii=False)} |")
                results.setdefault(name, []).append(score)
                log(name, label, score, f"{speed:.1f}x")
            except Exception as e:
                lines.append(f"| {name} | failed: {type(e).__name__}: {str(e)[:200]} | | | | |")
                log(name, "failed", e)
        lines.append("")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines))


if __name__ == "__main__":
    main()
