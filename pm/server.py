"""Server quản lý đề tài (chỉ dùng thư viện chuẩn Python 3.10+).

Chạy:  python pm/server.py   -> mở http://localhost:8765

Dữ liệu là các file .md trong pm/items và pm/docs (mỗi mục 1 file, phần thảo luận chỉ
thêm vào cuối) -> 2 người sửa song song trên git gần như không xung đột. Ảnh dán từ
clipboard lưu ở pm/assets. Nút "Đồng bộ" trên giao diện chạy commit -> pull --rebase -> push
(chỉ đụng tới thư mục pm/).
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import secrets
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

PM_DIR = Path(__file__).resolve().parent
ITEMS_DIR = PM_DIR / "items"
DOCS_DIR = PM_DIR / "docs"
ASSETS_DIR = PM_DIR / "assets"
CONFIG_PATH = PM_DIR / "config.json"
USER_PATH = PM_DIR / ".user"
INDEX_PATH = PM_DIR / "INDEX.md"
STATIC_FILES = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/style.css": "style.css"}

HOST, PORT = "127.0.0.1", 8765
MAX_UPLOAD = 15 * 1024 * 1024
COMMENTS_HEADING = "## Thảo luận"
COMMENTS_NOTE = "<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->"
COMMENT_RE = re.compile(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?) · (.+?)\s*$", re.M)
ID_RE = re.compile(r"^[A-Z]{1,6}-\d{3,4}$")
CHECK_RE = re.compile(r"^\s*[-*] \[( |x|X)\] +(?=\S)", re.M)  # bỏ qua dòng checklist trống của mẫu

LOCK = threading.Lock()


# ===== Cấu hình & người dùng =====


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def current_user() -> str:
    if USER_PATH.exists():
        return USER_PATH.read_text(encoding="utf-8").strip()
    return ""


def type_by_prefix(config: dict) -> dict[str, str]:
    return {t["prefix"]: key for key, t in config["types"].items()}


def dir_for_type(type_key: str) -> Path:
    return DOCS_DIR if type_key == "doc" else ITEMS_DIR


# ===== Đọc/ghi file mục =====


def parse_value(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [v.strip() for v in raw[1:-1].split(",") if v.strip()]
    return raw


def format_value(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(v).strip() for v in value if str(v).strip()) + "]"
    return str(value).replace("\n", " ").strip()


def parse_item_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    meta: dict = {}
    warnings: list[str] = []
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            for line in text[4:end].split("\n"):
                if not line.strip() or ":" not in line:
                    continue
                key, _, val = line.partition(":")
                key = key.strip()
                if key in meta:
                    # Thường do merge=union khi 2 người cùng sửa 1 trường -> giữ giá trị sau, báo để xem lại
                    warnings.append(f"Trường '{key}' bị lặp (có thể do 2 người cùng sửa) - đang lấy giá trị sau cùng")
                meta[key] = parse_value(val)
            body = text[end + 4:].lstrip("\n")

    content, comments = body, []
    idx = body.find("\n" + COMMENTS_HEADING)
    if body.startswith(COMMENTS_HEADING):
        idx = -1
        content, rest = "", body[len(COMMENTS_HEADING):]
        comments = split_comments(rest)
    elif idx != -1:
        content = body[:idx]
        comments = split_comments(body[idx + 1 + len(COMMENTS_HEADING):])

    checks = CHECK_RE.findall(content)
    return {
        "meta": meta,
        "content": content.rstrip() + "\n" if content.strip() else "",
        "comments": comments,
        "checklist": {"done": sum(1 for c in checks if c.lower() == "x"), "total": len(checks)},
        "warnings": warnings,
        "rev": hashlib.sha1(text.encode("utf-8")).hexdigest()[:12],
        "file": path.relative_to(PM_DIR).as_posix(),
    }


def split_comments(section: str) -> list[dict]:
    matches = list(COMMENT_RE.finditer(section))
    comments = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        comments.append({
            "index": i,
            "time": m.group(1),
            "author": m.group(2),
            "text": section[m.end():end].strip("\n").rstrip(),
        })
    return comments


def render_item_file(meta: dict, content: str, comments: list[dict]) -> str:
    order = ["id", "type", "title", "status"]
    keys = order + [k for k in meta if k not in order]
    lines = ["---"] + [f"{k}: {format_value(meta[k])}" for k in keys if k in meta and meta[k] not in (None, "", [])] + ["---", ""]
    out = "\n".join(lines) + "\n" + (content.strip() + "\n\n" if content.strip() else "")
    out += COMMENTS_HEADING + "\n" + COMMENTS_NOTE + "\n"
    for c in comments:
        out += f"\n### {c['time']} · {c['author']}\n{c['text'].strip()}\n"
    return out


def find_item_path(item_id: str) -> Path | None:
    if not ID_RE.match(item_id):
        return None
    for folder in (ITEMS_DIR, DOCS_DIR):
        for p in folder.glob(f"{item_id}*.md"):
            if p.name == f"{item_id}.md" or p.name.startswith(f"{item_id}-"):
                return p
    return None


def slugify(title: str) -> str:
    table = str.maketrans(
        "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ",
        "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd",
    )
    s = title.lower().translate(table)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:50].rstrip("-") or "muc"


def list_items() -> list[dict]:
    items = []
    for folder in (DOCS_DIR, ITEMS_DIR):
        for p in sorted(folder.glob("*.md")):
            try:
                parsed = parse_item_file(p)
            except Exception as exc:  # file hỏng không làm sập cả danh sách
                items.append({"meta": {"id": p.stem, "title": p.name}, "warnings": [f"Lỗi đọc file: {exc}"], "file": p.name})
                continue
            last = parsed["comments"][-1] if parsed["comments"] else None
            items.append({
                "meta": parsed["meta"],
                "checklist": parsed["checklist"],
                "comment_count": len(parsed["comments"]),
                "last_comment": {"time": last["time"], "author": last["author"]} if last else None,
                "recent_comments": [
                    {"time": c["time"], "author": c["author"], "text": c["text"][:160]} for c in parsed["comments"][-3:]
                ],
                "excerpt": parsed["content"][:400],
                "warnings": parsed["warnings"],
                "file": parsed["file"],
            })
    return items


def next_id(config: dict, type_key: str) -> str:
    prefix = config["types"][type_key]["prefix"]
    folder = dir_for_type(type_key)
    nums = [int(m.group(1)) for p in folder.glob(f"{prefix}-*.md") if (m := re.match(rf"{prefix}-(\d+)", p.name))]
    return f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ===== INDEX.md (chỉ sinh lúc đồng bộ để tránh xung đột git) =====


def build_index() -> str:
    config = load_config()
    items = list_items()
    out = [
        "# Bảng tổng hợp quản lý đề tài",
        "",
        "> File tự sinh bởi `pm/server.py` mỗi lần bấm **Đồng bộ** - không sửa tay. "
        "Xem/sửa đầy đủ: `python pm/server.py` rồi mở http://localhost:8765",
        "",
    ]
    for type_key, t in config["types"].items():
        group = [i for i in items if i["meta"].get("type") == type_key]
        if not group:
            continue
        labels = {s["key"]: s["label"] for s in t["statuses"]}
        counts = {}
        for i in group:
            counts[i["meta"].get("status", "")] = counts.get(i["meta"].get("status", ""), 0) + 1
        summary = ", ".join(f"{labels.get(k, k)}: {v}" for k, v in counts.items())
        out += [f"## {t['label']} ({len(group)}) — {summary}", "", "| ID | Tiêu đề | Trạng thái | Phụ trách | Checklist | Thảo luận |", "|---|---|---|---|---|---|"]
        for i in group:
            m = i["meta"]
            ck = i["checklist"]
            progress = "%d/%d" % (ck["done"], ck["total"]) if ck["total"] else ""
            title = str(m.get("title", "")).replace("|", "\\|")
            status = labels.get(m.get("status", ""), m.get("status", ""))
            out.append(
                f"| [{m.get('id')}]({i['file']}) | {title} | {status} "
                f"| {m.get('owner', '')} | {progress} | {i['comment_count'] or ''} |"
            )
        out.append("")
    return "\n".join(out)


# ===== Git =====


def git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=PM_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )


def git_status(fetch: bool) -> dict:
    result: dict = {"ok": True}
    if fetch:
        f = git("fetch", "--quiet", timeout=30)
        result["fetch_error"] = f.stderr.strip() if f.returncode else ""
    result["branch"] = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    porcelain = git("status", "--porcelain", "--untracked-files=all", "--", ".").stdout.splitlines()
    changed = [line for line in porcelain if not line.endswith("INDEX.md")]
    result["local_changes"] = len(changed)
    counts = git("rev-list", "--left-right", "--count", "HEAD...@{u}")
    if counts.returncode == 0:
        ahead, behind = counts.stdout.split()
        result["ahead"], result["behind"] = int(ahead), int(behind)
    else:
        result["ahead"] = result["behind"] = 0
        result["upstream_error"] = counts.stderr.strip()
    return result


def changed_ids(names: list[str]) -> list[str]:
    ids = []
    for n in names:
        m = re.search(r"/([A-Z]{1,6}-\d{3,4})", "/" + n)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def git_sync(user: str) -> dict:
    log: list[str] = []

    def step(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
        r = git(*args, timeout=timeout)
        log.append(f"$ git {' '.join(args)}\n{(r.stdout + r.stderr).strip()}")
        return r

    # 1. INDEX.md là file sinh tự động -> bỏ thay đổi cục bộ, sinh lại sau khi pull
    git("checkout", "--", "INDEX.md")
    step("add", "-A", "--", ".")
    git("reset", "--quiet", "--", "INDEX.md")
    staged = git("diff", "--cached", "--name-only", "--", ".").stdout.split()
    if staged:
        ids = changed_ids(staged)
        what = ", ".join(ids[:6]) + (f" +{len(ids) - 6}" if len(ids) > 6 else "") if ids else "cập nhật"
        r = step("commit", "-m", f"pm: {what} ({user or 'không rõ'})", "--", ".")
        if r.returncode:
            return {"ok": False, "error": "Commit thất bại", "log": log}

    # 2. Lấy thay đổi của người kia
    r = step("pull", "--rebase", "--autostash", timeout=180)
    if r.returncode:
        if (Path(git("rev-parse", "--git-dir").stdout.strip()) / "rebase-merge").exists() or "rebase" in r.stderr.lower():
            step("rebase", "--abort")
        return {"ok": False, "error": "Pull thất bại (xung đột hoặc lỗi mạng) - đã hoàn tác rebase, dữ liệu cục bộ vẫn nguyên. Xem log.", "log": log}

    # 3. Hai người cùng tạo mục mới khi chưa đồng bộ -> trùng mã. Đổi mã mục của mình (vừa commit).
    renamed = fix_duplicate_ids(staged)
    if renamed:
        step("add", "-A", "--", "items", "docs")
        step("commit", "-m", "pm: đổi mã do trùng " + ", ".join(f"{a}→{b}" for a, b in renamed), "--", ".")

    # 4. Sinh lại INDEX.md và commit nếu đổi
    INDEX_PATH.write_text(build_index(), encoding="utf-8")
    if git("status", "--porcelain", "--", "INDEX.md").stdout.strip():
        step("add", "--", "INDEX.md")
        step("commit", "-m", "pm: cập nhật INDEX.md", "--", "INDEX.md")

    # 5. Đẩy lên
    status = git_status(fetch=False)
    if status.get("ahead"):
        r = step("push", timeout=180)
        if r.returncode:
            return {"ok": False, "error": "Push thất bại - xem log (có thể chưa đăng nhập GitHub hoặc không có quyền).", "log": log}
    return {"ok": True, "log": log, "committed": bool(staged), "renamed": renamed}


def fix_duplicate_ids(mine: list[str]) -> list[tuple[str, str]]:
    """Mã bị trùng sau khi pull -> đổi mã file do mình vừa tạo (nằm trong `mine`) sang mã trống kế tiếp,
    và sửa các chỗ nhắc mã cũ trong những file mình vừa sửa."""
    config = load_config()
    by_id: dict[str, list[Path]] = {}
    for folder in (ITEMS_DIR, DOCS_DIR):
        for p in folder.glob("*.md"):
            if m := re.match(r"^([A-Z]{1,6}-\d{3,4})", p.name):
                by_id.setdefault(m.group(1), []).append(p)
    mine_names = {Path(n).name for n in mine}
    prefixes = type_by_prefix(config)
    renamed = []
    for old_id, paths in by_id.items():
        if len(paths) < 2:
            continue
        for p in [p for p in paths if p.name in mine_names][: len(paths) - 1]:
            type_key = prefixes.get(old_id.split("-")[0])
            if not type_key:
                continue
            new_id = next_id(config, type_key)
            parsed = parse_item_file(p)
            meta = dict(parsed["meta"], id=new_id)
            target = p.with_name(new_id + p.name[len(old_id):])
            target.write_text(render_item_file(meta, parsed["content"], parsed["comments"]), encoding="utf-8")
            p.unlink()
            renamed.append((old_id, new_id))
            for n in mine_names - {p.name}:
                other = next((q for f in (ITEMS_DIR, DOCS_DIR) if (q := f / n).exists()), None)
                if other:
                    txt = other.read_text(encoding="utf-8")
                    other.write_text(re.sub(rf"\b{re.escape(old_id)}\b", new_id, txt), encoding="utf-8")
    return renamed


# ===== HTTP =====


class Handler(BaseHTTPRequestHandler):
    server_version = "pm/1.0"

    def log_message(self, fmt, *args):  # gọn log
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    # --- tiện ích ---
    def send_json(self, data, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def error(self, status: int, message: str):
        self.send_json({"error": message}, status)

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD:
            raise ValueError("File quá lớn (tối đa 15MB)")
        return self.rfile.read(length) if length else b""

    def read_json(self) -> dict:
        raw = self.read_body()
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Dữ liệu gửi lên không hợp lệ (cần JSON UTF-8): {exc}") from exc

    def dispatch(self, fn):
        """Bọc mọi handler: lỗi dữ liệu -> 400, lỗi khác -> 500 kèm thông báo (không đóng kết nối im lặng)."""
        try:
            return fn()
        except ValueError as exc:
            return self.error(400, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.log_error("Lỗi xử lý %s: %r", self.path, exc)
            return self.error(500, f"Lỗi server: {exc}")

    def send_file(self, path: Path):
        if not path.is_file():
            return self.error(404, "Không tìm thấy")
        data = path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def check_origin(self) -> bool:
        # Chặn trang web lạ gửi request ghi dữ liệu tới server local
        origin = self.headers.get("Origin")
        return origin is None or origin in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}")

    # --- định tuyến ---
    def do_GET(self):
        self.dispatch(self.route_get)

    def do_POST(self):
        self.dispatch(self.route_post)

    def do_PUT(self):
        self.dispatch(self.route_put)

    def do_DELETE(self):
        self.dispatch(self.route_delete)

    def route_get(self):
        url = urlparse(self.path)
        path = unquote(url.path)
        if path in STATIC_FILES:
            return self.send_file(PM_DIR / STATIC_FILES[path])
        if path.startswith("/assets/"):
            target = (ASSETS_DIR / path[len("/assets/"):]).resolve()
            if ASSETS_DIR.resolve() not in target.parents:
                return self.error(403, "Đường dẫn không hợp lệ")
            return self.send_file(target)
        if path == "/api/meta":
            return self.send_json({"config": load_config(), "user": current_user()})
        if path == "/api/items":
            return self.send_json(list_items())
        if m := re.match(r"^/api/items/([A-Z]{1,6}-\d{3,4})$", path):
            p = find_item_path(m.group(1))
            return self.send_json(parse_item_file(p)) if p else self.error(404, "Không tìm thấy mục")
        if path == "/api/git/status":
            fetch = parse_qs(url.query).get("fetch", ["0"])[0] == "1"
            try:
                return self.send_json(git_status(fetch))
            except Exception as exc:
                return self.send_json({"ok": False, "error": str(exc)})
        return self.error(404, "Không tìm thấy")

    def route_post(self):
        if not self.check_origin():
            return self.error(403, "Origin không hợp lệ")
        path = urlparse(self.path).path
        if path == "/api/user":
            name = str(self.read_json().get("name", "")).strip()
            if not name:
                return self.error(400, "Thiếu tên")
            USER_PATH.write_text(name, encoding="utf-8")
            return self.send_json({"user": name})
        if path == "/api/items":
            return self.create_item(self.read_json())
        if m := re.match(r"^/api/items/([A-Z]{1,6}-\d{3,4})/comments$", path):
            return self.add_comment(m.group(1), self.read_json())
        if path == "/api/upload":
            return self.upload()
        if path == "/api/git/sync":
            with LOCK:
                return self.send_json(git_sync(current_user()))
        return self.error(404, "Không tìm thấy")

    def route_put(self):
        if not self.check_origin():
            return self.error(403, "Origin không hợp lệ")
        path = urlparse(self.path).path
        if m := re.match(r"^/api/items/([A-Z]{1,6}-\d{3,4})$", path):
            return self.update_item(m.group(1), self.read_json())
        if m := re.match(r"^/api/items/([A-Z]{1,6}-\d{3,4})/comments/(\d+)$", path):
            return self.edit_comment(m.group(1), int(m.group(2)), self.read_json())
        return self.error(404, "Không tìm thấy")

    def route_delete(self):
        if not self.check_origin():
            return self.error(403, "Origin không hợp lệ")
        path = urlparse(self.path).path
        if m := re.match(r"^/api/items/([A-Z]{1,6}-\d{3,4})$", path):
            with LOCK:
                p = find_item_path(m.group(1))
                if not p:
                    return self.error(404, "Không tìm thấy mục")
                p.unlink()
            return self.send_json({"ok": True})
        if m := re.match(r"^/api/items/([A-Z]{1,6}-\d{3,4})/comments/(\d+)$", path):
            return self.edit_comment(m.group(1), int(m.group(2)), self.read_json(), delete=True)
        return self.error(404, "Không tìm thấy")

    # --- nghiệp vụ ---
    def create_item(self, data: dict):
        config = load_config()
        type_key = data.get("type")
        if type_key not in config["types"]:
            return self.error(400, "Loại mục không hợp lệ")
        title = str(data.get("title", "")).strip()
        if not title:
            return self.error(400, "Thiếu tiêu đề")
        t = config["types"][type_key]
        with LOCK:
            item_id = next_id(config, type_key)
            meta = {"id": item_id, "type": type_key, "title": title, "status": t["statuses"][0]["key"]}
            for k, v in (data.get("meta") or {}).items():
                if k not in ("id", "type"):
                    meta[k] = v
            meta.setdefault("created_by", current_user())
            content = data.get("content") or t.get("template", "")
            folder = dir_for_type(type_key)
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{item_id}-{slugify(title)}.md"
            path.write_text(render_item_file(meta, content, []), encoding="utf-8")
        return self.send_json(parse_item_file(path), 201)

    def update_item(self, item_id: str, data: dict):
        with LOCK:
            p = find_item_path(item_id)
            if not p:
                return self.error(404, "Không tìm thấy mục")
            current = parse_item_file(p)
            if data.get("rev") and data["rev"] != current["rev"]:
                return self.send_json({"error": "Mục vừa được thay đổi ở nơi khác (VD sau khi đồng bộ). Tải lại rồi sửa tiếp.", "conflict": True, "current": current}, 409)
            meta = dict(current["meta"])
            for k, v in (data.get("meta") or {}).items():
                if k in ("id", "type"):
                    continue
                if v in (None, "", []):
                    meta.pop(k, None)
                else:
                    meta[k] = v
            content = data["content"] if "content" in data else current["content"]
            p.write_text(render_item_file(meta, content, current["comments"]), encoding="utf-8")
            return self.send_json(parse_item_file(p))

    def add_comment(self, item_id: str, data: dict):
        text = str(data.get("text", "")).strip()
        if not text:
            return self.error(400, "Bình luận trống")
        user = current_user()
        if not user:
            return self.error(400, "Chưa đặt tên người dùng")
        with LOCK:
            p = find_item_path(item_id)
            if not p:
                return self.error(404, "Không tìm thấy mục")
            raw = p.read_text(encoding="utf-8").replace("\r\n", "\n")
            if COMMENTS_HEADING not in raw:
                raw = raw.rstrip("\n") + "\n\n" + COMMENTS_HEADING + "\n" + COMMENTS_NOTE + "\n"
            # Chỉ append vào cuối file -> 2 người bình luận song song vẫn merge được (merge=union)
            raw = raw.rstrip("\n") + f"\n\n### {now_str()} · {user}\n{text}\n"
            p.write_text(raw, encoding="utf-8")
            return self.send_json(parse_item_file(p), 201)

    def edit_comment(self, item_id: str, index: int, data: dict, delete: bool = False):
        user = current_user()
        with LOCK:
            p = find_item_path(item_id)
            if not p:
                return self.error(404, "Không tìm thấy mục")
            current = parse_item_file(p)
            comments = current["comments"]
            if index >= len(comments):
                return self.error(404, "Không tìm thấy bình luận")
            c = comments[index]
            if data.get("time") and data["time"] != c["time"]:
                return self.error(409, "Bình luận đã thay đổi vị trí - tải lại trang")
            if c["author"] != user:
                return self.error(403, "Chỉ sửa/xóa được bình luận của chính mình")
            if delete:
                comments.pop(index)
            else:
                text = str(data.get("text", "")).strip()
                if not text:
                    return self.error(400, "Bình luận trống")
                c["text"] = text
            p.write_text(render_item_file(current["meta"], current["content"], comments), encoding="utf-8")
            return self.send_json(parse_item_file(p))

    def upload(self):
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        name = self.headers.get("X-Filename") or ""
        ext = mimetypes.guess_extension(ctype) or Path(unquote(name)).suffix or ".bin"
        if ext == ".jpe":
            ext = ".jpg"
        if not re.match(r"^\.[a-z0-9]{1,5}$", ext.lower()):
            return self.error(400, "Loại file không hợp lệ")
        data = self.read_body()
        if not data:
            return self.error(400, "File trống")
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        stem = slugify(Path(unquote(name)).stem)[:30] if name else "anh"
        fname = f"{datetime.now():%Y%m%d-%H%M%S}-{stem}-{secrets.token_hex(2)}{ext.lower()}"
        (ASSETS_DIR / fname).write_bytes(data)
        return self.send_json({"path": f"../assets/{fname}", "url": f"/assets/{fname}", "name": fname, "is_image": ctype.startswith("image/")}, 201)


def main():
    global PORT
    port_args = [a for a in sys.argv[1:] if a.isdigit()]
    port = PORT = int(port_args[0]) if port_args else PORT
    for d in (ITEMS_DIR, DOCS_DIR, ASSETS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, port), Handler)
    url = f"http://localhost:{port}"
    print(f"Quản lý đề tài đang chạy tại {url}  (Ctrl+C để dừng)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
