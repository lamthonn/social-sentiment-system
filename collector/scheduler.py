"""Lập lịch thu thập định kỳ bằng APScheduler.

Có 2 cách chạy:
1. CLI foreground (`python -m collector schedule` / `make collect-schedule`) - dùng
   `BlockingScheduler`, chạy độc lập trong terminal/tmux riêng (xem `run_forever`).
2. Tích hợp trong tiến trình API (`make api`) - dùng `BackgroundScheduler`, bật/tắt qua
   UI (tab "Cấu hình thu thập"), trạng thái bật/tắt lưu trong bảng `scheduler_state` nên
   không mất khi restart API (xem `init`/`set_enabled`/`status`).

⚠️ Không chạy đồng thời cả 2 cách cho cùng 1 bộ .env/DB - sẽ thu thập trùng lặp lãng phí
quota (dữ liệu không bị lỗi vì đã có chặn trùng theo post_id, chỉ là tốn quota vô ích).

Cả 2 cách đều đọc cấu hình TRỰC TIẾP TỪ DB mỗi lượt chạy (bảng `tracked_videos` +
`search_queries`, quản lý qua UI/API - xem api/main.py) - không phải từ .env. Vì vậy
thêm/sửa/xóa video theo dõi hay từ khóa search qua UI có hiệu lực ngay ở lượt chạy kế
tiếp, không cần restart.

⚠️ Quota YouTube: mỗi từ khóa trong search_queries tốn 100 unit/lượt chạy (bất kể
max_videos). VD interval mặc định 60 phút (24 lượt/ngày) x 1 từ khóa = 2.400 unit/ngày
cho riêng phần search, cộng thêm phần lấy comment (1 unit/video) - vẫn thoải mái trong
hạn mức free 10.000 unit/ngày. Thêm nhiều từ khóa hoặc rút ngắn interval thì tính lại.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from collector.pipeline import collect_many
from config.settings import settings
from storage.database import SessionLocal
from storage.models import SchedulerState, SearchQuery, TrackedVideo

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


def run_once() -> None:
    """Chạy 1 lượt thu thập ngay, đọc cấu hình (video theo dõi + từ khóa search) từ DB tại
    thời điểm gọi. Dùng chung cho cả CLI (`run_forever`) lẫn scheduler chạy trong API."""
    platform_video_ids = _load_tracked_videos()
    search_queries = _load_search_queries()

    if not platform_video_ids and not search_queries:
        logger.warning("Chưa có video ID hay từ khóa nào được cấu hình (qua UI) - bỏ qua lượt này")
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


def run_forever() -> None:
    """CLI foreground: chạy ngay 1 lần rồi lặp lại mỗi `COLLECTOR_POLL_INTERVAL_MINUTES` phút."""
    logger.info(
        "Scheduler khởi động - chu kỳ %d phút, đọc cấu hình từ DB mỗi lượt chạy",
        settings.collector_poll_interval_minutes,
    )
    run_once()  # chạy ngay 1 lần khi start, không đợi hết interval đầu tiên

    scheduler = BlockingScheduler()
    scheduler.add_job(run_once, "interval", minutes=settings.collector_poll_interval_minutes)
    scheduler.start()


# ===== Scheduler chạy nền trong tiến trình API - bật/tắt qua UI (xem api/main.py) =====

_JOB_ID = "auto_collect"
_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def _load_enabled_from_db() -> bool:
    with SessionLocal() as session:
        row = session.get(SchedulerState, 1)
        if row is None:
            row = SchedulerState(id=1, enabled=False)
            session.add(row)
            session.commit()
        return row.enabled


def _save_enabled_to_db(enabled: bool) -> None:
    with SessionLocal() as session:
        row = session.get(SchedulerState, 1)
        if row is None:
            session.add(SchedulerState(id=1, enabled=enabled))
        else:
            row.enabled = enabled
        session.commit()


def init() -> None:
    """Gọi 1 lần lúc API khởi động: tạo scheduler nền (ở trạng thái tạm dừng) và khôi phục
    đúng trạng thái bật/tắt đã lưu trong DB từ lần chạy trước."""
    with _lock:
        global _scheduler
        if _scheduler is not None:
            return
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            run_once, "interval", minutes=settings.collector_poll_interval_minutes, id=_JOB_ID,
        )
        _scheduler.start()
        _scheduler.pause_job(_JOB_ID)  # mặc định tạm dừng - bật lại ngay dưới đây nếu DB đang enabled

    if _load_enabled_from_db():
        set_enabled(True)


def shutdown() -> None:
    """Gọi lúc API tắt (tránh rò rỉ thread nền, đặc biệt khi `uvicorn --reload` tự khởi động lại)."""
    global _scheduler
    with _lock:
        if _scheduler is not None:
            _scheduler.shutdown(wait=False)
            _scheduler = None


def status() -> dict:
    assert _scheduler is not None, "Gọi init() trước khi dùng status()"
    job = _scheduler.get_job(_JOB_ID)
    enabled = job is not None and job.next_run_time is not None
    return {
        "enabled": enabled,
        "poll_interval_minutes": settings.collector_poll_interval_minutes,
        "next_run_at": job.next_run_time if enabled else None,
    }


def set_enabled(enabled: bool) -> dict:
    """Bật/tắt thu thập tự động ngay lập tức (lưu lại vào DB để nhớ qua lần restart API sau).
    Khi bật: chạy luôn 1 lượt ngay (không đợi hết interval đầu), giống hành vi `run_forever`."""
    assert _scheduler is not None, "Gọi init() trước khi dùng set_enabled()"
    with _lock:
        if enabled:
            _scheduler.resume_job(_JOB_ID)
            _scheduler.add_job(run_once, id=f"{_JOB_ID}_kick", next_run_time=datetime.now(), replace_existing=True)
        else:
            _scheduler.pause_job(_JOB_ID)
        _save_enabled_to_db(enabled)
    return status()
