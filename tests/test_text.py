from factopia_voice import text as T


def test_normalize_swaps_curly_punctuation():
    assert T.normalize("It’s “fine” — really…") == "It's \"fine\" ,  really...".replace("  ", " ")


def test_blank_line_becomes_default_pause():
    assert T.segments("One.\n\nTwo.", 0.35) == [("speech", "One."), ("pause", 0.35), ("speech", "Two.")]


def test_pause_tag_with_and_without_seconds():
    parts = T.segments("A [pause 0.8] B [pause] C", 0.3)
    assert parts == [("speech", "A"), ("pause", 0.8), ("speech", "B"), ("pause", 0.3), ("speech", "C")]


def test_pause_tag_is_capped_and_case_insensitive():
    assert T.segments("A [PAUSE 99] B", 0.3)[1] == ("pause", 5.0)


def test_leading_and_trailing_pauses_are_dropped():
    assert T.segments("[pause] Hello [pause]\n\n", 0.3) == [("speech", "Hello")]


def test_only_pauses_gives_nothing():
    assert T.segments("  [pause]  \n\n", 0.3) == []


def test_dictionary_whole_word_any_case_and_possessive():
    out = T.apply_dictionary("Qatar, qatar's and Qatari.", [{"word": "Qatar", "say": "KUH-tar"}])
    assert out == "KUH-tar, KUH-tar's and Qatari."


def test_dictionary_longest_entry_wins():
    entries = [{"word": "New", "say": "nyoo"}, {"word": "New York", "say": "Noo Yawk"}]
    assert T.apply_dictionary("New York is new.", entries) == "Noo Yawk is nyoo."


def test_dictionary_ignores_empty_entries_and_regex_characters():
    assert T.apply_dictionary("C++ rocks", [{"word": "C++", "say": "see plus plus"}, {"word": "", "say": "x"}]) == "see plus plus rocks"


def test_word_count_ignores_pause_tags_and_joins_hyphens():
    assert T.word_count("It's a 3,000 year-old jar [pause 1] ok") == 7


def test_slug_and_title():
    assert T.slug("Hello, World! [pause]") == "hello-world"
    assert T.slug("!!!") == "voiceover"
    assert T.title_of("a b c d e f g h i") == "a b c d e f g..."


def test_slug_fallback_for_non_latin_names():
    assert T.slug("蜂蜜永远不会变质") == "voiceover"
    assert T.slug("ပျားရည်", "captions") == "captions"
