"""Middleware bảo vệ toàn bộ API: xác thực JWT, phân quyền theo vai trò, ghi nhật ký truy cập.

An toàn mặc định: route không khớp quy tắc nào -> chỉ admin. Thêm endpoint mới thì khai báo quyền ở RULES.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from security.auth import audit, decode_token, role_at_least, token_expired_only
from storage.database import SessionLocal
from storage.models import User

# (phương thức, đường dẫn regex, vai trò tối thiểu; None = công khai)
RULES: list[tuple[str, re.Pattern, str | None]] = [(m, re.compile(p), r) for m, p, r in [
    ("GET", r"^/health$", None),
    ("POST", r"^/auth/login$", None),
    ("GET", r"^/(docs|redoc|openapi\.json)$", None),
    ("GET", r"^/auth/me$", "viewer"),
    ("POST", r"^/auth/change-password$", "viewer"),
    ("GET", r"^/(stats|dashboard/.*|topics.*|models/runs.*|experiments)$", "viewer"),
    ("GET", r"^/(posts.*|analysis/.*|search-queries|tracked-videos|scheduler|pipeline/runs.*)$", "analyst"),
    ("POST|PUT|DELETE", r"^/(search-queries.*|tracked-videos.*|scheduler/toggle)$", "analyst"),
    ("POST", r"^/pipeline/run$", "analyst"),  # bước datasets/train kiểm tra admin trong handler
    ("GET|POST|PUT|DELETE", r"^/(users.*|audit.*|models/.+/select)$", "admin"),
]]
# xem dữ liệu chi tiết cũng được ghi nhật ký (lưu vết truy cập dữ liệu)
AUDITED_GET = re.compile(r"^/(posts|analysis/posts|audit|users)")


def required_role(method: str, path: str) -> tuple[bool, str | None]:
    for methods, pattern, role in RULES:
        if method in methods.split("|") and pattern.match(path):
            return True, role
    return False, "admin"


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


# ----- giới hạn tần suất (cửa sổ trượt 60 giây, theo IP) -----
RATE_LIMITS = [(re.compile(r"^/pipeline/run$"), 10), (re.compile(r"^/auth/login$"), 30), (re.compile(r".*"), 600)]
_hits: dict[tuple[str, str], deque] = defaultdict(deque)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def rate_limited(ip: str, path: str) -> bool:
    pattern, limit = next((p, n) for p, n in RATE_LIMITS if p.match(path))
    q = _hits[(ip, pattern.pattern)]
    now = time.time()
    while q and q[0] < now - 60:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def _with_headers(response):
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":  # CORS preflight
            return await call_next(request)
        path = request.url.path
        if rate_limited(client_ip(request), path):
            audit(None, "rate-limit", f"{request.method} {path}", client_ip(request), success=False)
            return _with_headers(JSONResponse({"detail": "Quá nhiều yêu cầu - thử lại sau ít phút"}, status_code=429))
        _, role_needed = required_role(request.method, path)
        request.state.user = None
        if role_needed is not None:
            header = request.headers.get("authorization", "")
            claims = decode_token(header[7:]) if header.lower().startswith("bearer ") else None
            if not claims:
                if header:  # có gửi token nhưng không dùng được -> ghi lại; chỉ token sai chữ ký được tính là token giả (security/detect.py)
                    action = "expired-token" if token_expired_only(header[7:]) else "invalid-token"
                    audit(None, action, f"{request.method} {path}", client_ip(request), success=False)
                return _with_headers(JSONResponse({"detail": "Chưa đăng nhập hoặc phiên đã hết hạn"}, status_code=401))
            with SessionLocal() as s:  # đọc lại từ DB để tài khoản bị khóa/đổi quyền có hiệu lực ngay
                user = s.scalars(select(User).where(User.username == claims["sub"])).first()
            if not user or not user.is_active:
                return _with_headers(JSONResponse({"detail": "Tài khoản không tồn tại hoặc đã bị khóa"}, status_code=401))
            if not role_at_least(user.role, role_needed):
                audit(user.username, "forbidden", f"{request.method} {path}", client_ip(request), success=False)
                return _with_headers(JSONResponse({"detail": "Bạn không có quyền thực hiện thao tác này"}, status_code=403))
            request.state.user = {"username": user.username, "role": user.role}
        response = await call_next(request)
        u = request.state.user
        if u and (request.method != "GET" or AUDITED_GET.match(path)) and not path.startswith("/auth/"):
            detail = f"{request.method} {path}" + (f"?{request.url.query}" if request.url.query else "")
            audit(u["username"], f"{request.method.lower()} {path.split('/')[1]}", detail, client_ip(request), response.status_code < 400)
        return _with_headers(response)
