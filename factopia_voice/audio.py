"""Audio assembly and export."""
import numpy as np
import soundfile as sf


def silence(rate, seconds):
    return np.zeros(int(rate * seconds), dtype="float32")


def trim(samples, rate, threshold=0.004, keep=0.04):
    """Cut dead air from both ends so pauses are exactly what the script asked for."""
    loud = np.flatnonzero(np.abs(samples) > threshold)
    if loud.size == 0:
        return samples
    pad = int(rate * keep)
    return samples[max(0, loud[0] - pad): loud[-1] + pad + 1]


def normalize(samples, peak=0.89):
    top = float(np.abs(samples).max()) if samples.size else 0.0
    return samples * (peak / top) if top > 0 else samples


def save(path, samples, rate, fmt):
    sf.write(str(path), samples, rate, format="MP3" if fmt == "mp3" else "WAV")
