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
        "part": "snippet,replies",  # replies: kèm tối đa 5 trả lời đầu mỗi bình luận, không tốn thêm quota
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


def iter_replies(parent_id: str):
    """Generator duyệt TẤT CẢ trả lời của 1 bình luận gốc (comments.list, 1 unit/trang tối đa 100)."""
    page_token = None
    while True:
        params = {"part": "snippet", "parentId": parent_id, "maxResults": 100, "textFormat": "plainText"}
        if page_token:
            params["pageToken"] = page_token
        data = _get("comments", params)
        yield from data.get("items", [])
        page_token = data.get("nextPageToken")
        if not page_token:
            break


def fetch_videos(video_ids: list[str]) -> list[dict]:
    """Thông tin + số liệu (snippet, statistics) của nhiều video - 1 unit/lần gọi, tối đa 50 video/lần."""
    items: list[dict] = []
    for start in range(0, len(video_ids), 50):
        chunk = video_ids[start:start + 50]
        data = _get("videos", {"part": "snippet,statistics", "id": ",".join(chunk)})
        items.extend(data.get("items", []))
    return items


def fetch_most_popular(region_code: str = "VN", max_results: int = 20) -> list[dict]:
    """Video đang thịnh hành của 1 quốc gia (videos.list chart=mostPopular) - 1 unit/lần, đã kèm
    snippet + statistics nên không cần gọi thêm fetch_videos."""
    data = _get("videos", {
        "part": "snippet,statistics", "chart": "mostPopular",
        "regionCode": region_code, "maxResults": min(max_results, 50),
    })
    return data.get("items", [])


def fetch_channel_upload_ids(channel_id: str, max_results: int = 10) -> list[str]:
    """ID các video mới nhất của 1 kênh (playlistItems.list, 1 unit/lần).

    Playlist uploads của kênh `UCxxxx` luôn có ID `UUxxxx` nên khỏi gọi channels.list để tra.
    """
    data = _get("playlistItems", {
        "part": "contentDetails", "playlistId": "UU" + channel_id[2:], "maxResults": min(max_results, 50),
    })
    return [item["contentDetails"]["videoId"] for item in data.get("items", [])]


def resolve_channel_id(value: str) -> str:
    """Nhận ID kênh (UCxxxx), URL /channel/UCxxxx, hoặc @handle / URL /@handle -> trả về ID kênh UCxxxx.

    Chỉ trường hợp @handle mới gọi API (channels.list forHandle, 1 unit).
    """
    value = value.strip()
    parsed = urlparse(value)
    path = parsed.path if parsed.netloc else value
    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        raise YouTubeAPIError(f"Không nhận ra kênh YouTube từ '{value}'")

    if segments[0] == "channel" and len(segments) > 1:
        return segments[1]
    if segments[0].startswith("UC") and len(segments[0]) == 24:
        return segments[0]

    handle = next((seg for seg in segments if seg.startswith("@")), None)
    if handle is None:
        raise YouTubeAPIError(f"Không nhận ra kênh YouTube từ '{value}' (cần ID UCxxxx hoặc @handle)")
    data = _get("channels", {"part": "id", "forHandle": handle})
    items = data.get("items", [])
    if not items:
        raise YouTubeAPIError(f"Không tìm thấy kênh {handle}")
    return items[0]["id"]


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
