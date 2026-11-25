"""Kiểm thử nạp cấu hình thu thập mặc định."""
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from storage import seed
from storage.database import Base
from storage.models import SearchQuery, TrackedChannel


@pytest.fixture()
def factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_seed_file_is_valid_and_loads_into_empty_db(factory):
    added = seed.seed_collector(factory)
    assert added["search_queries"] >= 1 and added["tracked_channels"] >= 1
    with factory() as s:
        channels = s.execute(select(TrackedChannel)).scalars().all()
        assert all(c.channel_id.startswith("UC") for c in channels)
        assert any(not c.enabled for c in channels)  # kênh tắt bình luận được nạp ở trạng thái tắt
        assert len(s.execute(select(SearchQuery)).scalars().all()) == added["search_queries"]


def test_seed_does_not_touch_non_empty_tables(factory, tmp_path):
    with factory() as s:
        s.add(SearchQuery(platform="youtube", query="của tôi", max_videos=3, published_within_days=1))
        s.commit()
    path = tmp_path / "seed.json"
    path.write_text(json.dumps({"search_queries": [{"query": "khác"}], "tracked_channels": [{"channel_id": "UCx"}]}), encoding="utf-8")

    assert seed.seed_collector(factory, path) == {"search_queries": 0, "tracked_channels": 1}  # bảng từ khóa đã có -> giữ nguyên
    with factory() as s:
        assert [q.query for q in s.execute(select(SearchQuery)).scalars()] == ["của tôi"]
    assert seed.seed_collector(factory, path) == {"search_queries": 0, "tracked_channels": 0}  # chạy lại không nhân đôi
