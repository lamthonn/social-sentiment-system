---
id: T-011
type: task
title: Collector YouTube theo video ID
status: done
owner: Lâm
priority: Trung bình
module: Thu thập
ch: [CH3]
created_by: Claude (khởi tạo)
---

## Mô tả
Lấy bình luận top-level qua `commentThreads.list`, phân trang, ghi `raw_posts`.

## Việc cần làm
- [x] Client YouTube Data API (httpx)
- [x] Trích video ID từ mọi dạng URL
- [x] CLI `python -m collector run`

## Kết quả / Bằng chứng
`collector/youtube_client.py`, `collector/pipeline.py`

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
