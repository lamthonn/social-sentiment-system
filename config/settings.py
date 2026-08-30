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

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
