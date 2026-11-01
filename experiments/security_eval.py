"""T-35 (CH4): đánh giá cơ chế an ninh theo chuỗi phát hiện -> bảo vệ -> ghi nhật ký -> cảnh báo.

Phần 1 - mô phỏng nhật ký 7 ngày: 30 người dùng bình thường (dùng chung 3 IP như mạng trường, có gõ sai mật khẩu,
token hết hạn, duyệt dữ liệu nhanh) trộn với các đợt tấn công nhiều cường độ, gồm cả biến thể chậm cố ý né ngưỡng.
Chạy security/detect.py trên toàn bộ nhật ký, tính tỉ lệ phát hiện (1 - False Negative) theo loại tấn công và số
cảnh báo nhầm (False Positive) trên người dùng bình thường. 5 seed.
Phần 2 - kiểm thử đầu-cuối trên API thật (TestClient): mỗi kịch bản kiểm tra bị chặn? có ghi nhật ký? có cảnh báo?
Tài khoản và dòng nhật ký tạm của phần 2 được xóa sau khi chạy.
Chạy: python -m experiments.security_eval
"""
from __future__ import annotations

import random
from collections import Counter
from datetime import datetime, timedelta, timezone

from experiments import save_result
from security.detect import KINDS, Event, detect

SEEDS = (0, 1, 2, 3, 4)
START = datetime(2026, 1, 5)
NORMAL_USERS, NAT_IPS = 30, 3


def normal_traffic(rng: random.Random, split_expired: bool = True) -> list[Event]:
    expired_action = "expired-token" if split_expired else "invalid-token"  # trước khi tách: hết hạn cũng bị coi là token giả
    ev = []
    for u in range(NORMAL_USERS):
        name, ip = f"user{u}", f"10.0.0.{u % NAT_IPS + 1}"
        role = rng.choice(["viewer", "analyst", "analyst"])
        for day in range(7):
            for _ in range(rng.randint(0, 3)):  # số phiên làm việc trong ngày
                t = START + timedelta(days=day, hours=rng.uniform(7, 22))
                for _ in range(rng.choices([0, 1, 2, 3, 4], [85, 9, 3, 2, 1])[0]):  # gõ sai mật khẩu rồi mới đúng
                    ev.append(Event(t, name, "login", "", ip, False))
                    t += timedelta(seconds=rng.uniform(3, 20))
                ev.append(Event(t, name, "login", "", ip, True))
                if rng.random() < 0.2:  # token hết hạn: trang tải song song vài API cùng lúc (middleware ghi là expired-token)
                    for _ in range(rng.randint(3, 6)):
                        ev.append(Event(t, None, expired_action, "GET /stats", ip, False))
                if rng.random() < 0.03:  # bấm nhầm vào đường dẫn không có quyền
                    ev.append(Event(t, name, "forbidden", "GET /users", ip, False))
                if role == "analyst":
                    fast = rng.random() < 0.1  # phiên lật trang nhanh
                    for _ in range(rng.randint(5, 80 if fast else 40)):
                        t += timedelta(seconds=rng.uniform(2, 8) if fast else rng.uniform(5, 60))
                        ev.append(Event(t, name, "get analysis", f"GET /analysis/posts?page={rng.randint(1, 50)}", ip, True))
    return ev


def attacks(rng: random.Random) -> list[tuple[str, str, str, list[Event]]]:
    """(loại kịch bản, loại cảnh báo mong đợi, khóa nhận diện kẻ tấn công, sự kiện)."""
    out = []

    def at(): return START + timedelta(days=rng.uniform(0, 6.5))

    for i in range(10):
        ip, t, ev = f"203.0.113.{i}", at(), []
        for _ in range(rng.randint(10, 200)):
            ev.append(Event(t, "admin", "login", "", ip, False))
            t += timedelta(seconds=rng.uniform(1, 20))
        out.append(("Dò mật khẩu nhanh", "brute-force", ip, ev))
    for i in range(10):
        ip, t, ev = f"203.0.114.{i}", at(), []
        for _ in range(rng.randint(20, 60)):
            ev.append(Event(t, "admin", "login", "", ip, False))
            t += timedelta(minutes=rng.uniform(3, 6))
        out.append(("Dò mật khẩu chậm (né ngưỡng)", "brute-force", ip, ev))
    for i in range(10):
        ip, t, ev = f"198.51.100.{i}", at(), []
        for u in rng.sample(range(NORMAL_USERS), rng.randint(6, 25)):
            ev.append(Event(t, f"user{u}", "login", "", ip, False))
            t += timedelta(seconds=rng.uniform(5, 30))
        out.append(("Thử mật khẩu trên nhiều tài khoản", "password-spray", ip, ev))
    for i in range(10):
        name, ip, t, ev = f"stolen_viewer{i}", f"192.0.2.{i}", at(), []
        for _ in range(rng.randint(6, 30)):
            ev.append(Event(t, name, "forbidden", rng.choice(["GET /users", "GET /audit", "POST /models/3/select"]), ip, False))
            t += timedelta(seconds=rng.uniform(1, 15))
        out.append(("Tài khoản bị chiếm dò quyền admin", "privilege-probe", name, ev))
    for i in range(10):
        ip, t, ev = f"192.0.3.{i}", at(), []
        for _ in range(rng.randint(15, 100)):
            ev.append(Event(t, None, "invalid-token", "GET /analysis/posts", ip, False))
            t += timedelta(seconds=rng.uniform(0.5, 10))
        out.append(("Gửi token giả", "token-forgery", ip, ev))
    for i in range(10):
        name, ip, t, ev = f"stolen_analyst{i}", f"192.0.4.{i}", at(), []
        for p in range(rng.randint(100, 1000)):
            ev.append(Event(t, name, "get analysis", f"GET /analysis/posts?page={p}", ip, True))
            t += timedelta(seconds=rng.uniform(0.2, 3))
        out.append(("Tải dữ liệu hàng loạt nhanh", "mass-access", name, ev))
    for i in range(10):
        name, ip, t, ev = f"slow_analyst{i}", f"192.0.5.{i}", at(), []
        for p in range(rng.randint(200, 600)):
            ev.append(Event(t, name, "get analysis", f"GET /analysis/posts?page={p}", ip, True))
            t += timedelta(seconds=rng.uniform(15, 30))
        out.append(("Tải dữ liệu hàng loạt chậm (né ngưỡng)", "mass-access", name, ev))
    return out


_DATA = {}


def _data(seed: int, split_expired: bool):
    if (seed, split_expired) not in _DATA:
        rng = random.Random(seed)
        _DATA[(seed, split_expired)] = (normal_traffic(rng, split_expired), attacks(rng))
    return _DATA[(seed, split_expired)]


def simulate(long_window: bool = True, split_expired: bool = True) -> tuple[list[dict], list[dict], dict]:
    per_kind: dict[str, dict] = {}
    fp_rows, fp_total, normal_events = [], 0, 0
    for seed in SEEDS:
        normal, atk = _data(seed, split_expired)
        normal_events += len(normal)
        alerts = detect(normal + [e for *_, ev in atk for e in ev], long_window=long_window)
        for scenario, kind, key, ev in atk:
            hit = next((a for a in alerts if a.kind == kind and key in a.key), None)
            d = per_kind.setdefault(scenario, {"n": 0, "tp": 0, "delay": [], "events": []})
            d["n"] += 1
            d["events"].append(len(ev))
            if hit:
                d["tp"] += 1
                d["delay"].append(sum(1 for e in ev if e.at <= hit.fired_at))  # số sự kiện tấn công đã lọt qua tới lúc cảnh báo
        atk_keys = {key for _, _, key, _ in atk}
        fps = [a for a in alerts if not any(k in a.key for k in atk_keys)]
        fp_total += len(fps)
        for a in fps:
            fp_rows.append({"Seed": seed, "Loại cảnh báo": KINDS[a.kind], "Đối tượng": a.key, "Số sự kiện": a.count})
    rows = []
    for scenario, d in per_kind.items():
        rows.append({"Kịch bản tấn công": scenario, "Số đợt": d["n"], "Phát hiện": d["tp"], "Tỉ lệ phát hiện": f"{d['tp'] / d['n']:.0%}",
                     "Tỉ lệ bỏ sót (FN)": f"{1 - d['tp'] / d['n']:.0%}",
                     "Sự kiện/đợt (TB)": round(sum(d["events"]) / d["n"]),
                     "Phát hiện sau ~ sự kiện": round(sum(d["delay"]) / len(d["delay"])) if d["delay"] else None})
    summary = {"normal_events": normal_events, "fp_total": fp_total, "weeks": len(SEEDS)}
    return rows, fp_rows, summary


def sweep_mass_access() -> list[dict]:
    """Đánh đổi bỏ sót / báo nhầm theo ngưỡng 'truy xuất hàng loạt' trong 10 phút."""
    from security import detect as D

    saved, out = D.MASS_ACCESS, []
    try:
        for th in (40, 60, 80, 100, 150, 200):
            D.MASS_ACCESS = th
            rows, fp_rows, summ = simulate(long_window=True)
            r = {x["Kịch bản tấn công"]: x["Tỉ lệ phát hiện"] for x in rows}
            out.append({"Ngưỡng (lần xem / 10 phút)": th, "Phát hiện tải nhanh": r["Tải dữ liệu hàng loạt nhanh"],
                        "Phát hiện tải chậm": r["Tải dữ liệu hàng loạt chậm (né ngưỡng)"],
                        "Cảnh báo nhầm / tuần": round(sum(1 for f in fp_rows if f["Loại cảnh báo"] == KINDS["mass-access"]) / summ["weeks"], 1)})
            print(out[-1])
    finally:
        D.MASS_ACCESS = saved
    return out


def end_to_end() -> list[dict]:
    import jwt
    from fastapi.testclient import TestClient
    from sqlalchemy import delete, select

    from api import security_mw
    from api.main import app
    from security import auth
    from security.auth import create_token, hash_password
    from security.detect import load_events
    from storage.database import SessionLocal
    from storage.models import AuditLog, User

    start = datetime.utcnow() - timedelta(seconds=1)
    users = {"zz_viewer": "viewer", "zz_analyst": "analyst"}
    with SessionLocal() as s:
        for u, r in users.items():
            s.add(User(username=u, password_hash=hash_password("Eval-only-12345"), role=r))
        s.commit()
    c = TestClient(app)
    hv = {"Authorization": f"Bearer {create_token('zz_viewer', 'viewer')}"}
    ha = {"Authorization": f"Bearer {create_token('zz_analyst', 'analyst')}"}
    rows = []

    def logged(action: str, since: datetime) -> int:
        with SessionLocal() as s:
            return len(s.scalars(select(AuditLog).where(AuditLog.at >= since, AuditLog.action == action, AuditLog.ip == "testclient")).all())

    def scenario(name: str, kind: str | None, action: str, fn):
        t0 = datetime.utcnow()
        codes = fn()
        with SessionLocal() as s:
            alerts = [a for a in detect([e for e in load_events(s, t0) if e.ip == "testclient"]) if kind and a.kind == kind]
        blocked = sorted({x for x in codes if x >= 400})
        rows.append({"Kịch bản": name, "Phản hồi": ", ".join(map(str, blocked)) or "200",
                     "Bị chặn": "Có" if blocked else "Không", "Ghi nhật ký": f"Có ({logged(action, t0)} dòng)" if logged(action, t0) else "Không",
                     "Cảnh báo": KINDS[alerts[0].kind] if alerts else ("Không cần" if kind is None else "Không")})
        print(rows[-1])

    try:
        scenario("Dò mật khẩu 8 lần", "brute-force", "login",
                 lambda: [c.post("/auth/login", json={"username": "zz_analyst", "password": f"sai{i}"}).status_code for i in range(8)])
        auth._FAILS.clear()
        scenario("SQL injection ở ô đăng nhập", None, "login",
                 lambda: [c.post("/auth/login", json={"username": "' OR '1'='1' --", "password": "x' OR 1=1 --"}).status_code])
        auth._FAILS.clear()
        scenario("Thử mật khẩu trên 6 tài khoản", "password-spray", "login",
                 lambda: [c.post("/auth/login", json={"username": f"user{i}", "password": "Matkhau123"}).status_code for i in range(6)])
        auth._FAILS.clear()
        scenario("Viewer gọi chức năng admin 6 lần", "privilege-probe", "forbidden",
                 lambda: [c.get(p, headers=hv).status_code for p in ["/users", "/audit", "/users", "/audit", "/users", "/audit"]])
        scenario("Token giả 12 lần", "token-forgery", "invalid-token",
                 lambda: [c.get("/stats", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.e30.gia"}).status_code for _ in range(12)])
        expired = jwt.encode({"sub": "zz_analyst", "role": "analyst", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
                             auth._SECRET, algorithm="HS256")
        scenario("Token hết hạn 12 lần (người dùng thật hết phiên)", None, "expired-token",
                 lambda: [c.get("/stats", headers={"Authorization": f"Bearer {expired}"}).status_code for _ in range(12)])
        scenario("Analyst tải 110 trang dữ liệu liên tục", "mass-access", "get analysis",
                 lambda: [c.get(f"/analysis/posts?page={i % 20 + 1}", headers=ha).status_code for i in range(110)])
        saved = security_mw.RATE_LIMITS[-1]
        security_mw.RATE_LIMITS[-1] = (saved[0], 20)  # hạ ngưỡng để thử nhanh
        security_mw._hits.clear()
        try:
            scenario("Gửi dồn 30 yêu cầu (ngưỡng thử 20/phút)", "rate-limit", "rate-limit",
                     lambda: [c.get("/health").status_code for _ in range(30)])
        finally:
            security_mw.RATE_LIMITS[-1] = saved
            security_mw._hits.clear()
    finally:
        auth._FAILS.clear()
        with SessionLocal() as s:  # dọn: không để dữ liệu kiểm thử gây cảnh báo thật ở bước monitor
            s.execute(delete(AuditLog).where(AuditLog.at >= start, AuditLog.ip == "testclient"))
            s.execute(delete(User).where(User.username.in_(list(users))))
            s.commit()
    return rows


def run() -> None:
    from security import detect as D

    versions = {"Bản đầu: chỉ 10 phút": simulate(long_window=False, split_expired=False),
                "+ cửa sổ 24 giờ": simulate(long_window=True, split_expired=False),
                "+ tách token hết hạn": simulate(long_window=True, split_expired=True)}
    rows, fp_rows, summary = versions["+ tách token hết hạn"]
    compare = [{"Kịch bản tấn công": r["Kịch bản tấn công"], **{v: res[0][i]["Tỉ lệ phát hiện"] for v, res in versions.items()}}
               for i, r in enumerate(rows)]
    compare.append({"Kịch bản tấn công": "Cảnh báo nhầm / tuần", **{v: round(res[2]["fp_total"] / res[2]["weeks"], 1) for v, res in versions.items()}})
    first, *_, last = versions
    sweep = sweep_mass_access()
    e2e = end_to_end()
    per_week = summary["fp_total"] / summary["weeks"]
    fp_kinds = Counter(f["Loại cảnh báo"] for f in fp_rows)
    findings = [f"Cảnh báo nhầm trên người dùng bình thường: {summary['fp_total']} cảnh báo / {summary['weeks']} tuần mô phỏng "
                f"({per_week:.1f}/tuần, trên {summary['normal_events'] // summary['weeks']} sự kiện bình thường mỗi tuần)"
                + (": " + ", ".join(f"{k} {n}" for k, n in fp_kinds.items()) if fp_kinds else "") + "."]
    v1_fp = Counter(f["Loại cảnh báo"] for f in versions["+ cửa sổ 24 giờ"][1])
    if v1_fp[KINDS["token-forgery"]] > fp_kinds[KINDS["token-forgery"]]:
        findings.append(f"Trước khi tách, có {v1_fp[KINDS['token-forgery']]} cảnh báo token giả nhầm: nhiều người dùng chung một IP (NAT mạng trường) "
                        "hết phiên gần cùng lúc. Middleware nay ghi riêng token đúng chữ ký nhưng hết hạn (expired-token), chỉ token sai chữ ký "
                        "mới được tính là token giả.")
    for r in rows:
        if r["Tỉ lệ bỏ sót (FN)"] != "0%":
            findings.append(f"'{r['Kịch bản tấn công']}' vẫn bị bỏ sót {r['Tỉ lệ bỏ sót (FN)']}: kẻ tấn công đi dưới cả ngưỡng 10 phút lẫn 24 giờ. "
                            "Hướng khắc phục: phát hiện bất thường theo hồ sơ từng người dùng (so với mức dùng thường ngày của chính họ).")
    fixed = [c for c in compare[:-1] if c[first] != c[last]]
    if fixed:
        findings.append("So với bản đầu, bộ luật hiện tại cải thiện: " + "; ".join(f"{c['Kịch bản tấn công']} {c[first]} -> {c[last]}" for c in fixed)
                        + f"; cảnh báo nhầm {compare[-1][first]} -> {compare[-1][last]} mỗi tuần.")
    findings.append("Ngưỡng truy xuất hàng loạt là đánh đổi giữa bỏ sót và báo nhầm (người dùng thật đôi khi lật trang nhanh): "
                    + "; ".join(f"{x['Ngưỡng (lần xem / 10 phút)']}: bắt {x['Phát hiện tải nhanh']} tải nhanh, {x['Cảnh báo nhầm / tuần']} nhầm/tuần" for x in sweep)
                    + f". Ngưỡng mặc định {D.MASS_ACCESS} được chọn từ chính bảng này nên kết quả ở ngưỡng đó là lạc quan; "
                    "cần hiệu chỉnh lại theo nhật ký vận hành thật.")
    fails = [r["Kịch bản"] for r in e2e if r["Cảnh báo"] == "Không" or r["Ghi nhật ký"] == "Không"]
    findings.append("Kiểm thử đầu-cuối: " + ("mọi kịch bản đều bị chặn hoặc ghi nhật ký và có cảnh báo khi cần." if not fails
                                            else "chưa đạt ở: " + "; ".join(fails) + "."))
    findings.append("Truy xuất dữ liệu hàng loạt bằng tài khoản hợp lệ không bị chặn tức thời (chỉ cảnh báo) - "
                    "đây là chủ đích để không cản người dùng thật; cần người quản trị xem cảnh báo và khóa tài khoản.")
    save_result("security_eval", "Đánh giá cơ chế an ninh: phát hiện, bảo vệ, ghi nhật ký, cảnh báo",
                "CH4 - đánh giá các cơ chế an ninh, tỉ lệ False Positive / False Negative (T-35)",
                f"Bộ phát hiện luật (security/detect.py), cửa sổ trượt {D.WINDOW.seconds // 60} phút, ngưỡng: đăng nhập sai {D.BRUTE_FORCE}, "
                f"số tài khoản bị thử {D.SPRAY_USERS}, bị từ chối quyền {D.FORBIDDEN}, token giả {D.BAD_TOKEN}, xem dữ liệu chi tiết {D.MASS_ACCESS}; "
                f"cửa sổ 24 giờ: đăng nhập sai {D.BRUTE_FORCE_LONG}, xem dữ liệu chi tiết {D.MASS_ACCESS_LONG}. "
                f"Mô phỏng: {NORMAL_USERS} người dùng thật dùng chung {NAT_IPS} IP, 7 ngày, {len(SEEDS)} seed; mỗi kịch bản 10 đợt/seed. "
                "Dữ liệu mô phỏng không thay được dữ liệu vận hành thật - ngưỡng cần hiệu chỉnh lại khi có nhật ký thật.",
                [{"title": "Tỉ lệ phát hiện theo kịch bản (mô phỏng, bộ luật đầy đủ)", "columns": list(rows[0].keys()), "rows": rows},
                 {"title": "So sánh bộ luật", "columns": list(compare[0].keys()), "rows": compare},
                 {"title": "Đánh đổi theo ngưỡng truy xuất hàng loạt", "columns": list(sweep[0].keys()), "rows": sweep},
                 {"title": "Kiểm thử đầu-cuối trên API", "columns": list(e2e[0].keys()), "rows": e2e},
                 {"title": "Các cảnh báo nhầm (mô phỏng)", "columns": ["Seed", "Loại cảnh báo", "Đối tượng", "Số sự kiện"], "rows": fp_rows}],
                findings)


if __name__ == "__main__":
    run()
