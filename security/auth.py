"""Xác thực và phân quyền cho webapp (NV-10): băm mật khẩu, JWT, vai trò, chống dò mật khẩu, nhật ký."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt

from config.settings import settings
from storage.database import SessionLocal
from storage.models import AuditLog

logger = logging.getLogger(__name__)

ROLES = ("viewer", "analyst", "admin")  # quyền tăng dần
ROLE_LABELS = {"viewer": "Người xem", "analyst": "Phân tích viên", "admin": "Quản trị"}
_ITERATIONS = 240_000
_SECRET = settings.jwt_secret or secrets.token_urlsafe(32)
if not settings.jwt_secret:
    logger.warning("JWT_SECRET chưa đặt trong .env - dùng khóa tạm, mọi người phải đăng nhập lại khi API khởi động lại")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(iterations))
        return hmac.compare_digest(calc, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> None:
    if len(password) < 10 or password.isdigit() or password.isalpha():
        raise ValueError("Mật khẩu cần ít nhất 10 ký tự, gồm cả chữ và số")


def create_token(username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": username, "role": role, "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(payload, _SECRET, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def role_at_least(role: str, minimum: str) -> bool:
    return role in ROLES and ROLES.index(role) >= ROLES.index(minimum)


# ----- chống dò mật khẩu: tối đa 5 lần sai / 10 phút cho mỗi (IP, tên đăng nhập) -----
_FAILS: dict[tuple[str, str], deque] = defaultdict(deque)
MAX_FAILS, WINDOW = 5, 600


def login_blocked(ip: str, username: str) -> bool:
    q = _FAILS[(ip, username)]
    while q and q[0] < time.time() - WINDOW:
        q.popleft()
    return len(q) >= MAX_FAILS


def record_login_failure(ip: str, username: str) -> None:
    _FAILS[(ip, username)].append(time.time())


def reset_login_failures(ip: str, username: str) -> None:
    _FAILS.pop((ip, username), None)


def audit(username: str | None, action: str, detail: str | None = None, ip: str | None = None, success: bool = True) -> None:
    """Ghi một dòng nhật ký; lỗi ghi nhật ký không được làm hỏng request chính."""
    try:
        with SessionLocal() as s:
            s.add(AuditLog(username=username, action=action, detail=(detail or "")[:2000], ip=ip, success=success))
            s.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Không ghi được audit log")
