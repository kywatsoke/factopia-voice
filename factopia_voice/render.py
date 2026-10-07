"""Draws captions. The same code makes the preview frame and the exported
video, so what you see in the editor is what the export contains."""
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import fonts, media

DEFAULT_STYLE = {
    "font": "",             # font id "Family|Style"; empty picks a bold default
    "size": 84,             # text height in pixels on a 1080-wide frame; scales with the video
    "color": "#FFFFFF",
    "outline": 6,           # outline thickness on a 1080-wide frame; 0 turns it off
    "outline_color": "#101010",
    "box": False,           # background box behind the text
    "box_color": "#000000",
    "box_opacity": 70,      # percent
    "position": 62,         # vertical centre of the caption, percent from the top
    "width": 80,            # widest a caption may be, percent of the frame
    "uppercase": True,
}


def clean_style(style):
    s = dict(DEFAULT_STYLE)
    for key, default in DEFAULT_STYLE.items():
        value = (style or {}).get(key, default)
        if isinstance(default, bool):
            s[key] = bool(value)
        elif isinstance(default, int):
            try:
                s[key] = int(float(value))
            except (TypeError, ValueError):
                s[key] = default
        else:
            s[key] = str(value)
    s["size"] = min(300, max(16, s["size"]))
    s["outline"] = min(30, max(0, s["outline"]))
    s["box_opacity"] = min(100, max(0, s["box_opacity"]))
    s["position"] = min(96, max(4, s["position"]))
    s["width"] = min(100, max(30, s["width"]))
    for key in ("color", "outline_color", "box_color"):
        if not (len(s[key]) == 7 and s[key][0] == "#" and all(c in "0123456789abcdefABCDEF" for c in s[key][1:])):
            s[key] = DEFAULT_STYLE[key]
    return s


def _rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _wrap(draw, text, font, stroke, limit):
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and draw.textlength(trial, font=font) + 2 * stroke > limit:
            lines.append(current)
            current = word
        else:
            current = trial
    return lines + [current] if current else lines


def caption_image(text, style, width, height):
    """Return (RGBA image of one caption, (left, top) where it goes on the frame)."""
    style = clean_style(style)
    scale = width / 1080
    info = fonts.find(style["font"])
    font = ImageFont.truetype(info["path"], max(8, round(style["size"] * scale)), index=info["index"])
    stroke = round(style["outline"] * scale)
    pad = round(style["size"] * scale * 0.32) if style["box"] else stroke + 2
    text = text.upper() if style["uppercase"] else text
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    body = "\n".join(_wrap(probe, text, font, stroke, width * style["width"] / 100 - 2 * pad)) or " "
    spacing = round(style["size"] * scale * 0.18)
    box = probe.multiline_textbbox((0, 0), body, font=font, stroke_width=stroke, spacing=spacing, align="center")
    l, t, r, b = math.floor(box[0]), math.floor(box[1]), math.ceil(box[2]), math.ceil(box[3])
    w, h = r - l + 2 * pad, b - t + 2 * pad
    image = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if style["box"]:
        draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=round(style["size"] * scale * 0.22),
                               fill=_rgb(style["box_color"]) + (round(255 * style["box_opacity"] / 100),))
    draw.multiline_text((pad - l, pad - t), body, font=font, fill=_rgb(style["color"]) + (255,), spacing=spacing,
                        align="center", stroke_width=stroke, stroke_fill=_rgb(style["outline_color"]) + (255,))
    left = round((width - w) / 2)
    top = round(height * style["position"] / 100 - h / 2)
    return image, (left, min(max(top, 0), max(0, height - h)))


def preview(source, has_video, width, height, seconds, text, style, max_side=720):
    """A frame of the video (or a plain backdrop for audio) with one caption drawn on it."""
    frame = media.frame(source, seconds) if has_video else None
    if frame is None:
        frame = Image.new("RGB", (width, height), (32, 36, 44))
    if text.strip():
        overlay, at = caption_image(text, style, frame.width, frame.height)
        frame.paste(overlay, at, overlay)
    frame.thumbnail((max_side, max_side))
    return frame


class _Overlay:
    """A caption prepared for fast blending onto raw video frames."""

    def __init__(self, text, style, width, height):
        image, (left, top) = caption_image(text, style, width, height)
        x0, y0 = max(0, left), max(0, top)
        x1, y1 = min(width, left + image.width), min(height, top + image.height)
        data = np.asarray(image, dtype=np.uint16)[y0 - top:y1 - top, x0 - left:x1 - left]
        self.box = (y0, y1, x0, x1)
        self.alpha = data[..., 3:4]
        self.color = data[..., :3] * self.alpha

    def blend(self, frame):
        y0, y1, x0, x1 = self.box
        region = frame[y0:y1, x0:x1].astype(np.uint16)
        frame[y0:y1, x0:x1] = ((self.color + region * (255 - self.alpha)) // 255).astype(np.uint8)


def burn(source, out_path, lines, style, info, on_progress=lambda pct: None):
    """Write a copy of the video with the captions drawn into the picture."""
    width, height = info["width"] // 2 * 2, info["height"] // 2 * 2      # H.264 needs even sizes
    fps, duration = info["fps"], max(info["duration"], 0.1)
    log = open(str(out_path) + ".log", "wb")
    decoder = subprocess.Popen(
        media.command("-i", source, "-map", "0:v:0", "-vf", f"fps={fps},scale={width}:{height}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"),
        stdout=subprocess.PIPE, stderr=log, creationflags=media.NO_WINDOW)
    encoder = subprocess.Popen(
        media.command("-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", fps,
                      "-i", "pipe:0", "-i", source, "-map", "0:v:0", "-map", "1:a:0?",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                      "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path),
        stdin=subprocess.PIPE, stderr=log, creationflags=media.NO_WINDOW)
    size, index, cursor, cache, frames = width * height * 3, 0, 0, {}, 0
    try:
        while True:
            raw = decoder.stdout.read(size)
            if len(raw) < size:
                break
            t = index / fps
            while cursor < len(lines) and lines[cursor]["end"] <= t:
                cache.pop(cursor, None)
                cursor += 1
            if cursor < len(lines) and lines[cursor]["start"] <= t:
                if cursor not in cache:
                    cache[cursor] = _Overlay(lines[cursor]["text"], style, width, height)
                frame = np.frombuffer(bytearray(raw), dtype=np.uint8).reshape(height, width, 3)
                cache[cursor].blend(frame)
                raw = frame.tobytes()
            encoder.stdin.write(raw)
            index += 1
            frames += 1
            if index % 15 == 0:
                on_progress(min(99, int(t * 100 / duration)))
    finally:
        decoder.stdout.close()
        try:
            encoder.stdin.close()
        except OSError:
            pass
        decoder.wait()
        code = encoder.wait()
        log.close()
    if code != 0 or frames == 0 or not os.path.exists(out_path):
        if os.path.exists(out_path):
            os.remove(out_path)
        raise RuntimeError("The video could not be exported. Details are in " + str(out_path) + ".log")
    os.remove(str(out_path) + ".log")
    return frames
