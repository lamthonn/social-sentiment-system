"""T-35 (CH4): phát hiện hành vi bất thường từ nhật ký truy cập (audit_logs) bằng luật cửa sổ trượt.

Chuỗi xử lý của đề tài: phát hiện -> bảo vệ (middleware: khóa đăng nhập, 403, 429) -> ghi nhật ký -> cảnh báo (hàm này).
Hàm detect() là hàm thuần trên danh sách bản ghi, nên dùng được cho cả dữ liệu thật (pipeline monitor)
lẫn dữ liệu mô phỏng (experiments/security_eval.py).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

WINDOW = timedelta(minutes=10)
LONG_WINDOW = timedelta(hours=24)  # bắt tấn công dàn trải, cố ý đi chậm dưới ngưỡng 10 phút
# ngưỡng: số sự kiện trong một cửa sổ WINDOW
BRUTE_FORCE = 5         # đăng nhập sai cùng IP + cùng tài khoản
SPRAY_USERS = 5         # số tài khoản khác nhau đăng nhập sai từ cùng IP
FORBIDDEN = 5           # lần bị từ chối quyền (403) của cùng tài khoản
BAD_TOKEN = 10          # token giả/hết hạn từ cùng IP
MASS_ACCESS = 100       # lần xem dữ liệu chi tiết (/posts, /analysis/posts) của cùng tài khoản;
                        # chọn theo bảng quét ngưỡng của experiments/security_eval.py - hiệu chỉnh lại khi có nhật ký thật
BRUTE_FORCE_LONG = 20  # đăng nhập sai cùng IP + tài khoản trong 24 giờ
MASS_ACCESS_LONG = 300  # lần xem dữ liệu chi tiết của cùng tài khoản trong 24 giờ
DATA_PATHS = ("GET /posts", "GET /analysis/posts")
ALERT_PREFIX = "An ninh: "  # cảnh báo an ninh trong kết quả monitor - API chỉ cho admin xem chi tiết


@dataclass
class Event:
    at: datetime
    username: str | None
    action: str
    detail: str
    ip: str
    success: bool


@dataclass
class Alert:
    kind: str
    key: str           # IP hoặc tài khoản bị nghi
    first_at: datetime  # đầu cửa sổ có hành vi bất thường
    fired_at: datetime  # lúc đủ ngưỡng, tức lúc cảnh báo được bật
    count: int         # số sự kiện trong cửa sổ
    message: str


KINDS = {
    "brute-force": "Dò mật khẩu một tài khoản",
    "password-spray": "Thử mật khẩu trên nhiều tài khoản",
    "privilege-probe": "Dò quyền (gọi chức năng không được phép)",
    "token-forgery": "Token giả (sai chữ ký) lặp lại",
    "mass-access": "Truy xuất dữ liệu hàng loạt",
    "rate-limit": "Vượt giới hạn tần suất",
}


def _bursts(times_by_key: dict[str, list[datetime]], threshold: int, window: timedelta = WINDOW):
    """Mỗi khóa: lần đầu tiên có >= threshold sự kiện trong một cửa sổ window (chỉ báo một lần cho mỗi khóa).
    Trả về (khóa, đầu cửa sổ, số sự kiện trong cửa sổ, lúc đủ ngưỡng)."""
    out = []
    for key, times in times_by_key.items():
        times = sorted(times)
        j = 0
        for i, t in enumerate(times):
            while times[j] < t - window:
                j += 1
            if i - j + 1 >= threshold:
                out.append((key, times[j], sum(1 for x in times if times[j] <= x <= times[j] + window), t))
                break
    return out


def _span(window: timedelta) -> str:
    return f"{window.seconds // 60} phút" if window < timedelta(days=1) else "24 giờ"


def detect(events: list[Event], long_window: bool = True) -> list[Alert]:
    """long_window=False: chỉ dùng luật cửa sổ 10 phút (để so sánh trong thực nghiệm)."""
    login_fail, spray, forbidden, bad_token, data, limited = (defaultdict(list) for _ in range(6))
    for e in events:
        if e.action == "login" and not e.success:
            login_fail[f"{e.ip}|{e.username}"].append(e.at)
            spray[e.ip].append((e.at, e.username))
        elif e.action == "forbidden":
            forbidden[e.username or "?"].append(e.at)
        elif e.action == "invalid-token":
            bad_token[e.ip].append(e.at)
        elif e.action == "rate-limit":
            limited[e.ip].append(e.at)
        elif e.success and e.username and e.detail.startswith(DATA_PATHS):
            data[e.username].append(e.at)

    brute_rules = [(BRUTE_FORCE, WINDOW)] + ([(BRUTE_FORCE_LONG, LONG_WINDOW)] if long_window else [])
    mass_rules = [(MASS_ACCESS, WINDOW)] + ([(MASS_ACCESS_LONG, LONG_WINDOW)] if long_window else [])
    alerts: list[Alert] = []
    seen: set[tuple[str, str]] = set()

    def add(a: Alert) -> None:  # mỗi (loại, đối tượng) chỉ báo một lần - giữ luật bật sớm nhất
        if (a.kind, a.key) not in seen:
            seen.add((a.kind, a.key))
            alerts.append(a)

    for th, win in brute_rules:
        for k, t, n, f in _bursts(login_fail, th, win):
            ip, user = k.split("|", 1)
            add(Alert("brute-force", f"{user} @ {ip}", t, f, n, f"{n} lần đăng nhập sai vào '{user}' từ {ip} trong {_span(win)}"))
    for ip, items in spray.items():  # số tài khoản khác nhau bị thử trong cửa sổ
        items.sort()
        for i, (t, _) in enumerate(items):
            users: set = set()
            for x, u in items[i:]:
                if x > t + WINDOW:
                    break
                users.add(u)
                if len(users) >= SPRAY_USERS:
                    add(Alert("password-spray", ip, t, x, len(users), f"Đăng nhập sai vào {len(users)}+ tài khoản khác nhau từ {ip}"))
                    break
            if ("password-spray", ip) in seen:
                break
    for k, t, n, f in _bursts(forbidden, FORBIDDEN):
        add(Alert("privilege-probe", k, t, f, n, f"Tài khoản '{k}' bị từ chối quyền {n} lần trong {_span(WINDOW)}"))
    for k, t, n, f in _bursts(bad_token, BAD_TOKEN):
        add(Alert("token-forgery", k, t, f, n, f"{n} yêu cầu với token không hợp lệ từ {k} trong {_span(WINDOW)}"))
    for th, win in mass_rules:
        for k, t, n, f in _bursts(data, th, win):
            add(Alert("mass-access", k, t, f, n, f"Tài khoản '{k}' xem dữ liệu chi tiết {n} lần trong {_span(win)}"))
    for k, v in limited.items():
        add(Alert("rate-limit", k, min(v), min(v), len(v), f"{k} bị chặn do vượt giới hạn tần suất"))
    return sorted(alerts, key=lambda a: a.fired_at)


def load_events(session, since: datetime) -> list[Event]:
    from sqlalchemy import select

    from storage.models import AuditLog

    rows = session.scalars(select(AuditLog).where(AuditLog.at >= since).order_by(AuditLog.at)).all()
    return [Event(r.at, r.username, r.action, r.detail or "", r.ip or "?", r.success) for r in rows]


def redact_for_role(info, role: str | None):
    """Bỏ chi tiết cảnh báo an ninh (tên tài khoản, IP) khỏi kết quả monitor với người không phải admin."""
    if role == "admin" or not isinstance(info, dict):
        return info
    info = {k: v for k, v in info.items() if k != "security_alerts_24h"}
    if isinstance(info.get("alerts"), list):
        kept = [a for a in info["alerts"] if not str(a).startswith(ALERT_PREFIX)]
        hidden = len(info["alerts"]) - len(kept)
        info["alerts"] = kept + ([f"Có {hidden} cảnh báo an ninh - quản trị viên xem chi tiết"] if hidden else [])
    return info
