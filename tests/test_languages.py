from factopia_voice import captions as C
from factopia_voice import languages as L


def test_detect():
    assert L.detect("Honey never spoils.") == "en"
    assert L.detect("蜂蜜永远不会变质。") == "zh"
    assert L.detect("ပျားရည်သည် ဘယ်တော့မှ မပုပ်ပါ။") == "my"
    assert L.detect("") == "en"


def test_segments_rebuild_the_text_and_respect_syllables():
    for text in ["Honey never spoils.", "蜂蜜永远不会变质。考古学家", "ပျားရည်သည် ဘယ်တော့မှ မပုပ်ပါ။ သိပ္ပံပညာ", "Mix 中文 and မြန်မာ"]:
        assert "".join(L.segments(text)) == text
    my = L.segments("သိပ္ပံပညာ")
    assert my[0] == "သိပ္ပံ"                     # a stacked consonant stays in its syllable
    assert all(not s.startswith(("်", "္", "ာ", "ိ", "ေ")) for s in L.segments("မြန်မာနိုင်ငံ"))
    assert L.segments("变质。考")[1] == "质。"     # closing punctuation stays with its character


def test_join():
    assert L.join(["Honey never", "spoils."], "en") == "Honey never spoils."
    assert L.join(["蜂蜜永远", "不会变质。"], "zh") == "蜂蜜永远不会变质。"


def test_parse_srt_handles_real_world_files():
    srt = "﻿1\r\n00:00:01,000 --> 00:00:02,500\r\n<i>Hello</i>\r\nthere\r\n\r\n\r\n00:00:03.2 --> 00:00:04.75\r\n第二行\r\n\r\n3\r\n00:00:05,000 --> 00:00:06,000\r\n\r\n"
    assert C.parse_srt(srt) == [{"start": 1.0, "end": 2.5, "text": "Hello there"}, {"start": 3.2, "end": 4.75, "text": "第二行"}]


def test_parse_srt_rejects_other_files():
    import pytest
    with pytest.raises(ValueError):
        C.parse_srt("just some notes")


def test_srt_round_trip():
    lines = [{"start": 0.0, "end": 1.04, "text": "Hello"}, {"start": 1.5, "end": 3.0, "text": "ပျားရည်"}]
    assert C.parse_srt(C.srt(lines)) == lines


def test_sentences_group_lines_and_break_on_pauses():
    lines = [{"start": 0, "end": 1, "text": "Honey never"}, {"start": 1, "end": 2, "text": "spoils."},
             {"start": 2, "end": 3, "text": "Bees fan"}, {"start": 5, "end": 6, "text": "their wings"}]
    out = C.sentences(lines, "en")
    assert [s["text"] for s in out] == ["Honey never spoils.", "Bees fan", "their wings"]
    assert out[0]["start"] == 0 and out[0]["end"] == 2
    zh = C.sentences([{"start": 0, "end": 1, "text": "蜂蜜永远"}, {"start": 1, "end": 2, "text": "不会变质。"}], "zh")
    assert zh[0]["text"] == "蜂蜜永远不会变质。"


def test_spread_keeps_short_text_whole_and_splits_long_text_by_clause():
    assert C.spread("Short line.", 1, 3, "en") == [{"start": 1, "end": 3, "text": "Short line."}]
    out = C.spread("考古学家在埃及古墓中发现了三千年前的蜂蜜，而且它仍然可以安全食用。", 10.0, 16.0, "zh")
    assert len(out) >= 2 and all(len(l["text"]) <= 20 for l in out)
    assert out[0]["start"] == 10.0 and out[-1]["end"] == 16.0
    assert "".join(l["text"] for l in out) == "考古学家在埃及古墓中发现了三千年前的蜂蜜，而且它仍然可以安全食用。"
    assert all(a["end"] == b["start"] for a, b in zip(out, out[1:]))
    my = C.spread("ပျားရည်သည် ဘယ်တော့မှ မပုပ်ပါ၊ သိပ္ပံပညာရှင်များက အီဂျစ်ဂူသင်္ချိုင်းများတွင် နှစ်ပေါင်းသုံးထောင်ရှိ ပျားရည်ကို တွေ့ရှိခဲ့သည်။", 0, 8, "my")
    assert len(my) >= 2 and all(not l["text"].startswith(("်", "္", "ာ")) for l in my)
