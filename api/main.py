"""Khung FastAPI (Giai đoạn 0) + endpoint đọc dữ liệu thô (Giai đoạn 2) + cấu hình collector."""
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas import (
    PostListResponse,
    RawPostOut,
    SearchQueryIn,
    SearchQueryOut,
    StatsResponse,
    TrackedVideoIn,
    TrackedVideoOut,
)
from config.settings import settings
from storage.database import get_session
from storage.models import AnalysisResult, RawPost, SearchQuery, TrackedVideo

app = FastAPI(title="Social Sentiment System API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalize_video_id(platform: str, value: str) -> str:
    """Chấp nhận ID thuần hoặc URL đầy đủ - dùng đúng logic trích ID của từng nền tảng."""
    if platform == "youtube":
        from collector.youtube_client import extract_video_id as extractor
    elif platform == "tiktok":
        from collector.tiktok_client import extract_video_id as extractor
    else:
        return value.strip()
    return extractor(value)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stats", response_model=StatsResponse)
def stats(session: Session = Depends(get_session)) -> StatsResponse:
    total_posts = session.scalar(select(func.count()).select_from(RawPost)) or 0
    analyzed = session.scalar(select(func.count()).select_from(AnalysisResult)) or 0
    return StatsResponse(total_posts=total_posts, analyzed=analyzed)


@app.get("/posts", response_model=PostListResponse)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: str | None = None,
    category: str | None = None,
    session: Session = Depends(get_session),
) -> PostListResponse:
    """Danh sách bài đăng/comment đã thu thập, mới nhất trước, có phân trang."""
    query = select(RawPost)
    count_query = select(func.count()).select_from(RawPost)
    if platform:
        query = query.where(RawPost.platform == platform)
        count_query = count_query.where(RawPost.platform == platform)
    if category:
        query = query.where(RawPost.category == category)
        count_query = count_query.where(RawPost.category == category)

    total = session.scalar(count_query) or 0
    items = (
        session.execute(
            query.order_by(RawPost.collected_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return PostListResponse(
        items=[RawPostOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/posts/categories", response_model=list[str])
def list_post_categories(session: Session = Depends(get_session)) -> list[str]:
    """Danh sách category khác nhau đang có trong raw_posts (để FE làm dropdown lọc)."""
    rows = session.execute(
        select(RawPost.category).where(RawPost.category.is_not(None)).distinct().order_by(RawPost.category)
    ).scalars().all()
    return list(rows)


# ===== Cấu hình collector (thay cho sửa .env - scheduler đọc trực tiếp từ DB, có hiệu lực ngay) =====


@app.get("/search-queries", response_model=list[SearchQueryOut])
def list_search_queries(session: Session = Depends(get_session)):
    return session.execute(select(SearchQuery).order_by(SearchQuery.id)).scalars().all()


@app.post("/search-queries", response_model=SearchQueryOut, status_code=201)
def create_search_query(payload: SearchQueryIn, session: Session = Depends(get_session)):
    row = SearchQuery(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@app.put("/search-queries/{query_id}", response_model=SearchQueryOut)
def update_search_query(query_id: int, payload: SearchQueryIn, session: Session = Depends(get_session)):
    row = session.get(SearchQuery, query_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy từ khóa")
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    session.commit()
    session.refresh(row)
    return row


@app.delete("/search-queries/{query_id}", status_code=204)
def delete_search_query(query_id: int, session: Session = Depends(get_session)):
    row = session.get(SearchQuery, query_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy từ khóa")
    session.delete(row)
    session.commit()


@app.get("/tracked-videos", response_model=list[TrackedVideoOut])
def list_tracked_videos(session: Session = Depends(get_session)):
    return session.execute(select(TrackedVideo).order_by(TrackedVideo.id)).scalars().all()


@app.post("/tracked-videos", response_model=TrackedVideoOut, status_code=201)
def create_tracked_video(payload: TrackedVideoIn, session: Session = Depends(get_session)):
    video_id = _normalize_video_id(payload.platform, payload.video_id)

    existing = session.execute(
        select(TrackedVideo).where(TrackedVideo.platform == payload.platform, TrackedVideo.video_id == video_id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Video này đã được theo dõi")

    row = TrackedVideo(platform=payload.platform, video_id=video_id, label=payload.label, enabled=payload.enabled)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@app.put("/tracked-videos/{tracked_video_id}", response_model=TrackedVideoOut)
def update_tracked_video(tracked_video_id: int, payload: TrackedVideoIn, session: Session = Depends(get_session)):
    row = session.get(TrackedVideo, tracked_video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")

    row.platform = payload.platform
    row.video_id = _normalize_video_id(payload.platform, payload.video_id)
    row.label = payload.label
    row.enabled = payload.enabled
    session.commit()
    session.refresh(row)
    return row


@app.delete("/tracked-videos/{tracked_video_id}", status_code=204)
def delete_tracked_video(tracked_video_id: int, session: Session = Depends(get_session)):
    row = session.get(TrackedVideo, tracked_video_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    session.delete(row)
    session.commit()
