from factopia_voice import captions as C


def words(*items):
    return [{"text": t, "start": s, "end": e} for t, s, e in items]


def test_tokens_join_into_words_with_offset():
    out = C.words_from_tokens([" O", "ct", "opus", " has", " three", ","], [0.0, 0.1, 0.2, 0.5, 0.7, 0.9], offset=10)
    assert [(w["text"], w["start"]) for w in out] == [("Octopus", 10.0), ("has", 10.5), ("three,", 10.7)]


def test_word_ends_use_next_start_unless_a_pause_follows():
    out = C.word_ends([{"text": "one", "start": 0.0}, {"text": "two", "start": 0.4}, {"text": "three", "start": 3.0}], limit=3.3)
    assert out[0]["end"] == 0.4                 # runs up to the next word
    assert 0.6 < out[1]["end"] < 1.2            # a 2.6 s gap is a pause, not a long word
    assert out[2]["end"] == 3.3                 # never past the end of the recording


def test_group_breaks_at_sentence_end_pause_and_length():
    w = words(("Honey", 0, .3), ("never", .3, .6), ("spoils.", .6, 1.0), ("Bees", 1.0, 1.3), ("fan", 1.3, 1.5),
              ("their", 1.5, 1.7), ("wings", 1.7, 2.0), ("now", 3.5, 3.8))
    lines = C.group(w, "short")
    # "wings" would be alone, so it joins the line before; "now" follows a pause and stays apart
    assert [l["text"] for l in lines] == ["Honey never spoils.", "Bees fan their wings", "now"]
    assert lines[0]["start"] == 0 and lines[0]["end"] == 1.0
    assert [l["text"] for l in C.group(w, "long")] == ["Honey never spoils.", "Bees fan their wings", "now"]


def test_single_leftover_word_joins_the_line_before():
    w = words(("blood", 0, .3), ("through", .3, .6), ("the", .6, .8), ("gills.", .8, 1.2))
    assert [l["text"] for l in C.group(w, "short")] == ["blood through the gills."]


def test_align_uses_script_words_and_fills_gaps():
    heard = words(("honey", 0.0, 0.4), ("never", 0.4, 0.8), ("spoils", 0.8, 1.2), ("3,000", 1.2, 2.0), ("years", 2.0, 2.4))
    out = C.align("Honey never spoils. Three thousand years", heard)
    assert [w["text"] for w in out] == ["Honey", "never", "spoils.", "Three", "thousand", "years"]
    assert out[2]["start"] == 0.8 and out[5]["start"] == 2.0
    assert out[3]["start"] == 1.2 and abs(out[4]["start"] - 1.6) < 0.01 and out[4]["end"] == 2.0


def test_align_ignores_a_script_for_another_recording():
    heard = words(("completely", 0, .5), ("different", .5, 1), ("words", 1, 1.5))
    assert C.align("Honey never spoils at all", heard) == heard


def test_tidy_sorts_clamps_and_removes_overlap():
    lines = C.tidy([{"start": 5, "end": 4, "text": " b  b "}, {"start": 0, "end": 6, "text": "a"}, {"start": 1, "end": 2, "text": "  "}],
                   duration=5.5)
    assert lines == [{"start": 0.0, "end": 5.0, "text": "a"}, {"start": 5.0, "end": 5.1, "text": "b b"}]   # an end before its start becomes a short line


def test_srt_format():
    out = C.srt([{"start": 0, "end": 1.04, "text": "Hello"}, {"start": 3661.5, "end": 3662, "text": "Bye"}])
    assert out == "1\n00:00:00,000 --> 00:00:01,040\nHello\n\n2\n01:01:01,500 --> 01:01:02,000\nBye\n"
