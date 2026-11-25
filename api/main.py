"""Khung FastAPI (Giai đoạn 0) + endpoint đọc dữ liệu thô (Giai đoạn 2) + cấu hình collector."""
import json

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from api.schemas import (
    PostListResponse,
    RawPostOut,
    SchedulerStatusOut,
    SchedulerToggleIn,
    SearchQueryIn,
    SearchQueryOut,
    StatsResponse,
    TrackedChannelIn,
    TrackedChannelOut,
    TrackedVideoIn,
    TrackedVideoOut,
    VideoDetailOut,
    VideoListResponse,
    VideoOut,
    VideoSnapshotOut,
    VideoTopCommentOut,
)
from api.app_routes import router as app_router
from api.security_mw import AuthMiddleware
from collector import scheduler as job_scheduler
from config.settings import settings
from storage.database import get_session
from storage.models import (
    AnalysisResult,
    CleanPost,
    RawPost,
    SearchQuery,
    TrackedChannel,
    TrackedVideo,
    VideoMeta,
    VideoStatSnapshot,
)

app = FastAPI(title="Social Sentiment System API", version="0.2.0")

# Thứ tự: CORS thêm sau nên bọc ngoài cùng -> phản hồi 401/403 của AuthMiddleware vẫn có header CORS.
# AuthMiddleware: mọi route cần đăng nhập + đúng vai trò, trừ các route công khai khai báo ở api/security_mw.py
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(app_router)


@app.on_event("startup")
def _start_scheduler() -> None:
    """Khôi phục trạng thái bật/tắt thu thập tự động đã lưu trong DB từ lần chạy trước."""
    job_scheduler.init()


@app.on_event("shutdown")
def _stop_scheduler() -> None:
    job_scheduler.shutdown()


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
    # đếm số bài đã có nhãn quan điểm (không đếm trùng khi cùng bài có kết quả của nhiều task/mô hình)
    analyzed = session.scalar(
        select(func.count(func.distinct(AnalysisResult.raw_post_id))).where(AnalysisResult.task == "sentiment")
    ) or 0
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


# ===== Bật/tắt job thu thập tự động (scheduler chạy nền trong tiến trình API - xem collector/scheduler.py) =====


@app.get("/scheduler", response_model=SchedulerStatusOut)
def scheduler_status() -> SchedulerStatusOut:
    return SchedulerStatusOut(**job_scheduler.status())


@app.post("/scheduler/toggle", response_model=SchedulerStatusOut)
def scheduler_toggle(payload: SchedulerToggleIn) -> SchedulerStatusOut:
    return SchedulerStatusOut(**job_scheduler.set_enabled(payload.enabled))


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


def _resolve_channel_id(value: str) -> str:
    """UCxxxx / URL kênh / @handle -> UCxxxx. Lỗi tra cứu (handle sai, hết quota...) trả về 400."""
    from collector.youtube_client import YouTubeAPIError, resolve_channel_id

    try:
        return resolve_channel_id(value)
    except YouTubeAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/tracked-channels", response_model=list[TrackedChannelOut])
def list_tracked_channels(session: Session = Depends(get_session)):
    return session.execute(select(TrackedChannel).order_by(TrackedChannel.id)).scalars().all()


@app.post("/tracked-channels", response_model=TrackedChannelOut, status_code=201)
def create_tracked_channel(payload: TrackedChannelIn, session: Session = Depends(get_session)):
    channel_id = _resolve_channel_id(payload.channel_id)
    if session.execute(select(TrackedChannel).where(TrackedChannel.channel_id == channel_id)).first():
        raise HTTPException(status_code=409, detail="Kênh này đã được theo dõi")

    row = TrackedChannel(
        channel_id=channel_id, label=payload.label, max_videos=payload.max_videos, enabled=payload.enabled,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@app.put("/tracked-channels/{tracked_channel_id}", response_model=TrackedChannelOut)
def update_tracked_channel(tracked_channel_id: int, payload: TrackedChannelIn, session: Session = Depends(get_session)):
    row = session.get(TrackedChannel, tracked_channel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy kênh")

    # chỉ tra lại khi người dùng đổi ô kênh (tránh tốn quota khi chỉ bật/tắt hay sửa ghi chú)
    if payload.channel_id.strip() != row.channel_id:
        row.channel_id = _resolve_channel_id(payload.channel_id)
    row.label = payload.label
    row.max_videos = payload.max_videos
    row.enabled = payload.enabled
    session.commit()
    session.refresh(row)
    return row


@app.delete("/tracked-channels/{tracked_channel_id}", status_code=204)
def delete_tracked_channel(tracked_channel_id: int, session: Session = Depends(get_session)):
    row = session.get(TrackedChannel, tracked_channel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy kênh")
    session.delete(row)
    session.commit()


# ===== Lâm: xem video đã thu thập (thông tin + số liệu theo thời gian) =====
_VIDEO_SORTS = {
    "views": VideoStatSnapshot.view_count,
    "likes": VideoStatSnapshot.like_count,
    "comments": VideoStatSnapshot.comment_count,
    "published": VideoMeta.published_at,
}


def _video_out(meta: VideoMeta, snap: VideoStatSnapshot | None, collected: int) -> VideoOut:
    return VideoOut(
        platform=meta.platform, video_id=meta.video_id, title=meta.title, channel_title=meta.channel_title,
        published_at=meta.published_at,
        view_count=snap.view_count if snap else None,
        like_count=snap.like_count if snap else None,
        comment_count=snap.comment_count if snap else None,
        captured_at=snap.captured_at if snap else None,
        collected_comments=collected,
    )


@app.get("/videos", response_model=VideoListResponse)
def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    sort: str = Query("views", pattern="^(views|likes|comments|published)$"),
    session: Session = Depends(get_session),
) -> VideoListResponse:
    """Video đã thu thập kèm số liệu của lần chụp gần nhất; q tìm theo tiêu đề hoặc tên kênh."""
    latest_snap_id = select(func.max(VideoStatSnapshot.id)).group_by(VideoStatSnapshot.platform, VideoStatSnapshot.video_id)
    collected = (
        select(RawPost.platform, RawPost.video_id, func.count().label("n"))
        .where(RawPost.video_id.is_not(None)).group_by(RawPost.platform, RawPost.video_id).subquery()
    )
    query = (
        select(VideoMeta, VideoStatSnapshot, func.coalesce(collected.c.n, 0))
        .outerjoin(VideoStatSnapshot, and_(
            VideoStatSnapshot.platform == VideoMeta.platform,
            VideoStatSnapshot.video_id == VideoMeta.video_id,
            VideoStatSnapshot.id.in_(latest_snap_id),
        ))
        .outerjoin(collected, and_(collected.c.platform == VideoMeta.platform, collected.c.video_id == VideoMeta.video_id))
    )
    count_query = select(func.count()).select_from(VideoMeta)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        match = or_(VideoMeta.title.ilike(pattern), VideoMeta.channel_title.ilike(pattern))
        query, count_query = query.where(match), count_query.where(match)

    total = session.scalar(count_query) or 0
    rows = session.execute(
        query.order_by(_VIDEO_SORTS[sort].desc().nulls_last(), VideoMeta.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return VideoListResponse(
        items=[_video_out(meta, snap, n) for meta, snap, n in rows], total=total, page=page, page_size=page_size,
    )


@app.get("/videos/{video_id}", response_model=VideoDetailOut)
def get_video(video_id: str, session: Session = Depends(get_session)) -> VideoDetailOut:
    """Chi tiết 1 video: mô tả, chuỗi số liệu theo thời gian, bình luận nhiều like nhất (chỉ clean_text)."""
    meta = session.execute(select(VideoMeta).where(VideoMeta.video_id == video_id)).scalars().first()
    if meta is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")

    snaps = session.execute(
        select(VideoStatSnapshot)
        .where(VideoStatSnapshot.platform == meta.platform, VideoStatSnapshot.video_id == video_id)
        .order_by(VideoStatSnapshot.captured_at)
    ).scalars().all()
    collected = session.scalar(
        select(func.count()).select_from(RawPost).where(RawPost.platform == meta.platform, RawPost.video_id == video_id)
    ) or 0
    top = session.execute(
        select(RawPost, CleanPost.clean_text)
        .outerjoin(CleanPost, CleanPost.raw_post_id == RawPost.id)
        .where(RawPost.platform == meta.platform, RawPost.video_id == video_id)
        .order_by(RawPost.like_count.desc().nulls_last(), RawPost.id)
        .limit(10)
    ).all()
    try:
        tags = json.loads(meta.tags) if meta.tags else []
    except ValueError:
        tags = []
    return VideoDetailOut(
        video=_video_out(meta, snaps[-1] if snaps else None, collected),
        description=meta.description,
        tags=tags,
        snapshots=[VideoSnapshotOut(
            captured_at=s.captured_at, view_count=s.view_count, like_count=s.like_count, comment_count=s.comment_count,
        ) for s in snaps],
        top_comments=[VideoTopCommentOut(
            post_id=p.post_id, text=text, like_count=p.like_count, reply_count=p.reply_count, is_reply=p.parent_id is not None,
        ) for p, text in top],
    )
