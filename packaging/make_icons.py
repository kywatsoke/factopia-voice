"""Draw the app icon (the same mark as web/icon.svg) and save the .png, .icns
and .ico files the installers need, into build/."""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build"
ORANGE = (217, 72, 15, 255)


def draw(size):
    scale = 4                                   # draw large, shrink smooth
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = round(s * 0.06)                       # macOS-style margin inside the tile
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=round((s - 2 * pad) * 0.25), fill=ORANGE)
    unit = (s - 2 * pad) / 32                   # the SVG is drawn on a 32 x 32 grid
    width = max(1, round(2.6 * unit))
    for x, y1, y2 in ((7, 13, 19), (11.5, 9.5, 22.5), (16, 12, 20), (20.5, 7.5, 24.5), (25, 13.5, 18.5)):
        cx, r = pad + x * unit, width / 2       # a bar with round ends
        d.rounded_rectangle([cx - r, pad + y1 * unit - r, cx + r, pad + y2 * unit + r], radius=r, fill="white")
    return img.resize((size, size), Image.LANCZOS)


def main():
    OUT.mkdir(exist_ok=True)
    big = draw(1024)
    big.save(OUT / "icon.png")
    big.save(OUT / "icon.icns", sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
    draw(256).save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
