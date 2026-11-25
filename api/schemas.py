"""Pydantic schema cho response của API (tách khỏi model ORM ở storage/models.py)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RawPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    post_id: str
    author_hash: str
    content: str
    category: str | None
    posted_at: datetime | None
    collected_at: datetime


class PostListResponse(BaseModel):
    items: list[RawPostOut]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    total_posts: int
    analyzed: int


class SearchQueryIn(BaseModel):
    platform: str = "youtube"
    query: str
    max_videos: int = 10
    published_within_days: int = 7
    enabled: bool = True


class SearchQueryOut(SearchQueryIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class TrackedVideoIn(BaseModel):
    platform: str
    video_id: str  # chấp nhận ID thuần hoặc URL đầy đủ - server tự trích ID
    label: str | None = None
    enabled: bool = True


class TrackedVideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    video_id: str
    label: str | None
    enabled: bool
    created_at: datetime


class TrackedChannelIn(BaseModel):
    channel_id: str  # chấp nhận UCxxxx, URL kênh hoặc @handle - server tự đổi sang UCxxxx
    label: str | None = None
    max_videos: int = 10
    enabled: bool = True


class TrackedChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    channel_id: str
    label: str | None
    max_videos: int
    enabled: bool
    created_at: datetime


class SchedulerStatusOut(BaseModel):
    enabled: bool
    poll_interval_minutes: int
    next_run_at: datetime | None


class SchedulerToggleIn(BaseModel):
    enabled: bool


# ===== Lâm: xem video đã thu thập và số liệu theo thời gian =====
class VideoOut(BaseModel):
    platform: str
    video_id: str
    title: str
    channel_title: str | None
    published_at: datetime | None
    view_count: int | None  # lần chụp số liệu gần nhất; None nếu chưa có hoặc nền tảng ẩn
    like_count: int | None
    comment_count: int | None
    captured_at: datetime | None
    collected_comments: int  # số bình luận đã lưu trong raw_posts


class VideoListResponse(BaseModel):
    items: list[VideoOut]
    total: int
    page: int
    page_size: int


class VideoSnapshotOut(BaseModel):
    captured_at: datetime
    view_count: int | None
    like_count: int | None
    comment_count: int | None


class VideoTopCommentOut(BaseModel):
    post_id: str
    text: str | None  # clean_text (đã che PII); None nếu bình luận chưa qua bước làm sạch
    like_count: int | None
    reply_count: int | None
    is_reply: bool


class VideoDetailOut(BaseModel):
    video: VideoOut
    description: str | None
    tags: list[str]
    snapshots: list[VideoSnapshotOut]
    top_comments: list[VideoTopCommentOut]
