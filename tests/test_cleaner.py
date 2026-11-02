import unicodedata

from preprocessing.cleaner import clean_text


def test_unescapes_html_entities():
    assert clean_text("Tin &amp; b&#224;i") == "Tin & bài"


def test_removes_urls():
    assert clean_text("Xem thêm tại https://example.com/abc?x=1 nhé") == "Xem thêm tại nhé"
    assert clean_text("Link: www.example.com hay quá") == "Link: hay quá"


def test_collapses_repeated_characters():
    assert clean_text("đẹppppp quááááá") == "đẹp quá"


def test_keeps_double_repeated_characters():
    # Lặp đúng 2 lần không bị coi là nhấn mạnh quá mức - giữ nguyên.
    assert clean_text("xem xong") == "xem xong"


def test_collapses_repeated_punctuation():
    assert clean_text("Hay quá!!!! Thật ạ???") == "Hay quá! Thật ạ?"


def test_normalizes_whitespace():
    assert clean_text("  nhiều    khoảng   trắng  \n\t") == "nhiều khoảng trắng"


def test_normalizes_unicode_nfc():
    nfc_text = "không"
    nfd_text = unicodedata.normalize("NFD", nfc_text)
    assert nfd_text != nfc_text  # 2 chuỗi khác nhau ở mức byte dù nhìn giống hệt nhau
    assert clean_text(nfd_text) == clean_text(nfc_text) == nfc_text
