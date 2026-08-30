"""Client gọi TikTok Research API - Video Comment List.

⚠️ CHƯA TEST bằng key thật (client_key/client_secret cần đăng ký & được TikTok
duyệt: https://developers.tiktok.com/products/research-api). Endpoint/field
dưới đây viết theo tài liệu công khai tại thời điểm viết code - TikTok có thể
đổi field/endpoint theo thời gian. **Việc đầu tiên cần làm khi có key thật**:
gọi thử `fetch_video_comments()` với 1 video_id thật, in ra response JSON đầy
đủ, đối chiếu lại với `_parse_comment` bên collector/pipeline.py (đặc biệt
phần lấy định danh tác giả - xem ghi chú trong pipeline.py).

Tài liệu tham khảo: https://developers.tiktok.com/doc/research-api-specs-query-video-comments
"""
from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx

from config.settings import settings

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
COMMENT_LIST_URL = "https://open.tiktokapis.com/v2/research/video/comment/list/"
# Field theo tài liệu Research API - kiểm tra lại danh sách field khả dụng khi có key thật,
# có thể cần thêm field khác (VD: reply_count) hoặc field tên khác đi.
COMMENT_FIELDS = "id,like_count,create_time,text,video_id,parent_comment_id"

_token_cache: dict[str, object] = {"access_token": "", "expires_at": 0.0}


class TikTokAPIError(RuntimeError):
    """Lỗi khi gọi TikTok Research API (token hết hạn, chưa được cấp quyền, video không tồn tại...)."""


def _get_access_token() -> str:
    """Lấy access token (OAuth2 client credentials grant), cache tới gần hết hạn thì xin lại."""
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:  # type: ignore[operator]
        return _token_cache["access_token"]  # type: ignore[return-value]

    resp = httpx.post(
        TOKEN_URL,
        data={
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "grant_type": "client_credentials",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15.0,
    )
    if resp.status_code != 200:
        raise TikTokAPIError(f"Lấy access token thất bại -> HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    # Đã test thật: endpoint này trả HTTP 200 ngay cả khi thiếu/sai client_key - client_secret,
    # lỗi nằm trong body JSON chứ không phải status code. Phải check key "access_token" tồn tại.
    if "access_token" not in data:
        raise TikTokAPIError(f"Lấy access token thất bại -> body: {data}")
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 7200)
    return _token_cache["access_token"]  # type: ignore[return-value]


def fetch_video_comments(video_id: str, cursor: int = 0, max_count: int = 100) -> dict:
    """Lấy 1 trang comment của 1 video TikTok (tối đa 100 comment/lần theo tài liệu)."""
    token = _get_access_token()
    resp = httpx.post(
        f"{COMMENT_LIST_URL}?fields={COMMENT_FIELDS}",
        json={"video_id": int(video_id), "cursor": cursor, "max_count": max_count},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=15.0,
    )
    if resp.status_code != 200:
        raise TikTokAPIError(f"comment/list -> HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def iter_video_comments(video_id: str, max_pages: int | None = None):
    """Generator duyệt các trang comment của 1 video TikTok."""
    cursor = 0
    pages = 0
    while True:
        payload = fetch_video_comments(video_id, cursor=cursor)
        data = payload.get("data", {})
        yield from data.get("comments", [])

        pages += 1
        has_more = data.get("has_more", False)
        cursor = data.get("cursor", cursor)
        if not has_more or (max_pages is not None and pages >= max_pages):
            break


def extract_video_id(value: str) -> str:
    """Nhận video ID thuần (dạng số) hoặc URL TikTok đầy đủ, VD:
    "https://www.tiktok.com/@user/video/7123456789012345678" -> "7123456789012345678"
    """
    value = value.strip()
    parsed = urlparse(value)
    if not parsed.netloc:
        return parsed.path  # chỉ là ID (có thể kèm "?..."/"&..." dán nhầm) - lấy path
    return parsed.path.rstrip("/").rsplit("/", 1)[-1]
