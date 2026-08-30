"""Client gọi YouTube Data API v3 (dùng httpx trực tiếp, không cần Google SDK)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx

from config.settings import settings

BASE_URL = "https://www.googleapis.com/youtube/v3"

_YOUTUBE_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com"}


class YouTubeAPIError(RuntimeError):
    """Lỗi khi gọi YouTube Data API (hết quota, video không tồn tại, comment bị tắt...)."""


def extract_video_id(value: str) -> str:
    """Nhận video ID thuần HOẶC URL YouTube đầy đủ (watch?v=..., youtu.be/..., /shorts/...),
    kể cả khi kèm tham số thừa (`&list=`, `&t=`, hoặc dán nhầm `?list=` ngay sau ID).

    VD tất cả đều trả về "I-Y4kN5LXy8":
      - "I-Y4kN5LXy8"
      - "I-Y4kN5LXy8?list=RDzbAu6MLBWZg"                      (dán nhầm playlist)
      - "https://www.youtube.com/watch?v=I-Y4kN5LXy8&list=..."
      - "https://youtu.be/I-Y4kN5LXy8?list=..."
    """
    value = value.strip()
    parsed = urlparse(value)

    if parsed.netloc in _YOUTUBE_HOSTS and parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if video_id:
            return video_id

    if parsed.netloc == "youtu.be":
        return parsed.path.lstrip("/")

    # Không có netloc -> không phải URL, chỉ là ID (có thể kèm "?..."/"&..." dán nhầm) - lấy phần path
    if not parsed.netloc:
        return parsed.path

    # Dạng khác của youtube.com (VD /shorts/<id>, /embed/<id>) - lấy segment cuối path
    return parsed.path.rstrip("/").rsplit("/", 1)[-1]


def _get(path: str, params: dict) -> dict:
    params = {**params, "key": settings.youtube_api_key}
    resp = httpx.get(f"{BASE_URL}/{path}", params=params, timeout=15.0)
    if resp.status_code != 200:
        raise YouTubeAPIError(f"{path} -> HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def fetch_comment_threads(video_id: str, page_token: str | None = None, max_results: int = 100) -> dict:
    """Lấy 1 trang comment gốc (top-level) của 1 video.

    Tối đa 100 comment/lần gọi, tốn 1 unit quota/lần (quota mặc định: 10.000 unit/ngày).
    """
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "order": "time",
        "textFormat": "plainText",
    }
    if page_token:
        params["pageToken"] = page_token
    return _get("commentThreads", params)


def iter_comment_threads(video_id: str, max_pages: int | None = None):
    """Generator duyệt qua các trang comment của 1 video (tới hết hoặc tới max_pages)."""
    page_token = None
    pages = 0
    while True:
        data = fetch_comment_threads(video_id, page_token=page_token)
        yield from data.get("items", [])
        page_token = data.get("nextPageToken")
        pages += 1
        if not page_token or (max_pages is not None and pages >= max_pages):
            break


def search_videos(
    query: str,
    max_results: int = 25,
    published_after_days: int | None = 7,
    order: str = "date",
    region_code: str = "VN",
    relevance_language: str = "vi",
) -> list[dict]:
    """Tìm video công khai theo từ khóa (search.list).

    ⚠️ Tốn **100 unit quota/lần gọi** (khác hẳn commentThreads.list chỉ 1 unit/lần) -
    cân nhắc kỹ số lần gọi khi dùng trong scheduler (xem cảnh báo trong collector/README.md).
    Chỉ lấy 1 trang (tối đa 50 kết quả/trang theo giới hạn của API) - đủ dùng cho quét
    định kỳ tìm video mới, không cần duyệt hết lịch sử.
    """
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": order,  # "date" -> ưu tiên video mới nhất, phù hợp theo dõi xu hướng
        "maxResults": min(max_results, 50),
        "regionCode": region_code,
        "relevanceLanguage": relevance_language,
    }
    if published_after_days is not None:
        published_after = datetime.now(timezone.utc) - timedelta(days=published_after_days)
        params["publishedAfter"] = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")

    data = _get("search", params)
    return data.get("items", [])
