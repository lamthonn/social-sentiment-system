"""Cấu hình tập trung, đọc từ biến môi trường / file .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    postgres_user: str = "sss_user"
    postgres_password: str = "change_me"
    postgres_db: str = "sss_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Ẩn danh
    anonymization_salt: str = "change_this_to_a_long_random_secret"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Origin của frontend (React dev server) được phép gọi API - phân tách bởi dấu phẩy
    cors_origins: str = "http://localhost:5500"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Collector - credentials (Giai đoạn 2). Video ID theo dõi & từ khóa search được cấu
    # hình qua UI (bảng tracked_videos/search_queries - xem collector/scheduler.py), KHÔNG
    # còn nằm trong .env.
    youtube_api_key: str = ""
    collector_poll_interval_minutes: int = 60

    # TikTok (cần đăng ký & được duyệt Research API trước)
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
