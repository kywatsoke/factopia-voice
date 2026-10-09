"""The one path every voiceover takes:
script -> (translate) -> clean -> dictionary -> segments -> engine -> assemble -> file -> library."""
import threading
import time
import traceback

import numpy as np

from . import audio, library, text as T
from .config import CACHE, MODELS, OUTPUT, dictionary_store, ensure_dirs, models_problem, profile_store
from .downloads import fetch, missing
from .engines import create_engine
from .translate import get_translator


def clamp(value, low, high, fallback):
    try:
        return min(high, max(low, float(value)))
    except (TypeError, ValueError):
        return fallback


class Studio:
    def __init__(self):
        self.engine = None
        self.status = {"phase": "starting", "percent": 0, "detail": ""}
        self._lock = threading.Lock()
        self._started = False

    # ---- start-up -------------------------------------------------------
    def start(self):
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._boot, daemon=True).start()

    def _set(self, phase, percent=0, detail=""):
        self.status = {"phase": phase, "percent": percent, "detail": detail}

    def _boot(self):
        try:
            ensure_dirs()
            problem = models_problem()
            if problem:
                raise RuntimeError(problem)
            profile = profile_store.load()
            engine = create_engine(profile["engine"])
            if missing(engine.files(), MODELS):
                self._set("downloading", 0, "Downloading the voice model (one time only)")
                last = [-1]

                def progress(done, total, name):
                    pct = int(done * 100 / max(total, 1))
                    self._set("downloading", pct, f"Downloading the voice model: {done >> 20} of {total >> 20} MB")
                    if pct != last[0] and pct % 10 == 0:
                        last[0] = pct
                        print(f"  model download {pct}%", flush=True)

                fetch(engine.files(), MODELS, progress)
            self._set("loading", 100, "Loading the voice")
            engine.load(MODELS)
            if engine.voice(profile["voice"]) is None:
                profile["voice"] = engine.voices()[0].id
                profile_store.save(profile)
            self.engine = engine
            self._set("ready", 100)
            print("Voice is ready.", flush=True)
        except Exception as e:
            traceback.print_exc()
            self._set("error", 0, f"{e}")
            self._started = False          # a later start can try again

    def require_ready(self):
        if self.status["phase"] != "ready":
            raise RuntimeError("The voice is still getting ready. Try again in a moment.")

    # ---- synthesis ------------------------------------------------------
    def render(self, script, voice_id, speed, pause):
        script = T.apply_dictionary(T.normalize(script), dictionary_store.load())
        parts = T.segments(script, pause)
        if not any(kind == "speech" for kind, _ in parts):
            raise ValueError("Type or paste a script first.")
        chunks, rate, speech_seconds = [], None, 0.0
        with self._lock:                      # one clip at a time keeps memory flat
            for kind, value in parts:
                if kind == "pause":
                    chunks.append(("pause", value))
                    continue
                samples, rate = self.engine.synthesize(value, voice_id, speed)
                samples = audio.trim(samples, rate)
                speech_seconds += len(samples) / rate
                chunks.append(("speech", samples))
        joined = np.concatenate([audio.silence(rate, c) if k == "pause" else c for k, c in chunks])
        return audio.normalize(joined), rate, speech_seconds

    def generate(self, script, speed=None, pause=None, fmt=None, target_language=None):
        self.require_ready()
        profile = profile_store.load()
        speed = clamp(speed, 0.8, 1.3, profile["speed"])
        pause = clamp(pause, 0.0, 2.0, profile["pause"])
        fmt = fmt if fmt in ("mp3", "wav") else profile["format"]
        voice = self.engine.voice(profile["voice"])
        spoken = script
        if target_language and target_language != voice.language:
            translator = get_translator()
            if not translator.status()["ready"]:
                raise ValueError("Set up translation first.")
            spoken = translator.translate(script, voice.language[:2], target_language)

        started = time.time()
        samples, rate, speech_seconds = self.render(spoken, voice.id, speed, pause)
        name = f"{T.slug(script)}_{time.strftime('%Y%m%d-%H%M%S')}.{fmt}"
        audio.save(OUTPUT / name, samples, rate, fmt)

        words = T.word_count(spoken)
        if words >= 12 and speech_seconds > 2:      # learn this voice's real pace
            measured = words / (speech_seconds * speed)
            profile["wps"] = round(0.7 * profile["wps"] + 0.3 * measured, 3)
        profile.update(speed=speed, pause=pause, format=fmt)
        profile_store.save(profile)

        return library.add({
            "file": name, "title": T.title_of(script), "script": script, "words": words,
            "seconds": round(len(samples) / rate, 1), "took": round(time.time() - started, 1),
            "voice": voice.name, "voice_id": voice.id, "engine": self.engine.id,
            "speed": speed, "pause": pause, "format": fmt,
        })

    def preview(self, script):
        self.require_ready()
        profile = profile_store.load()
        samples, rate, _ = self.render(script[:300], profile["voice"], profile["speed"], profile["pause"])
        audio.save(CACHE / "preview.wav", samples, rate, "wav")
        return {"url": f"/preview.wav?t={int(time.time() * 1000)}"}
