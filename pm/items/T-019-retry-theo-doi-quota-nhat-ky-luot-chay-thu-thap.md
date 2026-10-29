---
id: T-019
type: task
title: Retry, theo dõi quota & nhật ký lượt chạy thu thập
status: todo
owner: Lâm
priority: Cao
module: Thu thập
ch: [CH3]
links: [FR-014, R-001]
created_by: Claude (khởi tạo)
---

## Mô tả
Ổn định khi vận hành liên tục: retry có backoff khi lỗi mạng/429, ước tính quota đã dùng, bảng crawl_runs, hiển thị trên UI.

## Việc cần làm
- [ ] Retry + backoff cho httpx
- [ ] Đếm unit quota theo ngày
- [ ] Bảng crawl_runs (bắt đầu, kết thúc, số bản ghi, lỗi)
- [ ] Trang theo dõi trên frontend

## Kết quả / Bằng chứng

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
