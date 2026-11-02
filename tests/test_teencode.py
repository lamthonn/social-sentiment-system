from preprocessing.teencode import normalize_teencode


def test_replaces_common_teencode():
    assert normalize_teencode("mik ko bik j") == "mình không biết gì"


def test_is_case_insensitive():
    assert normalize_teencode("Mik Ko") == "mình không"


def test_does_not_match_inside_longer_words():
    # "kho" (nhà kho) không được tách nhầm thành "k" + "ho".
    assert normalize_teencode("cái kho này") == "cái kho này"


def test_leaves_unknown_words_untouched():
    assert normalize_teencode("hôm nay trời đẹp") == "hôm nay trời đẹp"


def test_replaces_multi_word_phrase():
    assert normalize_teencode("Ủa, jz bạn ơi") == "Ủa, gì vậy bạn ơi"
