---
id: T-013
type: task
title: Scheduler thu thập định kỳ đọc cấu hình từ DB
status: done
owner: Lâm
priority: Trung bình
module: Thu thập
ch: [CH3]
created_by: Claude (khởi tạo)
---

## Mô tả
APScheduler, chạy ngay khi khởi động rồi lặp theo `COLLECTOR_POLL_INTERVAL_MINUTES`.

## Việc cần làm
- [x] Bảng search_queries, tracked_videos
- [x] Đọc lại cấu hình mỗi lượt
- [x] Lỗi 1 video không làm hỏng cả lượt

## Kết quả / Bằng chứng
`collector/scheduler.py`

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
