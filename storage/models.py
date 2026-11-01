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
    """Kết quả phân tích của một bài đăng cho một bài toán (task).

    task = "sentiment" (quan điểm 3 lớp, BT-01) hoặc "emotion" (cảm xúc 7 nhãn, BT-03).
    Tên cột sentiment_label/sentiment_score giữ nguyên để tương thích; với task "emotion"
    đó là nhãn/độ tin cậy cảm xúc.
    """
    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint("raw_post_id", "task", "model_name", name="uq_analysis_post_task_model"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_post_id: Mapped[int] = mapped_column(ForeignKey("raw_posts.id"), index=True)
    task: Mapped[str] = mapped_column(String(32), default="sentiment", index=True)
    sentiment_label: Mapped[str] = mapped_column(String(32))
    sentiment_score: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(64))
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    post: Mapped["RawPost"] = relationship(back_populates="results")


class CleanPost(Base):
    """Bản đã làm sạch của một bài thu thập (bước PL-02). Không chứa định danh gốc; số điện
    thoại/email trong nội dung đã được che (pii_masked = số chỗ đã che)."""
    __tablename__ = "clean_posts"

    raw_post_id: Mapped[int] = mapped_column(ForeignKey("raw_posts.id"), primary_key=True)
    clean_text: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(8), index=True)
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    pii_masked: Mapped[int] = mapped_column(Integer, default=0)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)  # "#a,#b" trích từ nội dung gốc (T-22)
    pipeline_version: Mapped[str] = mapped_column(String(16))
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PipelineRun(Base):
    """Nhật ký từng lượt chạy một bước pipeline (bước PL-08 giám sát đọc từ đây)."""
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    step: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)  # running / success / failed / skipped
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    records_in: Mapped[int] = mapped_column(Integer, default=0)
    records_out: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON hoặc văn bản
    triggered_by: Mapped[str] = mapped_column(String(64), default="cli")


class ModelRun(Base):
    """Một lần huấn luyện + đánh giá (khớp khối R-xx trong PROJECT.md)."""
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_code: Mapped[str] = mapped_column(String(96), unique=True)
    task: Mapped[str] = mapped_column(String(32), index=True)  # sentiment / emotion
    model_key: Mapped[str] = mapped_column(String(32))  # tfidf-lr / tfidf-svm / visobert …
    model_name: Mapped[str] = mapped_column(String(128))
    dataset: Mapped[str] = mapped_column(String(64))
    dataset_version: Mapped[str] = mapped_column(String(64))
    params: Mapped[str] = mapped_column(Text)  # JSON
    accuracy: Mapped[float] = mapped_column(Float)
    f1_macro: Mapped[float] = mapped_column(Float)
    precision_macro: Mapped[float] = mapped_column(Float)
    recall_macro: Mapped[float] = mapped_column(Float)
    per_class: Mapped[str] = mapped_column(Text)  # JSON {nhãn: {precision, recall, f1, support}}
    confusion: Mapped[str] = mapped_column(Text)  # JSON {labels: [...], matrix: [[...]]}
    train_seconds: Mapped[float] = mapped_column(Float)
    artifact_path: Mapped[str] = mapped_column(String(255))
    selected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # "auto" = tự chọn theo F1-macro cao nhất (sẽ đổi khi có lần huấn luyện tốt hơn); tên người = chọn tay (giữ nguyên)
    selected_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Topic(Base):
    """Chủ đề tìm được ở một lượt phân tích xu hướng (BT-02) và phân loại xu hướng của nó (BT-04)."""
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trend_run_id: Mapped[int] = mapped_column(ForeignKey("pipeline_runs.id"), index=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    topic_index: Mapped[int] = mapped_column(Integer)
    keywords: Mapped[str] = mapped_column(Text)  # các từ khóa đại diện, phân tách bởi ", "
    size: Mapped[int] = mapped_column(Integer)
    trend_label: Mapped[str] = mapped_column(String(32))  # Mới nổi / Đang tăng / Đang giảm / Ổn định / Chưa đủ dữ liệu
    growth: Mapped[float] = mapped_column(Float)
    sentiment_shift: Mapped[str] = mapped_column(String(32))  # Tích cực hóa / Tiêu cực hóa / Ổn định / Chưa đủ dữ liệu
    positive_share: Mapped[float] = mapped_column(Float, default=0)
    negative_share: Mapped[float] = mapped_column(Float, default=0)
    neutral_share: Mapped[float] = mapped_column(Float, default=0)


class TopicDaily(Base):
    """Số bài theo ngày của một chủ đề (chuỗi thời gian độ quan tâm)."""
    __tablename__ = "topic_daily"

    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    day: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    negative: Mapped[int] = mapped_column(Integer, default=0)
    positive: Mapped[int] = mapped_column(Integer, default=0)


class User(Base):
    """Tài khoản webapp. Mật khẩu băm PBKDF2-SHA256 (security/auth.py), không lưu mật khẩu gốc."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))  # admin / analyst / viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Nhật ký truy cập/thao tác (NV-10 lưu vết): ai, làm gì, lúc nào, từ đâu."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)


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


class SchedulerState(Base):
    """Bật/tắt job thu thập tự động (bảng chỉ có 1 dòng, id=1) - đọc/ghi qua UI, có hiệu lực ngay
    (không cần restart), và được API tự đọc lại khi khởi động để khôi phục đúng trạng thái trước đó."""
    __tablename__ = "scheduler_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
