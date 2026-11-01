"""Sao lưu CSDL (T-28): pg_dump trong container PostgreSQL -> data/backups/<thời điểm>.sql.gz, giữ KEEP bản mới nhất.

  python -m storage.backup            # tạo bản sao lưu
  python -m storage.backup --list     # liệt kê
Khôi phục (ghi đè dữ liệu hiện có - cẩn thận):
  gunzip -c data/backups/<file>.sql.gz | docker exec -i sss_postgres psql -U <POSTGRES_USER> -d <POSTGRES_DB>
Bản sao lưu chứa dữ liệu thu thập (đã ẩn danh tác giả) và bảng người dùng (mật khẩu đã băm): lưu nơi có kiểm soát truy cập.
"""
from __future__ import annotations

import gzip
import subprocess
import sys
from datetime import datetime

from config.settings import settings
from pipeline import DATA_DIR

CONTAINER = "sss_postgres"
KEEP = 14
BACKUP_DIR = DATA_DIR / "backups"


def backup() -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    out = BACKUP_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{settings.postgres_db}.sql.gz"
    dump = subprocess.run(
        ["docker", "exec", CONTAINER, "pg_dump", "-U", settings.postgres_user, "-d", settings.postgres_db, "--no-owner", "--clean", "--if-exists"],
        capture_output=True, check=False,
    )
    if dump.returncode:
        raise SystemExit(f"pg_dump lỗi: {dump.stderr.decode(errors='replace')[:500]}")
    with gzip.open(out, "wb") as f:
        f.write(dump.stdout)
    for old in sorted(BACKUP_DIR.glob("*.sql.gz"))[:-KEEP]:  # xoay vòng
        old.unlink()
    return str(out)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--list" in sys.argv:
        for f in sorted(BACKUP_DIR.glob("*.sql.gz")):
            print(f.name, f"{f.stat().st_size / 1024:.0f} KB")
    else:
        print("Đã sao lưu:", backup())
