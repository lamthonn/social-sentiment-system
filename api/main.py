"""Khung FastAPI (Giai đoạn 0)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings

app = FastAPI(title="Social Sentiment System API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict:
    """Placeholder - sẽ trả thống kê cảm xúc/xu hướng ở giai đoạn sau."""
    return {"total_posts": 0, "analyzed": 0}
