"""Kiểm thử collector YouTube: parse, thu thập tăng dần, trả lời, thông tin video.

Dùng SQLite trong bộ nhớ thay Postgres và client YouTube giả - không cần DB hay API key.
"""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from collector import pipeline, youtube_client
from storage.database import Base
from storage.models import RawPost, VideoMeta, VideoStatSnapshot


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(pipeline, "SessionLocal", factory)
    return factory


def _thread(cid: str, likes: int = 0, total_replies: int = 0, inline: int = 0) -> dict:
    comment = {
        "id": cid,
        "snippet": {
            "videoId": "vid1", "textDisplay": f"nội dung {cid}", "likeCount": likes,
            "authorChannelId": {"value": "UCauthor"}, "publishedAt": "2026-11-20T10:00:00Z",
        },
    }
    item = {"id": cid, "snippet": {"topLevelComment": comment, "totalReplyCount": total_replies}}
    if inline:
        item["replies"] = {"comments": [_reply(f"{cid}.r{i}", cid) for i in range(inline)]}
    return item


def _reply(rid: str, parent: str) -> dict:
    return {
        "id": rid,
        "snippet": {
            "videoId": "vid1", "parentId": parent, "textDisplay": f"trả lời {rid}", "likeCount": 1,
            "authorChannelId": {"value": "UCother"}, "publishedAt": "2026-11-20T11:00:00Z",
        },
    }


class FakeYouTube:
    """Giả lập commentThreads (nhiều trang) và comments.list, đếm số lần gọi."""

    def __init__(self, pages: list[list[dict]], replies: dict[str, list[dict]] | None = None):
        self.pages, self.replies = pages, replies or {}
        self.page_calls = 0
        self.reply_calls: list[str] = []

    def install(self, monkeypatch):
        monkeypatch.setattr(youtube_client, "fetch_comment_threads", self.fetch_comment_threads)
        monkeypatch.setattr(youtube_client, "iter_replies", self.iter_replies)

    def fetch_comment_threads(self, video_id, page_token=None, max_results=100):
        index = int(page_token or 0)
        self.page_calls += 1
        data = {"items": self.pages[index]}
        if index + 1 < len(self.pages):
            data["nextPageToken"] = str(index + 1)
        return data

    def iter_replies(self, parent_id):
        self.reply_calls.append(parent_id)
        yield from self.replies[parent_id]


def _posts(db) -> dict[str, RawPost]:
    with db() as session:
        return {p.post_id: p for p in session.execute(select(RawPost)).scalars()}


def test_parse_thread_and_reply():
    thread = pipeline._parse_youtube_comment(_thread("c1", likes=5, total_replies=2))
    assert (thread["post_id"], thread["like_count"], thread["reply_count"], thread["parent_id"]) == ("c1", 5, 2, None)
    assert thread["video_id"] == "vid1"

    reply = pipeline._parse_youtube_comment(_reply("c1.r0", "c1"))
    assert (reply["post_id"], reply["parent_id"], reply["reply_count"]) == ("c1.r0", "c1", None)


def test_parse_video_handles_hidden_stats():
    info = pipeline._parse_video({
        "id": "vid1",
        "snippet": {"title": "Tiêu đề", "channelId": "UCx", "categoryId": "25", "tags": ["giá vàng"],
                    "publishedAt": "2026-11-20T10:00:00Z"},
        "statistics": {"viewCount": "1200", "commentCount": "0"},  # likeCount bị ẩn
    })
    assert (info["view_count"], info["like_count"], info["comment_count"]) == (1200, None, 0)
    assert info["tags"] == '["giá vàng"]'


@pytest.mark.parametrize("value", [
    "UC" + "a" * 22,
    "https://www.youtube.com/channel/" + "UC" + "a" * 22,
])
def test_resolve_channel_id_without_api(value, monkeypatch):
    monkeypatch.setattr(youtube_client, "_get", lambda *a, **k: pytest.fail("không được gọi API"))
    assert youtube_client.resolve_channel_id(value) == "UC" + "a" * 22


@pytest.mark.parametrize("value", ["@vtv24", "https://www.youtube.com/@vtv24"])
def test_resolve_channel_id_from_handle(value, monkeypatch):
    calls = []

    def fake_get(path, params):
        calls.append((path, params))
        return {"items": [{"id": "UCresolved"}]}

    monkeypatch.setattr(youtube_client, "_get", fake_get)
    assert youtube_client.resolve_channel_id(value) == "UCresolved"
    assert calls == [("channels", {"part": "id", "forHandle": "@vtv24"})]


def test_resolve_channel_id_rejects_garbage():
    with pytest.raises(youtube_client.YouTubeAPIError):
        youtube_client.resolve_channel_id("khong-phai-kenh")


def test_collect_stores_context_fields_and_hashes_author(db, monkeypatch):
    FakeYouTube([[_thread("c1", likes=7, total_replies=1, inline=1)]]).install(monkeypatch)
    assert pipeline.collect_youtube_video_comments("vid1", category="giá vàng") == 2

    posts = _posts(db)
    assert (posts["c1"].video_id, posts["c1"].like_count, posts["c1"].reply_count) == ("vid1", 7, 1)
    assert (posts["c1.r0"].parent_id, posts["c1.r0"].reply_count) == ("c1", None)
    assert posts["c1"].category == "giá vàng"
    assert "UCauthor" not in posts["c1"].author_hash  # chỉ lưu bản băm


def test_incremental_stops_at_first_page_without_new_comments(db, monkeypatch):
    pages = [[_thread("c1")], [_thread("c2")], [_thread("c3")]]
    fake = FakeYouTube(pages)
    fake.install(monkeypatch)

    assert pipeline.collect_youtube_video_comments("vid1") == 3  # lần đầu: duyệt hết
    assert fake.page_calls == 3

    fake.page_calls = 0
    assert pipeline.collect_youtube_video_comments("vid1", incremental=True) == 0
    assert fake.page_calls == 1  # trang 1 đã biết hết -> dừng ngay, không duyệt tiếp trang 2, 3

    # chế độ thường vẫn duyệt hết
    fake.page_calls = 0
    pipeline.collect_youtube_video_comments("vid1")
    assert fake.page_calls == 3


def test_incremental_keeps_going_while_pages_have_new_comments(db, monkeypatch):
    fake = FakeYouTube([[_thread("c1")], [_thread("c2")]])
    fake.install(monkeypatch)
    pipeline.collect_youtube_video_comments("vid1")

    fake.pages = [[_thread("new1")], [_thread("c1")], [_thread("c2")]]
    fake.page_calls = 0
    assert pipeline.collect_youtube_video_comments("vid1", incremental=True) == 1
    assert fake.page_calls == 2  # trang 1 có bình luận mới, trang 2 toàn bình luận cũ -> dừng


def test_replies_fetched_only_when_count_grows(db, monkeypatch):
    all_replies = [_reply(f"c1.r{i}", "c1") for i in range(7)]
    fake = FakeYouTube([[_thread("c1", total_replies=7, inline=5)]], replies={"c1": all_replies})
    fake.install(monkeypatch)

    assert pipeline.collect_youtube_video_comments("vid1") == 8  # 1 gốc + 7 trả lời (5 inline trùng, không tính 2 lần)
    assert fake.reply_calls == ["c1"]

    pipeline.collect_youtube_video_comments("vid1")
    assert fake.reply_calls == ["c1"]  # số trả lời không đổi -> không gọi lại comments.list

    fake.pages = [[_thread("c1", total_replies=8, inline=5)]]
    fake.replies["c1"] = all_replies + [_reply("c1.r7", "c1")]
    assert pipeline.collect_youtube_video_comments("vid1") == 1
    assert fake.reply_calls == ["c1", "c1"]


def test_replies_skipped_when_disabled(db, monkeypatch):
    monkeypatch.setattr(pipeline.settings, "collector_fetch_replies", False)
    fake = FakeYouTube([[_thread("c1", total_replies=7, inline=5)]], replies={"c1": []})
    fake.install(monkeypatch)
    assert pipeline.collect_youtube_video_comments("vid1") == 6  # chỉ gốc + 5 trả lời inline
    assert fake.reply_calls == []


def test_existing_comment_gets_updated_like_count(db, monkeypatch):
    fake = FakeYouTube([[_thread("c1", likes=1)]])
    fake.install(monkeypatch)
    pipeline.collect_youtube_video_comments("vid1")

    fake.pages = [[_thread("c1", likes=42)]]
    assert pipeline.collect_youtube_video_comments("vid1") == 0
    assert _posts(db)["c1"].like_count == 42


def test_save_video_items_upserts_meta_and_appends_snapshots(db):
    item = {
        "id": "vid1",
        "snippet": {"title": "v1", "channelId": "UCx", "publishedAt": "2026-11-20T10:00:00Z"},
        "statistics": {"viewCount": "100", "likeCount": "10", "commentCount": "5"},
    }
    pipeline._save_video_items([item])
    item2 = {**item, "snippet": {**item["snippet"], "title": "v2"}, "statistics": {"viewCount": "250"}}
    pipeline._save_video_items([item2])

    with db() as session:
        metas = session.execute(select(VideoMeta)).scalars().all()
        snaps = session.execute(select(VideoStatSnapshot).order_by(VideoStatSnapshot.id)).scalars().all()
    assert [m.title for m in metas] == ["v2"]  # 1 dòng/video, được cập nhật
    assert [(s.view_count, s.like_count) for s in snaps] == [(100, 10), (250, None)]  # mỗi lượt 1 snapshot


def test_collect_video_items_skips_videos_without_comments(db, monkeypatch):
    fake = FakeYouTube([[_thread("c1")]])
    fake.install(monkeypatch)
    items = [
        {"id": "vid1", "snippet": {"title": "có bình luận"}, "statistics": {"commentCount": "1"}},
        {"id": "vid0", "snippet": {"title": "không có"}, "statistics": {"commentCount": "0"}},
    ]
    results = pipeline._collect_video_items(items, "chủ đề", None, True)
    assert results == {"vid1": {"title": "có bình luận", "inserted": 1}, "vid0": {"title": "không có", "inserted": 0}}
    assert fake.page_calls == 1
