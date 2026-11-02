"""Tách câu & tách từ (word segmentation) tiếng Việt, dùng thư viện `underthesea`.

PhoBERT/ViSoBERT được pre-train trên dữ liệu ĐÃ tách từ (các từ ghép nhiều âm tiết được
nối bằng "_", VD "học_sinh", "trí_tuệ_nhân_tạo") - bắt buộc phải tách từ bằng đúng cách
này (không phải chỉ split theo khoảng trắng) trước khi đưa vào tokenizer của mô hình, nếu
không độ chính xác sẽ giảm đáng kể so với lúc pre-train.
"""
from __future__ import annotations

from underthesea import sent_tokenize as _sent_tokenize
from underthesea import word_tokenize as _word_tokenize


def split_sentences(text: str) -> list[str]:
    """Tách 1 đoạn text (có thể nhiều câu) thành danh sách câu. Bỏ câu rỗng sau khi strip."""
    return [s.strip() for s in _sent_tokenize(text) if s.strip()]


def tokenize(text: str) -> str:
    """Tách từ tiếng Việt cho 1 câu, trả về text với từ ghép nhiều âm tiết nối bằng "_"
    (đúng định dạng input mà PhoBERT/ViSoBERT cần)."""
    return _word_tokenize(text, format="text")
