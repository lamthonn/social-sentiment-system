---
id: T-015
type: task
title: Ẩn danh định danh tác giả khi thu thập
status: done
owner: Lâm
priority: Trung bình
module: An ninh an toàn
ch: [CH4]
created_by: Claude (khởi tạo)
---

## Mô tả
SHA-256 + salt bí mật, gọi ngay trong pipeline trước khi ghi DB.

## Việc cần làm
- [x] Hàm `hash_identifier`
- [x] Áp dụng trong `_ingest`
- [x] Không lưu displayName/channelId gốc

## Kết quả / Bằng chứng
`security/anonymize.py`

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
