"""Pipeline tiền xử lý NLP tiếng Việt (Giai đoạn 1).

Thứ tự bắt buộc: làm sạch -> chuẩn hoá teencode -> tách câu -> tách từ. Đảo thứ tự sẽ cho
kết quả sai (VD tách từ trước khi chuẩn hoá teencode sẽ khiến "ko" bị coi là 1 từ độc lập
thay vì được thay bằng "không").

Dùng làm bước tiền xử lý trước khi fine-tune/suy luận mô hình cảm xúc (PhoBERT/ViSoBERT)
trên nội dung trong bảng `raw_posts` (xem storage/models.py).
"""
from __future__ import annotations

from dataclasses import dataclass

from preprocessing.cleaner import clean_text
from preprocessing.teencode import normalize_teencode
from preprocessing.tokenizer import split_sentences, tokenize


@dataclass
class PreprocessedText:
    normalized_text: str           # đã làm sạch + chuẩn hoá teencode, CHƯA tách câu/từ
    sentences: list[str]           # normalized_text đã tách câu
    tokenized_sentences: list[str]  # từng câu đã tách từ (nối bằng "_")
    tokenized_text: str             # toàn bộ text đã tách từ - sẵn sàng cho PhoBERT/ViSoBERT


def preprocess(raw_text: str) -> PreprocessedText:
    """Chạy toàn bộ pipeline tiền xử lý cho 1 đoạn text thô (1 bài đăng/bình luận)."""
    normalized = normalize_teencode(clean_text(raw_text))
    sentences = split_sentences(normalized)
    tokenized_sentences = [tokenize(s) for s in sentences]
    return PreprocessedText(
        normalized_text=normalized,
        sentences=sentences,
        tokenized_sentences=tokenized_sentences,
        tokenized_text=" ".join(tokenized_sentences),
    )
