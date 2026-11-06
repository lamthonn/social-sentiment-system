"""Làm sạch text thô (bài đăng/bình luận MXH) trước khi chuẩn hoá teencode/tách câu/tách từ.

Xử lý các vấn đề phổ biến của text thu thập qua API (HTML entity còn sót lại, Unicode
không đồng nhất, URL, ký tự/dấu câu lặp lại quá mức do nhấn mạnh cảm xúc kiểu MXH -
VD "đẹppppp", "hay quá!!!!") - KHÔNG động vào emoji vì emoji mang tín hiệu cảm xúc quan
trọng cho mô hình sentiment ở bước sau.
"""
from __future__ import annotations

import html
import re
import unicodedata

_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Ký tự (chữ/số) lặp lại từ 3 lần liên tiếp trở lên -> rút gọn còn 1 (VD "đẹppppp" -> "đẹp").
# Lặp đúng 2 lần được giữ nguyên vì tiếng Việt có nhiều từ hợp lệ viết vậy (VD "cc", "xx").
_REPEATED_CHAR_PATTERN = re.compile(r"(\w)\1{2,}", flags=re.UNICODE)
# Dấu câu lặp lại (VD "!!!", "???", "...") -> giữ lại đúng 1 dấu.
_REPEATED_PUNCT_PATTERN = re.compile(r"([!?.,])\1+")


def clean_text(text: str) -> str:
    """Chuẩn hoá 1 đoạn text thô thành dạng sạch, ổn định - bước đầu tiên của pipeline
    tiền xử lý (xem preprocessing/pipeline.py)."""
    text = html.unescape(text)
    text = unicodedata.normalize("NFC", text)
    text = _URL_PATTERN.sub(" ", text)
    text = _REPEATED_CHAR_PATTERN.sub(r"\1", text)
    text = _REPEATED_PUNCT_PATTERN.sub(r"\1", text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()
    return text
