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
