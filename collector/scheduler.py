"""Lập lịch thu thập định kỳ bằng APScheduler (chạy dạng process riêng, đứng foreground).

Đọc cấu hình TRỰC TIẾP TỪ DB mỗi lượt chạy (bảng `tracked_videos` + `search_queries`,
quản lý qua UI/API - xem api/main.py) - không phải từ .env. Vì vậy thêm/sửa/xóa video
theo dõi hay từ khóa search qua UI có hiệu lực ngay ở lượt chạy kế tiếp, không cần
restart scheduler.

⚠️ Quota YouTube: mỗi từ khóa trong search_queries tốn 100 unit/lượt chạy (bất kể
max_videos). VD interval mặc định 60 phút (24 lượt/ngày) x 1 từ khóa = 2.400 unit/ngày
cho riêng phần search, cộng thêm phần lấy comment (1 unit/video) - vẫn thoải mái trong
hạn mức free 10.000 unit/ngày. Thêm nhiều từ khóa hoặc rút ngắn interval thì tính lại.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from collector.pipeline import collect_many
from config.settings import settings
from storage.database import SessionLocal
from storage.models import SearchQuery, TrackedVideo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_tracked_videos() -> dict[str, list[tuple[str, str | None]]]:
    """{platform: [(video_id, category), ...]} cho các video đang bật theo dõi (enabled=True).

    category lấy từ `label` của video (nếu có) - dùng để lọc dữ liệu theo chủ đề sau này.
    """
    result: dict[str, list[tuple[str, str | None]]] = {}
    with SessionLocal() as session:
        rows = session.execute(select(TrackedVideo).where(TrackedVideo.enabled.is_(True))).scalars().all()
        for row in rows:
            result.setdefault(row.platform, []).append((row.video_id, row.label))
    return result


def _load_search_queries() -> list[dict]:
    """Danh sách từ khóa đang bật (enabled=True), mỗi từ khóa kèm max_videos/days riêng."""
    with SessionLocal() as session:
        rows = session.execute(select(SearchQuery).where(SearchQuery.enabled.is_(True))).scalars().all()
        return [
            {
                "query": row.query,
                "max_videos": row.max_videos,
                "days": row.published_within_days,
            }
            for row in rows
        ]


def run_forever() -> None:
    def job() -> None:
        platform_video_ids = _load_tracked_videos()
        search_queries = _load_search_queries()

        if not platform_video_ids and not search_queries:
            logger.warning(
                "Chưa có video ID hay từ khóa nào được cấu hình (qua UI) - bỏ qua lượt này"
            )
            return

        for platform, video_ids in platform_video_ids.items():
            logger.info("[%s] Bắt đầu thu thập định kỳ cho %d video", platform, len(video_ids))
            results = collect_many(platform, video_ids)
            logger.info("[%s] Kết quả: %s", platform, results)

        if search_queries:
            from collector.pipeline import discover_and_collect_youtube

            for sq in search_queries:
                logger.info("[youtube-search] Tìm video mới cho từ khóa '%s'", sq["query"])
                results = discover_and_collect_youtube(
                    sq["query"], max_videos=sq["max_videos"], published_within_days=sq["days"],
                )
                logger.info("[youtube-search] '%s' kết quả: %s", sq["query"], results)

    logger.info(
        "Scheduler khởi động - chu kỳ %d phút, đọc cấu hình từ DB mỗi lượt chạy",
        settings.collector_poll_interval_minutes,
    )
    job()  # chạy ngay 1 lần khi start, không đợi hết interval đầu tiên

    scheduler = BlockingScheduler()
    scheduler.add_job(job, "interval", minutes=settings.collector_poll_interval_minutes)
    scheduler.start()
