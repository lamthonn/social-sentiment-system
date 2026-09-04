"""Định nghĩa bảng dữ liệu (ORM)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.database import Base


class RawPost(Base):
    """Một bài đăng/bình luận thu thập từ mạng xã hội (tác giả đã được ẩn danh)."""
    __tablename__ = "raw_posts"
    __table_args__ = (
        # Chặn thu thập trùng khi collector chạy lặp lại trên cùng 1 video/bài đăng.
        UniqueConstraint("platform", "post_id", name="uq_raw_posts_platform_post_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    post_id: Mapped[str] = mapped_column(String(128), index=True)
    author_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA-256, KHÔNG lưu ID gốc
    content: Mapped[str] = mapped_column(Text)
    # Từ khóa search hoặc ghi chú (label) của video theo dõi đã sinh ra bài này - dùng để
    # lọc/đánh giá model theo từng chủ đề sau này. NULL nếu thu thập thủ công không gắn chủ đề.
    category: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    results: Mapped[list["AnalysisResult"]] = relationship(back_populates="post")


class AnalysisResult(Base):
    """Kết quả phân tích cảm xúc của một bài đăng."""
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_post_id: Mapped[int] = mapped_column(ForeignKey("raw_posts.id"), index=True)
    sentiment_label: Mapped[str] = mapped_column(String(32))
    sentiment_score: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(64))
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post: Mapped["RawPost"] = relationship(back_populates="results")


class SearchQuery(Base):
    """Từ khóa để scheduler tự tìm video mới (thay cho sửa .env - cấu hình qua UI)."""
    __tablename__ = "search_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), default="youtube")
    query: Mapped[str] = mapped_column(String(255))
    max_videos: Mapped[int] = mapped_column(Integer, default=10)
    published_within_days: Mapped[int] = mapped_column(Integer, default=7)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrackedVideo(Base):
    """Video ID cố định cần theo dõi liên tục (thay cho YOUTUBE_VIDEO_IDS/TIKTOK_VIDEO_IDS trong .env)."""
    __tablename__ = "tracked_videos"
    __table_args__ = (
        UniqueConstraint("platform", "video_id", name="uq_tracked_videos_platform_video_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(50))
    video_id: Mapped[str] = mapped_column(String(128))
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # ghi chú tùy chọn (VD tên video)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
