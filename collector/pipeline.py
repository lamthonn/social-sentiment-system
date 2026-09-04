"""Pipeline: thu thập comment (YouTube/TikTok) -> ẩn danh tác giả -> ghi bảng raw_posts."""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from datetime import datetime, timezone

from sqlalchemy import select

from security.anonymize import hash_identifier
from storage.database import SessionLocal
from storage.models import RawPost

logger = logging.getLogger(__name__)


def _parse_dt_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_youtube_comment(item: dict) -> dict:
    top = item["snippet"]["topLevelComment"]["snippet"]
    author_channel_id = top.get("authorChannelId", {}).get("value")
    return {
        "post_id": item["snippet"]["topLevelComment"]["id"],
        # authorChannelId ổn định hơn authorDisplayName (tên có thể trùng/đổi) - ưu tiên dùng để hash.
        "author_identifier": author_channel_id or top.get("authorDisplayName", "unknown"),
        "content": top.get("textDisplay", ""),
        "posted_at": _parse_dt_iso(top.get("publishedAt")),
    }


def _parse_tiktok_comment(item: dict) -> dict:
    # ⚠️ CHƯA XÁC MINH bằng key thật (xem cảnh báo trong collector/tiktok_client.py).
    # Tài liệu công khai của TikTok Research API cho Comment object KHÔNG liệt kê field
    # định danh tác giả comment rõ ràng (khác Video object có "username" của người đăng
    # video). Thử vài field khả dĩ trước, fallback về "unknown:<video_id>" nếu không có -
    # nghĩa là KHÔNG phân biệt được tác giả giữa các comment cùng video cho tới khi verify
    # lại bằng key thật (in response JSON thật ra xem có field nào khác không).
    author_identifier = item.get("user_id") or item.get("username") or f"unknown:{item.get('video_id')}"
    create_time = item.get("create_time")
    return {
        "post_id": str(item["id"]),
        "author_identifier": str(author_identifier),
        "content": item.get("text", ""),
        "posted_at": datetime.fromtimestamp(create_time, tz=timezone.utc) if create_time else None,
    }


def _ingest(
    platform: str,
    items: Iterable[dict],
    parse_fn: Callable[[dict], dict],
    category: str | None = None,
) -> int:
    """Duyệt qua các item thô (comment) của 1 video, ẩn danh tác giả, ghi raw_posts, bỏ qua trùng."""
    inserted = 0
    with SessionLocal() as session:
        for raw_item in items:
            parsed = parse_fn(raw_item)

            exists = session.execute(
                select(RawPost.id).where(
                    RawPost.platform == platform,
                    RawPost.post_id == parsed["post_id"],
                )
            ).first()
            if exists:
                continue

            session.add(
                RawPost(
                    platform=platform,
                    post_id=parsed["post_id"],
                    author_hash=hash_identifier(parsed["author_identifier"]),
                    content=parsed["content"],
                    posted_at=parsed["posted_at"],
                    category=category,
                )
            )
            inserted += 1

        session.commit()

    return inserted


def collect_youtube_video_comments(video_id: str, max_pages: int | None = None, category: str | None = None) -> int:
    """Thu thập comment của 1 video YouTube, ghi vào raw_posts. Trả về số bản ghi mới (bỏ qua trùng)."""
    from collector.youtube_client import iter_comment_threads

    inserted = _ingest(
        "youtube", iter_comment_threads(video_id, max_pages=max_pages), _parse_youtube_comment, category=category,
    )
    logger.info("[youtube] Video %s (category=%s): thu thập %d comment mới", video_id, category, inserted)
    return inserted


def collect_tiktok_video_comments(video_id: str, max_pages: int | None = None, category: str | None = None) -> int:
    """Thu thập comment của 1 video TikTok, ghi vào raw_posts. Trả về số bản ghi mới (bỏ qua trùng)."""
    from collector.tiktok_client import iter_video_comments

    inserted = _ingest(
        "tiktok", iter_video_comments(video_id, max_pages=max_pages), _parse_tiktok_comment, category=category,
    )
    logger.info("[tiktok] Video %s (category=%s): thu thập %d comment mới", video_id, category, inserted)
    return inserted


_COLLECTORS: dict[str, Callable[..., int]] = {
    "youtube": collect_youtube_video_comments,
    "tiktok": collect_tiktok_video_comments,
}


def collect_many(
    platform: str,
    videos: list[str] | list[tuple[str, str | None]],
    max_pages: int | None = None,
) -> dict[str, int]:
    """Thu thập nhiều video của 1 nền tảng; lỗi ở 1 video không làm hỏng cả batch.

    `videos` nhận list video_id thuần (không gắn category) HOẶC list (video_id, category)
    - mỗi video có thể có category riêng (VD lấy từ label của từng tracked_video).
    """
    collect_fn = _COLLECTORS[platform]
    results: dict[str, int] = {}
    for item in videos:
        video_id, category = item if isinstance(item, tuple) else (item, None)
        try:
            results[video_id] = collect_fn(video_id, max_pages=max_pages, category=category)
        except Exception:
            logger.exception("[%s] Lỗi khi thu thập video %s", platform, video_id)
            results[video_id] = 0
    return results


def discover_and_collect_youtube(
    query: str,
    max_videos: int = 10,
    published_within_days: int | None = 7,
    max_pages: int | None = None,
    category: str | None = None,
) -> dict[str, dict]:
    """Tìm video YouTube mới theo từ khóa rồi thu thập luôn comment - không cần biết trước video ID.

    Trả về {video_id: {"title": ..., "inserted": số comment mới}}.
    ⚠️ search_videos() tốn 100 unit quota/lần gọi (xem cảnh báo trong youtube_client.py) -
    gọi 1 lần/từ khóa/lượt chạy, không phụ thuộc max_videos.
    category mặc định = chính từ khóa search (query) nếu không truyền riêng - dùng để lọc
    dữ liệu theo chủ đề sau này (xem RawPost.category).
    """
    from collector.youtube_client import search_videos

    category = category if category is not None else query
    videos = search_videos(query, max_results=max_videos, published_after_days=published_within_days)

    results: dict[str, dict] = {}
    for video in videos:
        video_id = video["id"]["videoId"]
        title = video["snippet"]["title"]
        try:
            inserted = collect_youtube_video_comments(video_id, max_pages=max_pages, category=category)
        except Exception:
            logger.exception("[youtube-search] Lỗi khi thu thập video %s (%s)", video_id, title)
            inserted = 0
        results[video_id] = {"title": title, "inserted": inserted}

    return results
