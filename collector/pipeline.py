"""Pipeline: thu thập comment (YouTube/TikTok) -> ẩn danh tác giả -> ghi bảng raw_posts."""
from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable
from datetime import datetime, timezone

from sqlalchemy import select, update

from config.settings import settings
from security.anonymize import hash_identifier
from storage.database import SessionLocal
from storage.models import RawPost, VideoMeta, VideoStatSnapshot

logger = logging.getLogger(__name__)


def _parse_dt_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_youtube_comment(item: dict) -> dict:
    """Chuẩn hóa 1 bình luận YouTube - nhận cả commentThread (bình luận gốc) lẫn comment (trả lời)."""
    snippet = item["snippet"]
    if "topLevelComment" in snippet:  # commentThread -> bình luận gốc
        comment = snippet["topLevelComment"]
        top, post_id, reply_count = comment["snippet"], comment["id"], snippet.get("totalReplyCount", 0)
    else:  # comment resource -> trả lời của 1 bình luận gốc
        top, post_id, reply_count = snippet, item["id"], None
    author_channel_id = top.get("authorChannelId", {}).get("value")
    return {
        "post_id": post_id,
        # authorChannelId ổn định hơn authorDisplayName (tên có thể trùng/đổi) - ưu tiên dùng để hash.
        "author_identifier": author_channel_id or top.get("authorDisplayName", "unknown"),
        "content": top.get("textDisplay", ""),
        "posted_at": _parse_dt_iso(top.get("publishedAt")),
        "video_id": top.get("videoId"),
        "parent_id": top.get("parentId"),
        "like_count": top.get("likeCount"),
        "reply_count": reply_count,
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
    video_id: str | None = None,
) -> int:
    """Duyệt qua các item thô (comment) của 1 video, ẩn danh tác giả, ghi raw_posts, bỏ qua trùng.

    Bình luận đã có thì không thêm lại, nhưng cập nhật like_count/reply_count (và video_id nếu
    bản cũ chưa có) khi số liệu mới khác. Trả về số bản ghi MỚI.
    """
    inserted = 0
    with SessionLocal() as session:
        for raw_item in items:
            parsed = parse_fn(raw_item)
            context = {
                "video_id": parsed.get("video_id") or video_id,
                "like_count": parsed.get("like_count"),
                "reply_count": parsed.get("reply_count"),
            }

            exists = session.execute(
                select(RawPost.id, RawPost.video_id, RawPost.like_count, RawPost.reply_count).where(
                    RawPost.platform == platform,
                    RawPost.post_id == parsed["post_id"],
                )
            ).first()
            if exists:
                changes = {
                    key: value for key, value in context.items()
                    if value is not None and value != getattr(exists, key)
                }
                if changes:
                    session.execute(update(RawPost).where(RawPost.id == exists.id).values(**changes))
                continue

            session.add(
                RawPost(
                    platform=platform,
                    post_id=parsed["post_id"],
                    author_hash=hash_identifier(parsed["author_identifier"]),
                    content=parsed["content"],
                    posted_at=parsed["posted_at"],
                    category=category,
                    parent_id=parsed.get("parent_id"),
                    **context,
                )
            )
            inserted += 1

        session.commit()

    return inserted


def _known_reply_counts(platform: str, post_ids: list[str]) -> dict[str, int | None]:
    """{post_id: reply_count đã lưu} cho các bình luận đã có trong DB (bình luận mới không có trong dict)."""
    if not post_ids:
        return {}
    with SessionLocal() as session:
        rows = session.execute(
            select(RawPost.post_id, RawPost.reply_count).where(
                RawPost.platform == platform, RawPost.post_id.in_(post_ids)
            )
        ).all()
    return {post_id: reply_count for post_id, reply_count in rows}


def collect_youtube_video_comments(
    video_id: str,
    max_pages: int | None = None,
    category: str | None = None,
    incremental: bool = False,
) -> int:
    """Thu thập comment (gốc + trả lời) của 1 video YouTube, ghi vào raw_posts. Trả về số bản ghi mới.

    incremental=True (dùng cho scheduler): comment duyệt từ mới tới cũ nên dừng ngay khi gặp một
    trang không có gì mới - mỗi lượt định kỳ chỉ tốn ~1 unit/video thay vì duyệt lại cả video.
    Trả lời chỉ được lấy đủ (comments.list) khi số trả lời tăng so với lần thu thập trước.
    """
    from collector import youtube_client as yt

    inserted = 0
    page_token = None
    pages = 0
    while True:
        data = yt.fetch_comment_threads(video_id, page_token=page_token)
        threads = data.get("items", [])
        known = _known_reply_counts("youtube", [t["snippet"]["topLevelComment"]["id"] for t in threads])

        batch: list[dict] = []
        for thread in threads:
            batch.append(thread)
            inline = thread.get("replies", {}).get("comments", [])
            batch.extend(inline)
            if not settings.collector_fetch_replies:
                continue
            total = thread["snippet"].get("totalReplyCount", 0)
            top_id = thread["snippet"]["topLevelComment"]["id"]
            if total > len(inline) and (top_id not in known or (known[top_id] or 0) < total):
                batch.extend(yt.iter_replies(top_id))

        page_new = _ingest("youtube", batch, _parse_youtube_comment, category=category, video_id=video_id)
        inserted += page_new

        page_token = data.get("nextPageToken")
        pages += 1
        if not page_token or (max_pages is not None and pages >= max_pages):
            break
        if incremental and page_new == 0:
            break

    logger.info("[youtube] Video %s (category=%s): thu thập %d comment mới", video_id, category, inserted)
    return inserted


# ===== Thông tin video + số liệu theo thời gian (video_meta, video_stats_snapshots) =====


def _to_int(value) -> int | None:
    """YouTube trả số dạng chuỗi ("1234"); trường bị ẩn thì không có -> None."""
    return int(value) if value is not None else None


def _parse_video(item: dict) -> dict:
    """Chuẩn hóa 1 video resource (snippet + statistics) của YouTube."""
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    return {
        "video_id": item["id"],
        "title": snippet.get("title", ""),
        "description": snippet.get("description"),
        "channel_id": snippet.get("channelId"),
        "channel_title": snippet.get("channelTitle"),
        "category_id": snippet.get("categoryId"),
        "tags": json.dumps(snippet["tags"], ensure_ascii=False) if snippet.get("tags") else None,
        "default_language": snippet.get("defaultLanguage") or snippet.get("defaultAudioLanguage"),
        "published_at": _parse_dt_iso(snippet.get("publishedAt")),
        "view_count": _to_int(stats.get("viewCount")),
        "like_count": _to_int(stats.get("likeCount")),
        "comment_count": _to_int(stats.get("commentCount")),
    }


def _save_video_items(items: list[dict]) -> None:
    """Cập nhật video_meta (mỗi video 1 dòng) và thêm 1 snapshot số liệu cho mỗi video."""
    now = datetime.utcnow()
    with SessionLocal() as session:
        for item in items:
            info = _parse_video(item)
            stats = {key: info.pop(key) for key in ("view_count", "like_count", "comment_count")}
            video_id = info.pop("video_id")

            row = session.execute(
                select(VideoMeta).where(VideoMeta.platform == "youtube", VideoMeta.video_id == video_id)
            ).scalar_one_or_none()
            if row is None:
                session.add(VideoMeta(platform="youtube", video_id=video_id, first_seen_at=now, updated_at=now, **info))
            else:
                for key, value in info.items():
                    setattr(row, key, value)
                row.updated_at = now

            session.add(VideoStatSnapshot(platform="youtube", video_id=video_id, captured_at=now, **stats))
        session.commit()


def _refresh_youtube_video_info(video_ids: list[str]) -> None:
    """Lưu thông tin + snapshot cho các video đã biết ID. Lỗi chỉ ghi log, không làm hỏng việc thu thập comment."""
    from collector.youtube_client import fetch_videos

    try:
        _save_video_items(fetch_videos(video_ids))
    except Exception:
        logger.exception("[youtube] Lỗi khi cập nhật thông tin %d video", len(video_ids))


def collect_tiktok_video_comments(
    video_id: str, max_pages: int | None = None, category: str | None = None, incremental: bool = False,
) -> int:
    """Thu thập comment của 1 video TikTok, ghi vào raw_posts. Trả về số bản ghi mới (bỏ qua trùng).

    `incremental` chỉ để chung chữ ký với YouTube, TikTok luôn duyệt hết."""
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
    incremental: bool = False,
) -> dict[str, int]:
    """Thu thập nhiều video của 1 nền tảng; lỗi ở 1 video không làm hỏng cả batch.

    `videos` nhận list video_id thuần (không gắn category) HOẶC list (video_id, category)
    - mỗi video có thể có category riêng (VD lấy từ label của từng tracked_video).
    Với YouTube, mỗi lượt còn lưu thông tin video + snapshot số liệu (1 unit cho 50 video).
    """
    collect_fn = _COLLECTORS[platform]
    results: dict[str, int] = {}
    for item in videos:
        video_id, category = item if isinstance(item, tuple) else (item, None)
        try:
            results[video_id] = collect_fn(video_id, max_pages=max_pages, category=category, incremental=incremental)
        except Exception:
            logger.exception("[%s] Lỗi khi thu thập video %s", platform, video_id)
            results[video_id] = 0

    if platform == "youtube" and results:
        _refresh_youtube_video_info(list(results))
    return results


def _collect_video_items(
    items: list[dict], category: str | None, max_pages: int | None, incremental: bool,
) -> dict[str, dict]:
    """Lưu thông tin video rồi thu thập comment của từng video. Trả về {video_id: {"title", "inserted"}}.

    Video có commentCount = 0 được bỏ qua, đỡ tốn 1 unit gọi commentThreads vô ích.
    """
    _save_video_items(items)

    results: dict[str, dict] = {}
    for item in items:
        info = _parse_video(item)
        video_id, title = info["video_id"], info["title"]
        inserted = 0
        if info["comment_count"] != 0:
            try:
                inserted = collect_youtube_video_comments(
                    video_id, max_pages=max_pages, category=category, incremental=incremental,
                )
            except Exception:
                logger.exception("[youtube] Lỗi khi thu thập video %s (%s)", video_id, title)
        results[video_id] = {"title": title, "inserted": inserted}
    return results


def discover_and_collect_youtube(
    query: str,
    max_videos: int = 10,
    published_within_days: int | None = 7,
    max_pages: int | None = None,
    category: str | None = None,
    incremental: bool = False,
) -> dict[str, dict]:
    """Tìm video YouTube mới theo từ khóa rồi thu thập luôn comment - không cần biết trước video ID.

    Trả về {video_id: {"title": ..., "inserted": số comment mới}}.
    ⚠️ search_videos() tốn 100 unit quota/lần gọi (xem cảnh báo trong youtube_client.py) -
    gọi 1 lần/từ khóa/lượt chạy, không phụ thuộc max_videos.
    category mặc định = chính từ khóa search (query) nếu không truyền riêng - dùng để lọc
    dữ liệu theo chủ đề sau này (xem RawPost.category).
    """
    from collector.youtube_client import fetch_videos, search_videos

    category = category if category is not None else query
    found = search_videos(query, max_results=max_videos, published_after_days=published_within_days)
    video_ids = [video["id"]["videoId"] for video in found]
    if not video_ids:
        return {}
    return _collect_video_items(fetch_videos(video_ids), category, max_pages, incremental)


def collect_youtube_channel(
    channel_id: str,
    max_videos: int = 10,
    category: str | None = None,
    max_pages: int | None = None,
    incremental: bool = True,
) -> dict[str, dict]:
    """Thu thập comment của `max_videos` video mới nhất của 1 kênh (rẻ: 2 unit + 1 unit/video, không search)."""
    from collector.youtube_client import fetch_channel_upload_ids, fetch_videos

    category = category if category is not None else channel_id
    video_ids = fetch_channel_upload_ids(channel_id, max_results=max_videos)
    if not video_ids:
        return {}
    return _collect_video_items(fetch_videos(video_ids), category, max_pages, incremental)


def _is_vietnamese_video(item: dict) -> bool:
    """Video không khai báo ngôn ngữ thì giữ (đa số video Việt không khai báo); khai báo khác 'vi' thì bỏ."""
    snippet = item.get("snippet", {})
    lang = snippet.get("defaultLanguage") or snippet.get("defaultAudioLanguage")
    return not lang or lang.lower().startswith("vi")


def collect_youtube_trending(
    region_code: str = "VN",
    max_videos: int = 20,
    max_pages: int | None = None,
    incremental: bool = True,
) -> dict[str, dict]:
    """Thu thập comment của các video đang thịnh hành (chart=mostPopular) - bắt chủ đề nổi mà không cần từ khóa."""
    from collector.youtube_client import fetch_most_popular

    items = fetch_most_popular(region_code=region_code, max_results=max_videos)
    # chart mostPopular của VN vẫn lẫn video quốc tế (hàng chục nghìn bình luận tiếng Anh) -> bỏ video có ngôn ngữ khác tiếng Việt
    items = [item for item in items if _is_vietnamese_video(item)]
    return _collect_video_items(items, "trending", max_pages, incremental)
