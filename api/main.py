"""Khung FastAPI (Giai đoạn 0)."""
from fastapi import FastAPI

app = FastAPI(title="Social Sentiment System API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict:
    """Placeholder - sẽ trả thống kê cảm xúc/xu hướng ở giai đoạn sau."""
    return {"total_posts": 0, "analyzed": 0}
