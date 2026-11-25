"""Kiểm thử endpoint xem video: danh sách (số liệu mới nhất, tìm, sắp xếp) và chi tiết."""
from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import main
from storage.database import Base
from storage.models import CleanPost, RawPost, VideoMeta, VideoStatSnapshot


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as s:
        yield s


def _video(s, vid, title, channel, views_series, published="2026-11-20"):
    s.add(VideoMeta(platform="youtube", video_id=vid, title=title, channel_title=channel, tags='["a", "b"]',
                    published_at=datetime.fromisoformat(published)))
    for i, v in enumerate(views_series):
        s.add(VideoStatSnapshot(platform="youtube", video_id=vid, captured_at=datetime(2026, 11, 24, i),
                                view_count=v, like_count=v // 10, comment_count=3))


def _comment(s, vid, post_id, likes, parent=None, clean=None):
    raw = RawPost(platform="youtube", post_id=post_id, author_hash="h", content="bí mật", video_id=vid,
                  like_count=likes, parent_id=parent)
    s.add(raw)
    s.flush()
    if clean:
        s.add(CleanPost(raw_post_id=raw.id, clean_text=clean, lang="vi", pipeline_version="t"))


def test_list_uses_latest_snapshot_and_sorts_by_views(session):
    _video(session, "v1", "Giá vàng hôm nay", "Kênh A", [100, 500])  # snapshot mới nhất = 500
    _video(session, "v2", "Bóng đá", "Kênh B", [900])
    _video(session, "v3", "Chưa có số liệu", "Kênh B", [])
    _comment(session, "v1", "c1", 1)
    session.commit()

    res = main.list_videos(page=1, page_size=20, q=None, sort="views", session=session)
    assert [v.video_id for v in res.items] == ["v2", "v1", "v3"]  # video chưa có số liệu xếp cuối
    v1 = res.items[1]
    assert (v1.view_count, v1.like_count, v1.collected_comments) == (500, 50, 1)
    assert res.items[2].view_count is None and res.total == 3


def test_list_search_matches_title_or_channel(session):
    _video(session, "v1", "Giá vàng hôm nay", "Kênh A", [1])
    _video(session, "v2", "Bóng đá", "Kênh Vàng", [1])
    _video(session, "v3", "Khác", "Kênh C", [1])
    session.commit()
    res = main.list_videos(page=1, page_size=20, q="vàng", sort="views", session=session)
    assert sorted(v.video_id for v in res.items) == ["v1", "v2"] and res.total == 2


def test_detail_returns_series_and_top_comments_without_raw_content(session):
    _video(session, "v1", "T", "K", [10, 20, 30])
    _comment(session, "v1", "c1", 5, clean="bình luận ít like")
    _comment(session, "v1", "c2", 50, clean="bình luận nhiều like")
    _comment(session, "v1", "c2.r1", 9, parent="c2")  # chưa làm sạch
    session.commit()

    d = main.get_video("v1", session=session)
    assert [s.view_count for s in d.snapshots] == [10, 20, 30]
    assert d.tags == ["a", "b"] and d.video.collected_comments == 3
    assert [(c.post_id, c.text, c.is_reply) for c in d.top_comments] == [
        ("c2", "bình luận nhiều like", False), ("c2.r1", None, True), ("c1", "bình luận ít like", False),
    ]
    assert "bí mật" not in d.model_dump_json()  # nội dung gốc không ra API


def test_detail_unknown_video_is_404(session):
    with pytest.raises(HTTPException) as exc:
        main.get_video("nope", session=session)
    assert exc.value.status_code == 404
