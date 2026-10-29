"""Công cụ quản lý đề tài - toàn bộ dữ liệu nằm trong 1 file: pm/QUAN_LY_DE_TAI.md

Chạy:  python pm/server.py   -> mở http://localhost:8765   (Python 3.10+, không cần cài gì)

File .md có 3 mục:
  ## 1. Tổng quan      -> các tiểu mục "### Tiêu đề" + nội dung markdown tự do
  ## 2. Việc cần làm   -> bảng | Mã | Việc | Trạng thái | Người làm | Ghi chú |
  ## 3. Mô hình        -> mỗi mô hình 1 tiểu mục "### M-01 · Tên", các dòng "- Trường: giá trị",
                          dòng trống, rồi phần kết quả & nhận xét tự do
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
from urllib.parse import unquote, urlparse

PM_DIR = Path(__file__).resolve().parent
DOC_PATH = PM_DIR / "QUAN_LY_DE_TAI.md"
ASSETS_DIR = PM_DIR / "assets"
STATIC = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
HOST, PORT = "127.0.0.1", 8765
MAX_UPLOAD = 15 * 1024 * 1024
LOCK = threading.Lock()

MEMBERS = ["Nam", "Lâm"]
TASK_STATUSES = ["Chưa làm", "Đang làm", "Xong", "Tạm dừng"]
MODEL_STATUSES = ["Ứng viên", "Đang thử", "Đã chọn", "Loại"]
MODEL_FIELDS = ["Bài toán", "Nhóm", "Trạng thái", "Dataset", "Accuracy", "Precision", "Recall", "Macro-F1", "Mô tả"]
TITLE = "# Quản lý đề tài NCKH"
NOTE = "<!-- Sửa qua giao diện: python pm/server.py (http://localhost:8765). Sửa tay được nhưng giữ đúng định dạng 3 mục. -->"
H_OVERVIEW, H_TASKS, H_MODELS = "## 1. Tổng quan", "## 2. Việc cần làm", "## 3. Mô hình"


# ===== đọc / ghi file .md =====


def split_sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## (\d)\.[^\n]*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def split_subsections(block: str) -> list[tuple[str, str]]:
    chunks = re.split(r"^### +(.+?)\s*$", block, flags=re.M)
    return [(chunks[i].strip(), chunks[i + 1].strip("\n")) for i in range(1, len(chunks) - 1, 2)]


def parse_row(line: str) -> list[str]:
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def parse_doc(text: str) -> dict:
    text = text.replace("\r\n", "\n")
    sec = split_sections(text)
    warnings: list[str] = []

    overview = [{"title": t, "body": b.strip()} for t, b in split_subsections(sec.get("1", ""))]

    tasks: list[dict] = []
    seen: dict[str, dict] = {}
    for line in sec.get("2", "").split("\n"):
        if not line.strip().startswith("|") or re.match(r"^\s*\|[\s:|-]+\|\s*$", line):
            continue
        cells = parse_row(line) + [""] * 5
        if cells[0] in ("Mã", ""):
            continue
        task = {"id": cells[0], "title": cells[1], "status": cells[2] or TASK_STATUSES[0], "owner": cells[3], "note": cells[4]}
        old = seen.get(task["id"])
        if old and old["title"] == task["title"]:
            # 2 người cùng sửa 1 việc rồi git merge -> giữ dòng sau, báo để kiểm tra
            warnings.append(f"Việc {task['id']} có 2 dòng (2 người cùng sửa) - đang lấy dòng sau, kiểm tra lại trạng thái/ghi chú.")
            old.update(task)
            continue
        if old:  # 2 người cùng thêm việc mới trùng mã -> đổi mã việc sau
            task["id"] = next_id(tasks, "T")
            warnings.append(f"Mã trùng - đã đổi '{cells[1]}' sang {task['id']}.")
        seen[task["id"]] = task
        tasks.append(task)

    models: list[dict] = []
    for head, body in split_subsections(sec.get("3", "")):
        m = re.match(r"^([A-Z]+-\d+)\s*[·\-]\s*(.+)$", head)
        model = {"id": m.group(1) if m else next_id(models, "M"), "name": m.group(2).strip() if m else head, "fields": {}, "notes": ""}
        lines = body.strip("\n").split("\n")
        i = 0
        while i < len(lines) and (fm := re.match(r"^- ([^:]+):\s?(.*)$", lines[i])) and fm.group(1).strip() in MODEL_FIELDS:
            model["fields"][fm.group(1).strip()] = fm.group(2).strip()
            i += 1
        model["notes"] = "\n".join(lines[i:]).strip()
        if any(x["id"] == model["id"] for x in models):
            model["id"] = next_id(models, "M")
        models.append(model)

    return {
        "overview": overview, "tasks": tasks, "models": models, "warnings": warnings,
        "rev": hashlib.sha1(text.encode("utf-8")).hexdigest()[:12],
        "options": {"members": MEMBERS, "task_statuses": TASK_STATUSES, "model_statuses": MODEL_STATUSES, "model_fields": MODEL_FIELDS},
    }


def next_id(items: list[dict], prefix: str) -> str:
    nums = [int(m.group(1)) for x in items if (m := re.match(rf"^{prefix}-(\d+)$", x.get("id", "")))]
    return f"{prefix}-{(max(nums) + 1) if nums else 1:02d}"


def cell(value) -> str:
    return str(value or "").replace("\r", "").replace("\n", " ").replace("|", "\\|").strip()


def render_doc(data: dict) -> str:
    out = [TITLE, "", NOTE, "", H_OVERVIEW, ""]
    for sub in data.get("overview", []):
        title = cell(sub.get("title")).replace("\\|", "|") or "Không tên"
        body = re.sub(r"^(#{1,3}) ", "#### ", str(sub.get("body", "")).strip(), flags=re.M)  # không phá cấu trúc mục
        out += [f"### {title}", "", body, ""] if body else [f"### {title}", ""]

    out += [H_TASKS, "", "| Mã | Việc | Trạng thái | Người làm | Ghi chú |", "|---|---|---|---|---|"]
    tasks = data.get("tasks", [])
    for t in tasks:
        tid = t.get("id") or next_id(tasks, "T")
        t["id"] = tid
        out.append(f"| {tid} | {cell(t.get('title'))} | {cell(t.get('status')) or TASK_STATUSES[0]} | {cell(t.get('owner'))} | {cell(t.get('note'))} |")
    out.append("")

    out += [H_MODELS, ""]
    models = data.get("models", [])
    for m in models:
        mid = m.get("id") or next_id(models, "M")
        m["id"] = mid
        out.append(f"### {mid} · {cell(m.get('name')).replace(chr(92) + '|', '|')}")
        fields = m.get("fields", {})
        out += [f"- {k}: {cell(fields.get(k)).replace(chr(92) + '|', '|')}" for k in MODEL_FIELDS]
        notes = re.sub(r"^(#{1,3}) ", "#### ", str(m.get("notes", "")).strip(), flags=re.M)
        out += ["", notes, ""] if notes else [""]
    return "\n".join(out).rstrip() + "\n"


def read_doc() -> dict:
    if not DOC_PATH.exists():
        DOC_PATH.write_text(render_doc({}), encoding="utf-8")
    return parse_doc(DOC_PATH.read_text(encoding="utf-8"))


# ===== git =====


def git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=PM_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def git_status(fetch: bool) -> dict:
    if fetch:
        git("fetch", "--quiet", timeout=30)
    changed = git("status", "--porcelain", "--untracked-files=all", "--", ".").stdout.splitlines()
    res = {"local_changes": len(changed), "ahead": 0, "behind": 0}
    counts = git("rev-list", "--left-right", "--count", "HEAD...@{u}")
    if counts.returncode == 0:
        res["ahead"], res["behind"] = map(int, counts.stdout.split())
    return res


def git_sync() -> dict:
    log: list[str] = []

    def step(*args: str, timeout: int = 180) -> subprocess.CompletedProcess:
        r = git(*args, timeout=timeout)
        log.append(f"$ git {' '.join(args)}\n{(r.stdout + r.stderr).strip()}")
        return r

    step("add", "-A", "--", ".")
    if git("diff", "--cached", "--name-only", "--", ".").stdout.strip():
        if step("commit", "-m", f"pm: cập nhật quản lý đề tài ({datetime.now():%Y-%m-%d %H:%M})", "--", ".").returncode:
            return {"ok": False, "error": "Commit thất bại.", "log": log}
    r = step("pull", "--rebase", "--autostash")
    if r.returncode:
        step("rebase", "--abort")
        return {"ok": False, "error": "Lấy thay đổi về thất bại (mạng hoặc xung đột) - đã hoàn tác, dữ liệu trên máy vẫn nguyên.", "log": log}
    if git_status(False)["ahead"] and step("push").returncode:
        return {"ok": False, "error": "Đẩy lên thất bại - kiểm tra đăng nhập GitHub / quyền ghi.", "log": log}
    return {"ok": True, "log": log}


# ===== HTTP =====


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path):
        if not path.is_file():
            return self.send_json({"error": "Không tìm thấy"}, 404)
        data = path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") or "javascript" in ctype else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            raise ValueError("File quá lớn (tối đa 15MB)")
        return self.rfile.read(n) if n else b""

    def safe(self, fn):
        try:
            fn()
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:  # noqa: BLE001
            self.send_json({"error": f"Lỗi server: {exc}"}, 500)

    def origin_ok(self) -> bool:  # chặn trang web lạ gửi lệnh ghi tới server local
        o = self.headers.get("Origin")
        return o is None or o in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}")

    def do_GET(self):
        self.safe(self._get)

    def do_PUT(self):
        self.safe(self._write)

    def do_POST(self):
        self.safe(self._write)

    def _get(self):
        url = urlparse(self.path)
        path = unquote(url.path)
        if path in STATIC:
            return self.send_file(PM_DIR / STATIC[path])
        if path.startswith("/assets/"):
            target = (ASSETS_DIR / path[8:]).resolve()
            if ASSETS_DIR.resolve() not in target.parents:
                return self.send_json({"error": "Đường dẫn không hợp lệ"}, 403)
            return self.send_file(target)
        if path == "/api/doc":
            with LOCK:
                return self.send_json(read_doc())
        if path == "/api/git/status":
            return self.send_json(git_status("fetch=1" in url.query))
        self.send_json({"error": "Không tìm thấy"}, 404)

    def _write(self):
        if not self.origin_ok():
            return self.send_json({"error": "Origin không hợp lệ"}, 403)
        path = urlparse(self.path).path
        if path == "/api/doc" and self.command == "PUT":
            try:
                data = json.loads(self.body().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"Dữ liệu không hợp lệ: {exc}") from exc
            with LOCK:
                current = read_doc()
                if data.get("rev") != current["rev"]:
                    return self.send_json({"error": "File vừa được thay đổi ở nơi khác (VD sau khi đồng bộ) - đã tải lại bản mới.", "current": current}, 409)
                DOC_PATH.write_text(render_doc(data), encoding="utf-8")
                return self.send_json(read_doc())
        if path == "/api/upload":
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
            ext = (mimetypes.guess_extension(ctype) or Path(unquote(self.headers.get("X-Filename") or "")).suffix or ".bin").lower()
            ext = ".jpg" if ext == ".jpe" else ext
            if not re.match(r"^\.[a-z0-9]{1,5}$", ext):
                raise ValueError("Loại file không hợp lệ")
            data = self.body()
            if not data:
                raise ValueError("File trống")
            ASSETS_DIR.mkdir(exist_ok=True)
            name = f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}{ext}"
            (ASSETS_DIR / name).write_bytes(data)
            return self.send_json({"path": f"assets/{name}", "is_image": ctype.startswith("image/")}, 201)
        if path == "/api/git/sync":
            with LOCK:
                return self.send_json(git_sync())
        self.send_json({"error": "Không tìm thấy"}, 404)


def main():
    global PORT
    ports = [a for a in sys.argv[1:] if a.isdigit()]
    PORT = int(ports[0]) if ports else PORT
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Quản lý đề tài: {url}  (Ctrl+C để dừng)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
