---
id: T-009
type: task
title: Thiết kế CSDL mở rộng (metadata, hashtag, nhãn, xu hướng, người dùng)
status: todo
owner: Nam
priority: Cao
module: Lưu trữ
ch: [CH3]
links: [DOC-003]
created_by: Claude (khởi tạo)
---

## Mô tả
Bổ sung các bảng/cột còn thiếu so với nghiệp vụ (xem DOC-003 phần 'Thiếu so với nghiệp vụ'). Lưu ý `init_db()` không sửa bảng cũ → cần migration (Alembic) hoặc script SQL.

## Việc cần làm
- [ ] Cột `metadata` JSONB cho thuộc tính riêng từng nền tảng
- [ ] Bảng/ cột hashtag
- [ ] Quan hệ bình luận cha–con
- [ ] Bảng nhãn thủ công (gold labels)
- [ ] Bảng chủ đề & chỉ số xu hướng
- [ ] Bảng users/roles & audit_logs
- [ ] Bảng crawl_runs (lượt chạy)
- [ ] Chọn cách migration (Alembic?)

## Kết quả / Bằng chứng

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
