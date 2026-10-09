import subprocess

import numpy as np
import pytest

from factopia_voice import fonts, media, render

pytestmark = pytest.mark.skipif(not fonts.all_fonts(), reason="no fonts installed on this machine")


def test_fonts_are_found_and_default_resolves():
    found = fonts.all_fonts()
    assert all({"id", "label", "path", "index"} <= set(f) for f in found)
    assert fonts.find("No Such Font|Bold")["id"] == fonts.default_id()


def test_style_is_cleaned():
    s = render.clean_style({"size": "9999", "color": "red", "box": 1, "position": -5, "extra": "x"})
    assert s["size"] == 300 and s["color"] == "#FFFFFF" and s["box"] is True and s["position"] == 4 and "extra" not in s


def test_caption_image_is_centred_and_scales_with_the_frame():
    big, (x, y) = render.caption_image("Honey never spoils", render.DEFAULT_STYLE, 1080, 1920)
    small, _ = render.caption_image("Honey never spoils", render.DEFAULT_STYLE, 540, 960)
    assert abs((x + big.width / 2) - 540) <= 1 and abs((y + big.height / 2) - 1920 * 0.62) <= 1
    assert 0.4 < small.width / big.width < 0.6
    assert np.asarray(big)[..., 3].max() == 255


def test_long_text_wraps_inside_the_allowed_width():
    image, (x, _) = render.caption_image("word " * 30, {**render.DEFAULT_STYLE, "width": 60}, 1080, 1920)
    assert image.width <= 1080 * 0.6 + 4 and x >= 0 and image.height > 300


def test_burn_writes_captions_into_the_picture(tmp_path):
    src, out = tmp_path / "in.mp4", tmp_path / "out.mp4"
    made = subprocess.run(media.command("-y", "-f", "lavfi", "-i", "color=c=0x202830:s=270x480:r=10:d=2", "-f", "lavfi", "-i",
                                        "sine=frequency=440:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                        "-c:a", "aac", "-shortest", src), capture_output=True)
    if made.returncode != 0:
        pytest.skip("this ffmpeg build cannot make a test video")
    info = media.probe(src)
    assert info["has_video"] and info["has_audio"] and (info["width"], info["height"]) == (270, 480) and 1.8 < info["duration"] < 2.3
    lines = [{"start": 0.0, "end": 1.0, "text": "Hello there"}]
    frames = render.burn(src, out, lines, render.DEFAULT_STYLE, info)
    assert 18 <= frames <= 22 and media.probe(out)["has_audio"]
    with_caption = np.asarray(media.frame(out, 0.5), dtype=int)
    without = np.asarray(media.frame(out, 1.5), dtype=int)
    assert with_caption.max() > 200 and without.max() < 90          # white text only while the line is showing
    preview = render.preview(src, True, 270, 480, 0.5, "Hello there", render.DEFAULT_STYLE)
    assert np.asarray(preview, dtype=int).max() > 200


@pytest.mark.parametrize("lang,text", [("zh", "考古学家在埃及古墓中发现了三千年前的蜂蜜而且它仍然可以安全食用"),
                                       ("my", "ပျားရည်သည် ဘယ်တော့မှ မပုပ်ပါ။ သိပ္ပံပညာရှင်များက အီဂျစ်ဂူသင်္ချိုင်းများတွင် တွေ့ရှိခဲ့သည်။")])
def test_chinese_and_burmese_wrap_inside_the_frame(lang, text):
    font = fonts.for_language(lang)
    if not fonts.covers(font, lang):
        pytest.skip(f"no {lang} font on this machine")
    if not render.can_draw(text):
        pytest.skip(f"no text shaping (raqm) for {lang} on this machine")
    style = {**render.DEFAULT_STYLE, "font": font, "uppercase": False, "width": 70}
    image, (x, _) = render.caption_image(text, style, 1080, 1920)
    assert image.width <= 1080 * 0.7 + 4 and x > 0 and image.height > 2 * 84


def test_font_coverage_is_detected():
    latin_only = next((f["id"] for f in fonts.all_fonts() if f["family"] == "DejaVu Sans"), None)
    if latin_only is None:
        pytest.skip("DejaVu Sans not installed")
    assert fonts.covers(latin_only, "en") and not fonts.covers(latin_only, "my")
