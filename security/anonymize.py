"""Ẩn danh định danh người dùng ngay tại khâu thu thập."""
import hashlib

from config.settings import settings


def hash_identifier(raw_value: str, salt: str | None = None) -> str:
    """Băm định danh người dùng bằng SHA-256 + salt.

    Gọi hàm này NGAY khi thu thập, trước khi ghi vào CSDL, để hệ thống
    không bao giờ lưu định danh gốc (phù hợp Luật số 91/2025/QH15).
    """
    salt = salt if salt is not None else settings.anonymization_salt
    return hashlib.sha256(f"{salt}:{raw_value}".encode("utf-8")).hexdigest()
