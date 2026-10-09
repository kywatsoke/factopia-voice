"""Everything that touches ffmpeg: probing, audio extraction, single frames.
The ffmpeg binary comes with the imageio-ffmpeg package, so nothing has to be
installed separately on macOS or Windows."""
import io
import os
import re
import subprocess
import sys
from functools import lru_cache

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
MEDIA_TYPES = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


@lru_cache(1)
def ffmpeg():
    override = os.environ.get("FACTOPIA_VOICE_FFMPEG")
    if override:
        return override
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def command(*args):
    return [ffmpeg(), "-hide_banner", "-nostdin", *[str(a) for a in args]]


def run(*args):
    return subprocess.run(command(*args), capture_output=True, creationflags=NO_WINDOW)


def frame(path, seconds=0.0):
    """One decoded frame as an RGB image (rotation already applied), or None."""
    from PIL import Image
    for t in (max(0.0, seconds), 0.0):
        r = run("-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1")
        if r.stdout:
            return Image.open(io.BytesIO(r.stdout)).convert("RGB")
    return None


def probe(path):
    """Duration, and for video the displayed size and frame rate."""
    err = run("-i", path).stderr.decode("utf-8", "replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", err)
    info = {"duration": (int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])) if m else 0.0,
            "has_audio": bool(re.search(r"Stream #.*Audio:", err)), "has_video": False,
            "width": 1080, "height": 1920, "fps": 30.0}
    video = [l for l in err.splitlines() if re.search(r"Stream #.*Video:", l) and "attached pic" not in l]
    if video:
        first = frame(path, 0.0)
        if first is not None:
            fps = re.search(r"(\d+(?:\.\d+)?)\s*fps", video[0])
            info.update(has_video=True, width=first.width, height=first.height,
                        fps=min(60.0, max(1.0, float(fps[1]))) if fps else 30.0)
    return info


def extract_audio(path, wav):
    """Mono 16 kHz WAV, the format the speech recogniser expects."""
    r = run("-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav)
    if r.returncode != 0 or not os.path.exists(wav):
        raise RuntimeError("Could not read the sound from that file.")


# ---- video encoders ----------------------------------------------------------
# Hardware encoders tried in order, by system. Each is test-run once on a tiny
# clip before it is trusted; the processor (x264) is always the fallback.
HARDWARE = {"darwin": ["h264_videotoolbox"], "win32": ["h264_nvenc", "h264_qsv", "h264_amf"],
            "linux": ["h264_nvenc"]}
LABELS = {"h264_videotoolbox": "Apple VideoToolbox", "h264_nvenc": "NVIDIA graphics card",
          "h264_qsv": "Intel graphics", "h264_amf": "AMD graphics", None: "Processor (x264)"}
_PIXELS = {"h264_qsv": "nv12", "h264_amf": "nv12"}


def _encoder_works(name):
    r = run("-f", "lavfi", "-i", "color=c=black:s=320x240:r=30:d=1", "-frames:v", "15", "-c:v", name,
            "-b:v", "1M", "-pix_fmt", _PIXELS.get(name, "yuv420p"), "-f", "null", "-")
    return r.returncode == 0


@lru_cache(1)
def hardware_encoder():
    """The first hardware H.264 encoder that works on this computer, or None."""
    import json
    from .config import CACHE
    exe = ffmpeg()
    try:
        stamp = f"{exe}|{os.path.getsize(exe)}|{int(os.path.getmtime(exe))}"
    except OSError:
        stamp = exe
    cache = CACHE / "encoders.json"
    try:
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if saved.get("stamp") == stamp:
            return saved.get("encoder")
    except (OSError, ValueError):
        pass
    listed = run("-encoders").stdout.decode("utf-8", "replace")
    found = None
    for name in HARDWARE.get(sys.platform if sys.platform in HARDWARE else "linux", []):
        if re.search(rf"\b{name}\b", listed) and _encoder_works(name):
            found = name
            break
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"stamp": stamp, "encoder": found}), encoding="utf-8")
    except OSError:
        pass
    return found


def video_args(encoder, width, height, fps):
    """ffmpeg arguments for the video stream of an export."""
    if not encoder:
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
    kbps = int(max(4000, min(40000, width * height * fps * 0.16 / 1000)))     # about 10 Mbps at 1080p30
    return ["-c:v", encoder, "-b:v", f"{kbps}k", "-maxrate", f"{kbps * 3 // 2}k", "-bufsize", f"{kbps * 2}k",
            "-pix_fmt", _PIXELS.get(encoder, "yuv420p")]
