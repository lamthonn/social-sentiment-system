"""T-28: mã hóa dữ liệu khi lưu (encryption at rest) ở tầng ứng dụng.

- Cột nhạy cảm (raw_posts.content - nội dung gốc, chưa che SĐT/email/@tên) dùng kiểu EncryptedText:
  ORM tự mã hóa khi ghi và giải mã khi đọc, code thu thập / pipeline không phải đổi.
- Thuật toán: Fernet (AES-128-CBC + HMAC-SHA256, có xác thực - sửa bản mã sẽ bị phát hiện).
- Khóa: DATA_ENCRYPTION_KEY trong .env. Lộ CSDL hay bản sao lưu mà không có .env thì không đọc được nội dung.
  MẤT KHÓA = MẤT DỮ LIỆU: cất một bản khóa ở nơi riêng, không để cùng chỗ với bản sao lưu.
- Bản mã có tiền tố "enc1:"; giá trị không có tiền tố là dữ liệu cũ chưa mã hóa, vẫn đọc được bình thường.
  Chưa đặt khóa -> lưu dạng rõ (và bước monitor cảnh báo) để không làm hỏng máy chưa cấu hình.

  python -m security.crypto genkey            # sinh khóa mới, dán vào .env: DATA_ENCRYPTION_KEY=...
  python -m security.crypto status            # số dòng đã / chưa mã hóa
  python -m security.crypto encrypt-existing  # mã hóa các dòng cũ còn dạng rõ
"""
from __future__ import annotations

import logging
import sys
from functools import lru_cache

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from config.settings import settings

logger = logging.getLogger(__name__)
PREFIX = "enc1:"


@lru_cache(maxsize=1)
def _fernet():
    if not settings.data_encryption_key:
        logger.warning("Chưa đặt DATA_ENCRYPTION_KEY - nội dung gốc được lưu dạng rõ (xem security/crypto.py)")
        return None
    from cryptography.fernet import Fernet

    try:
        return Fernet(settings.data_encryption_key.encode())
    except ValueError as e:
        raise RuntimeError("DATA_ENCRYPTION_KEY không hợp lệ - sinh khóa bằng: python -m security.crypto genkey") from e


def encryption_enabled() -> bool:
    return _fernet() is not None


def encrypt(value: str) -> str:
    f = _fernet()
    if f is None or value.startswith(PREFIX):
        return value
    return PREFIX + f.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: str) -> str:
    if not value.startswith(PREFIX):
        return value  # dữ liệu cũ chưa mã hóa
    f = _fernet()
    if f is None:
        raise RuntimeError("Dữ liệu đã mã hóa nhưng chưa đặt DATA_ENCRYPTION_KEY trong .env")
    from cryptography.fernet import InvalidToken

    try:
        return f.decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError("Không giải mã được: DATA_ENCRYPTION_KEY sai hoặc dữ liệu đã bị sửa") from e


class EncryptedText(TypeDecorator):
    """Text được mã hóa trong CSDL. Không tìm kiếm / so sánh được bằng SQL (LIKE, =) trên cột này."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else encrypt(value)

    def process_result_value(self, value, dialect):
        return None if value is None else decrypt(value)


def _status(session) -> tuple[int, int]:
    from sqlalchemy import text

    total = session.execute(text("SELECT count(*) FROM raw_posts")).scalar() or 0
    enc = session.execute(text("SELECT count(*) FROM raw_posts WHERE content LIKE 'enc1:%'")).scalar() or 0
    return total, enc


def encrypt_existing(batch: int = 500) -> int:
    """Mã hóa các dòng raw_posts còn dạng rõ (đọc/ghi bằng SQL thô để không qua EncryptedText)."""
    from sqlalchemy import text

    from storage.database import SessionLocal

    if not encryption_enabled():
        raise SystemExit("Chưa đặt DATA_ENCRYPTION_KEY trong .env")
    done = 0
    with SessionLocal() as s:
        while True:
            rows = s.execute(text("SELECT id, content FROM raw_posts WHERE content NOT LIKE 'enc1:%' ORDER BY id LIMIT :n"),
                             {"n": batch}).all()
            if not rows:
                break
            for rid, content in rows:
                s.execute(text("UPDATE raw_posts SET content = :c WHERE id = :i"), {"c": encrypt(content), "i": rid})
            s.commit()
            done += len(rows)
    return done


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "genkey":
        from cryptography.fernet import Fernet

        print(Fernet.generate_key().decode())
    elif cmd == "encrypt-existing":
        print(f"Đã mã hóa {encrypt_existing()} dòng")
    elif cmd == "status":
        from storage.database import SessionLocal

        with SessionLocal() as s:
            total, enc = _status(s)
        print(f"Khóa: {'đã đặt' if encryption_enabled() else 'CHƯA ĐẶT'} | raw_posts: {enc}/{total} dòng đã mã hóa")
    else:
        raise SystemExit(__doc__)
