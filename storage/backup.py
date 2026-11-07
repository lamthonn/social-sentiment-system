"""Sao lưu CSDL (T-28): pg_dump trong container PostgreSQL -> data/backups/, giữ KEEP bản mới nhất.

Có DATA_ENCRYPTION_KEY -> bản sao lưu được mã hóa (<thời điểm>-<db>.sql.gz.enc, Fernet); chưa có -> .sql.gz dạng rõ.

  python -m storage.backup                          # tạo bản sao lưu
  python -m storage.backup --list                   # liệt kê
  python -m storage.backup --restore <file> --yes   # khôi phục (GHI ĐÈ dữ liệu hiện có), tự giải mã nếu cần
Bản sao lưu chứa dữ liệu thu thập (tác giả đã ẩn danh, nội dung gốc đã mã hóa nếu bật khóa), bảng người dùng
(mật khẩu đã băm) và nhật ký truy cập (có IP): lưu nơi có kiểm soát truy cập, và KHÔNG để cùng chỗ với khóa.
"""
from __future__ import annotations

import gzip
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config.settings import settings
from pipeline import DATA_DIR
from security.crypto import encryption_enabled

CONTAINER = "sss_postgres"
KEEP = 14
BACKUP_DIR = DATA_DIR / "backups"
PATTERNS = ("*.sql.gz", "*.sql.gz.enc")


def _fernet():
    from cryptography.fernet import Fernet

    return Fernet(settings.data_encryption_key.encode())


def _all_backups() -> list[Path]:
    return sorted((f for p in PATTERNS for f in BACKUP_DIR.glob(p)), key=lambda f: f.name)


def backup() -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dump = subprocess.run(
        ["docker", "exec", CONTAINER, "pg_dump", "-U", settings.postgres_user, "-d", settings.postgres_db, "--no-owner", "--clean", "--if-exists"],
        capture_output=True, check=False,
    )
    if dump.returncode:
        raise SystemExit(f"pg_dump lỗi: {dump.stderr.decode(errors='replace')[:500]}")
    data = gzip.compress(dump.stdout)
    name = f"{datetime.now():%Y%m%d-%H%M%S}-{settings.postgres_db}.sql.gz"
    if encryption_enabled():
        out = BACKUP_DIR / f"{name}.enc"
        out.write_bytes(_fernet().encrypt(data))
    else:
        out = BACKUP_DIR / name
        out.write_bytes(data)
    for old in _all_backups()[:-KEEP]:  # xoay vòng
        old.unlink()
    return str(out)


def restore(path: Path) -> None:
    data = path.read_bytes()
    if path.suffix == ".enc":
        if not encryption_enabled():
            raise SystemExit("Bản sao lưu đã mã hóa nhưng chưa đặt DATA_ENCRYPTION_KEY trong .env")
        from cryptography.fernet import InvalidToken

        try:
            data = _fernet().decrypt(data)
        except InvalidToken:
            raise SystemExit("Không giải mã được: DATA_ENCRYPTION_KEY sai hoặc tệp đã bị sửa") from None
    sql = gzip.decompress(data)
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-q", "-v", "ON_ERROR_STOP=1", "-U", settings.postgres_user,
                        "-d", settings.postgres_db], input=sql, capture_output=True, check=False)
    if r.returncode:
        raise SystemExit(f"psql lỗi: {r.stderr.decode(errors='replace')[:500]}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--list" in sys.argv:
        for f in _all_backups():
            print(f.name, f"{f.stat().st_size / 1024:.0f} KB", "(mã hóa)" if f.suffix == ".enc" else "(dạng rõ)")
    elif "--restore" in sys.argv:
        target = Path(sys.argv[sys.argv.index("--restore") + 1])
        if "--yes" not in sys.argv:
            raise SystemExit(f"Khôi phục sẽ GHI ĐÈ toàn bộ CSDL {settings.postgres_db} bằng {target.name}. Thêm --yes để xác nhận.")
        restore(target)
        print("Đã khôi phục từ", target)
    else:
        print("Đã sao lưu:", backup())
