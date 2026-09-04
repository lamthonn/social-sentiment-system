"""CLI cho collector.

  python -m collector run --platform youtube --video <VIDEO_ID> [--video <ID2> ...] [--max-pages N]
  python -m collector run --platform tiktok --video <VIDEO_ID>
  python -m collector search --query "<từ khóa>" [--max-videos N] [--days N]
  python -m collector schedule
"""
from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO)

# Đảm bảo in được tiếng Việt (dấu) bất kể terminal đang dùng encoding gì
# (VD: Windows console mặc định cp1252, không phải UTF-8).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(prog="collector")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Thu thập 1 lần rồi thoát")
    run_parser.add_argument(
        "--platform", choices=["youtube", "tiktok"], default="youtube",
        help="Nền tảng thu thập (mặc định: youtube)",
    )
    run_parser.add_argument(
        "--video", action="append", required=True,
        help="Video ID (hoặc URL đầy đủ, lặp lại flag để nhiều video, VD: --video abc --video xyz)",
    )
    run_parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Giới hạn số trang comment/video (mặc định: lấy hết, mỗi trang tối đa 100 comment)",
    )
    run_parser.add_argument(
        "--category", default=None,
        help="Gắn nhãn chủ đề cho dữ liệu thu thập lần này (tùy chọn, VD: \"giá vàng\") - dùng để lọc/đánh giá sau này",
    )

    search_parser = sub.add_parser(
        "search", help="Tìm video YouTube mới theo từ khóa rồi thu thập comment luôn (không cần biết trước video ID)"
    )
    search_parser.add_argument("--query", required=True, help="Từ khóa tìm kiếm (VD: \"giá vàng\")")
    search_parser.add_argument(
        "--max-videos", type=int, default=10,
        help="Số video tối đa lấy về (mặc định 10 - lưu ý: search chỉ tốn 100 unit quota/lần bất kể số này)",
    )
    search_parser.add_argument(
        "--days", type=int, default=7,
        help="Chỉ lấy video đăng trong N ngày gần đây (mặc định 7)",
    )
    search_parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Giới hạn số trang comment/video (mặc định: lấy hết)",
    )

    sub.add_parser(
        "schedule",
        help="Chạy lập lịch định kỳ theo cấu hình trong DB (tab \"Cấu hình thu thập\" trên frontend)",
    )

    args = parser.parse_args()

    if args.command == "run":
        from collector.pipeline import collect_many

        if args.platform == "youtube":
            from collector.youtube_client import extract_video_id
        else:
            from collector.tiktok_client import extract_video_id

        videos = [(extract_video_id(v), args.category) for v in args.video]
        results = collect_many(args.platform, videos, max_pages=args.max_pages)
        for video_id, count in results.items():
            print(f"[{args.platform}] {video_id}: {count} comment mới")

    elif args.command == "search":
        from collector.pipeline import discover_and_collect_youtube

        results = discover_and_collect_youtube(
            args.query, max_videos=args.max_videos, published_within_days=args.days, max_pages=args.max_pages,
        )
        if not results:
            print(f"Không tìm thấy video nào khớp từ khóa '{args.query}' trong {args.days} ngày gần đây")
        for video_id, info in results.items():
            print(f"{video_id} - {info['title']}: {info['inserted']} comment mới")

    elif args.command == "schedule":
        from collector.scheduler import run_forever

        run_forever()


if __name__ == "__main__":
    main()
