"""Tiền xử lý văn bản mạng xã hội tiếng Việt (bước PL-02, các bước CL-01…CL-08 trong PROJECT.md).

Thuần Python, không phụ thuộc thư viện ngoài. Dùng chung cho dữ liệu thu thập (pipeline clean)
và dữ liệu huấn luyện (UIT-VSFC, UIT-VSMEC) để mô hình thấy cùng một kiểu văn bản.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

PIPELINE_VERSION = "clean-v1"

# ----- CL-08: che thông tin cá nhân trong nội dung -----
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\d)")
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)
_MENTION_RE = re.compile(r"(?<!\w)@[\w.]{2,}")

# ----- CL-02: chuẩn hóa vị trí dấu thanh kiểu cũ -> kiểu mới (hoà -> hòa, thuý -> thúy, trừ "qu") -----
_TONE_FIX = {
    "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
    "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
    "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
}
_TONE_RE = re.compile(r"(?<![qQ])(" + "|".join(_TONE_FIX) + r")(?=[^a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]|$)")

# ----- CL-04: teencode / viết tắt phổ biến (chỉ các từ ít nhập nhằng) -----
TEENCODE = {
    "k": "không", "ko": "không", "kh": "không", "khg": "không", "kg": "không", "hok": "không", "hông": "không", "hem": "không",
    "đc": "được", "dc": "được", "đk": "được", "dk": "được", "đươc": "được",
    "j": "gì", "ji": "gì", "z": "vậy", "zậy": "vậy", "dzậy": "vậy", "vậyy": "vậy",
    "vs": "với", "mn": "mọi người", "mng": "mọi người", "ng": "người", "ngta": "người ta",
    "bt": "bình thường", "bth": "bình thường", "cx": "cũng", "cg": "cũng", "ntn": "như thế nào",
    "trc": "trước", "thik": "thích", "thjk": "thích", "iu": "yêu", "sp": "sản phẩm", "ae": "anh em",
    "nt": "nhắn tin", "hqua": "hôm qua", "hnay": "hôm nay", "mk": "mình", "mik": "mình", "mjk": "mình",
    "wá": "quá", "wa": "quá", "qá": "quá", "dzui": "vui", "zui": "vui", "fải": "phải", "fai": "phải",
    "nhìu": "nhiều", "nhiu": "nhiều", "bik": "biết", "bít": "biết", "bjt": "biết", "lun": "luôn",
    "đag": "đang", "dag": "đang", "ms": "mới", "mún": "muốn", "zai": "trai", "tks": "cảm ơn",
    "thanks": "cảm ơn", "thank": "cảm ơn", "cmt": "bình luận", "ib": "nhắn tin", "rep": "trả lời",
}
_WORD_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)

# ----- emoji: giữ nguyên cho Transformer; baseline TF-IDF dùng emoji_tags() đổi sang từ -----
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐❤️‍]+"
)
_EMOJI_GROUPS = {
    "emovui": "😂🤣😆😁😄😀😃😊☺😍🥰😘😻👍👏🎉💯❤♥💕💖💗😎🤩🥳🙌",
    "emobuon": "😢😭😞😔☹🙁😟😥💔😿😓",
    "emogian": "😡🤬😠👎😤🖕",
    "emoso": "😱😨😰😧",
    "emoghe": "🤮🤢😒🙄😑",
    "emongacnhien": "😮😲😯🤯😳",
}
_EMOJI_TAG = {ch: tag for tag, chars in _EMOJI_GROUPS.items() for ch in chars}

# ----- CL-07: dấu hiệu spam / quảng cáo -----
_PROMO_RE = re.compile(
    r"\b(inbox|ib|liên hệ|lien he|zalo|giảm giá|khuyến mãi|khuyen mai|sale|mua ngay|đặt hàng|dat hang|"
    r"kiếm tiền|kiem tien|thu nhập|việc nhẹ|đăng ký ngay|link|free ship|freeship|order)\b",
    re.I,
)
_VI_CHARS = set("ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ")
_VI_PLAIN_WORDS = {
    "khong", "duoc", "nguoi", "la", "cua", "toi", "ban", "qua", "nay", "roi", "thi", "ma", "co", "di", "ve",
    "nhung", "cung", "rat", "lam", "minh", "anh", "em", "chi", "nhu", "the", "nao", "gi", "vay", "thoi",
}


@dataclass
class CleanResult:
    text: str
    lang: str  # "vi" / "other" / "unk"
    is_spam: bool
    pii_masked: int
    urls: int


def _fix_tone(text: str) -> str:
    return _TONE_RE.sub(lambda m: _TONE_FIX[m.group(1)], text)


def _collapse_repeats(text: str) -> str:
    # "quáaaa" -> "quáa"? Không: gộp ký tự chữ lặp >= 3 lần về 1 lần ("đẹpppp" -> "đẹp"), emoji lặp về 1
    text = re.sub(r"([^\W\d_])\1{2,}", r"\1", text)
    text = re.sub(r"(" + _EMOJI_RE.pattern + r")(?:\s*\1)+", r"\1", text)
    return re.sub(r"[^\W\d_]+", lambda m: _strip_stretched_vowel(m.group(0)), text)


def _base(ch: str) -> str:
    return unicodedata.normalize("NFD", ch)[0]


_HORN = set("ơớờởỡợưứừửữự")  # ư/ơ có gốc u/o nhưng "ưu", "ươ" là vần thật (cứu, rượu)


def _strip_stretched_vowel(word: str) -> str:
    # "quáa" -> "quá", "nhéee" -> "nhé": bỏ nguyên âm không dấu kéo dài sau nguyên âm cùng gốc.
    # Tiếng Việt không có từ kết thúc bằng 2 nguyên âm không dấu giống nhau -> gộp trước.
    while len(word) >= 3 and word[-1] in "aeiouy" and word[-2] == word[-1]:
        word = word[:-1]
    while len(word) >= 3 and word[-1] in "aeiouy" and word[-2] != word[-1] and word[-2] not in _HORN and _base(word[-2]) == word[-1]:
        word = word[:-1]
    return word


def expand_teencode(text: str) -> str:
    tokens = _WORD_RE.findall(text)
    return " ".join(TEENCODE.get(tok, tok) for tok in tokens)


def detect_lang(text: str) -> str:
    words = re.findall(r"[^\W\d_]+", text)
    if len(words) < 2:
        return "unk"
    if any(ch in _VI_CHARS for ch in text):
        return "vi"
    plain = sum(1 for w in words if w in _VI_PLAIN_WORDS)
    return "vi" if plain / len(words) >= 0.2 else "other"


def mask_pii(text: str) -> tuple[str, int]:
    count = 0

    def sub(pattern: re.Pattern, repl: str, s: str) -> str:
        nonlocal count
        s, n = pattern.subn(repl, s)
        count += n
        return s

    # token liền chữ (\w) để bước tách từ phía sau không cắt rời
    text = sub(_EMAIL_RE, " xxemail ", text)
    text = sub(_PHONE_RE, " xxsđt ", text)
    text = sub(_MENTION_RE, " xxngườidùng ", text)
    return text, count


def clean_text(raw: str) -> CleanResult:
    """Làm sạch một bình luận. Thứ tự: Unicode NFC -> che PII -> bỏ URL -> chữ thường ->
    chuẩn dấu thanh -> gộp ký tự lặp -> teencode -> chuẩn khoảng trắng."""
    text = unicodedata.normalize("NFC", raw or "")
    text, pii = mask_pii(text)
    text, urls = _URL_RE.subn(" ", text)
    text = text.lower().replace("#", " ")
    text = _fix_tone(text)
    text = _collapse_repeats(text)
    text = expand_teencode(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.!?;:)])", r"\1", text).replace("( ", "(")

    letters = re.sub(r"[^\w]", "", text.replace("_", ""))
    is_spam = bool(_PROMO_RE.search(text) and (urls or pii)) or len(letters) < 2 or urls >= 2
    return CleanResult(text=text, lang=detect_lang(text), is_spam=is_spam, pii_masked=pii, urls=urls)


_HASHTAG_RE = re.compile(r"(?<!\w)#([^\W_][\w]{1,49})", re.UNICODE)


def extract_hashtags(raw: str) -> list[str]:
    """Hashtag trong nội dung GỐC (trước khi clean_text bỏ dấu #), chữ thường, NFC, không trùng, giữ thứ tự."""
    seen: list[str] = []
    for tag in _HASHTAG_RE.findall(unicodedata.normalize("NFC", raw or "")):
        tag = "#" + tag.lower()
        if tag not in seen:
            seen.append(tag)
    return seen


def emoji_tags(text: str) -> str:
    """Dùng cho baseline TF-IDF: đổi emoji thành từ mang nghĩa cảm xúc (emovui, emobuon…)."""
    return _EMOJI_RE.sub(lambda m: " " + " ".join(_EMOJI_TAG.get(ch, "emokhac") for ch in m.group(0) if ch not in "️‍") + " ", text)
