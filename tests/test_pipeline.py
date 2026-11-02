from preprocessing.pipeline import preprocess


def test_normalizes_teencode_before_tokenizing():
    result = preprocess("Mik thấy sp này dc lắm. Nhưng giá hơi caooo!!!")
    assert "mình" in result.normalized_text
    assert "được" in result.normalized_text
    assert "ko" not in result.normalized_text.split()


def test_splits_into_sentences():
    result = preprocess("Sản phẩm tốt. Giao hàng nhanh. Sẽ ủng hộ tiếp!")
    assert len(result.sentences) == 3


def test_tokenized_text_joins_compound_words_with_underscore():
    result = preprocess("Học sinh đang học bài rất chăm chỉ.")
    assert "_" in result.tokenized_text
    assert len(result.tokenized_sentences) == len(result.sentences)
