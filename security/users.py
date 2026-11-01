"""Quản lý tài khoản webapp từ dòng lệnh.

  python -m security.users add nam --role admin      # hỏi mật khẩu (không hiện khi gõ)
  python -m security.users add lam --role admin --random   # sinh mật khẩu ngẫu nhiên, in ra 1 lần
  python -m security.users list
  python -m security.users set-password nam
  python -m security.users disable lam
"""
from __future__ import annotations

import argparse
import getpass
import secrets
import sys

from sqlalchemy import select

from security.auth import ROLES, hash_password, validate_password_strength
from storage.database import SessionLocal
from storage.models import User


def _ask_password() -> str:
    pw = getpass.getpass("Mật khẩu: ")
    if pw != getpass.getpass("Nhập lại: "):
        sys.exit("Hai lần nhập không khớp")
    validate_password_strength(pw)
    return pw


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="security.users")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("username")
    a.add_argument("--role", choices=ROLES, default="viewer")
    a.add_argument("--random", action="store_true", help="sinh mật khẩu ngẫu nhiên và in ra một lần")
    sub.add_parser("list")
    for name in ("set-password", "disable", "enable"):
        sub.add_parser(name).add_argument("username")
    args = ap.parse_args()

    with SessionLocal() as s:
        if args.cmd == "list":
            for u in s.scalars(select(User).order_by(User.id)):
                print(f"{u.id:>3}  {u.username:<16} {u.role:<8} {'hoạt động' if u.is_active else 'đã khóa'}")
            return
        user = s.scalars(select(User).where(User.username == args.username)).first()
        if args.cmd == "add":
            if user:
                sys.exit(f"Đã có tài khoản {args.username}")
            pw = secrets.token_urlsafe(12) + "1a" if args.random else _ask_password()
            s.add(User(username=args.username, password_hash=hash_password(pw), role=args.role))
            s.commit()
            print(f"Đã tạo {args.username} ({args.role})" + (f" - mật khẩu: {pw}  (đổi sau khi đăng nhập)" if args.random else ""))
            return
        if not user:
            sys.exit(f"Không có tài khoản {args.username}")
        if args.cmd == "set-password":
            user.password_hash = hash_password(_ask_password())
        else:
            user.is_active = args.cmd == "enable"
        s.commit()
        print("Đã cập nhật")


if __name__ == "__main__":
    main()
