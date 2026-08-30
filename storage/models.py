"""Định nghĩa bảng dữ liệu (ORM)."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.database import Base


class RawPost(Base):
    """Một bài đăng/bình luận thu thập từ mạng xã hội (tác giả đã được ẩn danh)."""
    __tablename__ = "raw_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    post_id: Mapped[str] = mapped_column(String(128), index=True)
    author_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA-256, KHÔNG lưu ID gốc
    content: Mapped[str] = mapped_column(Text)
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
