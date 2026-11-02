"""Từ điển & hàm chuẩn hoá teencode/từ viết tắt tiếng Việt phổ biến trên mạng xã hội.

Áp dụng SAU bước làm sạch (`preprocessing.cleaner.clean_text`) và TRƯỚC khi tách câu/tách
từ, để mô hình NLP (PhoBERT/ViSoBERT) không bị lẫn từ lóng với từ chuẩn khi fine-tune hay
suy luận.

⚠️ Từ điển không thể đầy đủ 100% - từ lóng MXH biến đổi liên tục theo thời gian (Concept
Drift, xem docs/crawling_qna_design.md mục 12 & 14). Một số mục (VD "t", "h", "z") vẫn có
thể khớp nhầm trong ngữ cảnh không phải chat (tên biến, đơn vị đo...) - đây là đánh đổi
chấp nhận được cho dữ liệu bình luận MXH. Mở rộng dần bằng cách thêm vào TEENCODE_MAP khi
phát hiện từ mới xuất hiện nhiều trong dữ liệu thực tế (VD qua thống kê tần suất từ OOV).
"""
from __future__ import annotations

import re

# Khoá bên trái là teencode/viết tắt (đã lowercase), giá trị bên phải là dạng chuẩn tiếng Việt.
TEENCODE_MAP: dict[str, str] = {
    # Phủ định
    "k": "không", "ko": "không", "hok": "không", "hông": "không", "khum": "không", "kg": "không",
    "kp": "không phải",
    # Đại từ nhân xưng
    "mik": "mình", "mk": "mình", "mjk": "mình", "t": "tôi", "tui": "tôi",
    # Động từ / tính từ phổ biến
    "dc": "được", "đc": "được", "bít": "biết", "bik": "biết", "iu": "yêu", "bùn": "buồn",
    "nhìu": "nhiều", "wa": "quá", "qa": "quá", "wá": "quá", "zui": "vui", "dg": "đúng",
    "thik": "thích", "thix": "thích", "kute": "dễ thương", "xink": "xinh",
    # Hỏi / chỉ định
    "ntn": "như thế nào", "sao z": "sao vậy", "z": "vậy", "zậy": "vậy", "dậy": "vậy",
    "j": "gì", "jz": "gì vậy", "jzậy": "gì vậy", "j v": "gì vậy",
    # Thời gian
    "bh": "bao giờ", "bjo": "bao giờ", "h": "giờ", "r": "rồi", "rùi": "rồi", "roài": "rồi",
    # Quan hệ / xưng hô MXH
    "ny": "người yêu", "ck": "chồng", "vk": "vợ", "kb": "kết bạn", "add": "kết bạn",
    # Viết tắt phổ biến khác
    "vs": "với", "sv": "sinh viên", "tl": "trả lời", "ib": "nhắn tin riêng", "sml": "sấp mặt luôn",
    "vcl": "quá đáng", "ok": "ok", "oki": "ok",
}

# Ghép thành 1 pattern regex khớp nguyên cụm từ (word boundary qua lookaround, không dùng \b vì
# 1 số khoá chứa khoảng trắng như "sao z"), ưu tiên khớp cụm dài trước để không bị khớp nhầm bởi
# 1 từ ngắn hơn nằm trong cụm dài (VD "jzậy" phải thử trước "j" và "z" riêng lẻ).
_SORTED_KEYS = sorted(TEENCODE_MAP, key=len, reverse=True)
_PATTERN = re.compile(
    r"(?<!\w)(" + "|".join(re.escape(k) for k in _SORTED_KEYS) + r")(?!\w)",
    flags=re.IGNORECASE | re.UNICODE,
)


def normalize_teencode(text: str) -> str:
    """Thay thế teencode/từ viết tắt phổ biến bằng từ chuẩn tiếng Việt.

    Khớp nguyên cụm từ, không phân biệt hoa/thường; từ không có trong từ điển được giữ nguyên.
    """
    return _PATTERN.sub(lambda m: TEENCODE_MAP[m.group(0).lower()], text)
