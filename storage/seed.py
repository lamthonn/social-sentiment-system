"""Nạp cấu hình thu thập mặc định (từ khóa, kênh theo dõi) vào DB mới.

Dữ liệu nằm ở config/collector_seed.json. Chỉ nạp vào bảng đang TRỐNG: máy đã có cấu hình
(hoặc đã xóa hết có chủ ý ở một bảng khác) không bị ghi đè. Chạy tự động trong storage.migrate.
"""
import json
from pathlib import Path

from sqlalchemy import func, select

from storage.database import SessionLocal
from storage.models import SearchQuery, TrackedChannel

SEED_FILE = Path(__file__).resolve().parent.parent / "config" / "collector_seed.json"


def seed_collector(session_factory=SessionLocal, path: Path = SEED_FILE) -> dict[str, int]:
    """Trả về số dòng đã thêm cho từng bảng."""
    data = json.loads(path.read_text(encoding="utf-8"))
    added = {"search_queries": 0, "tracked_channels": 0}
    with session_factory() as session:
        if not session.scalar(select(func.count()).select_from(SearchQuery)):
            for row in data.get("search_queries", []):
                session.add(SearchQuery(platform="youtube", **row))
                added["search_queries"] += 1
        if not session.scalar(select(func.count()).select_from(TrackedChannel)):
            for row in data.get("tracked_channels", []):
                session.add(TrackedChannel(platform="youtube", **row))
                added["tracked_channels"] += 1
        session.commit()
    return added
