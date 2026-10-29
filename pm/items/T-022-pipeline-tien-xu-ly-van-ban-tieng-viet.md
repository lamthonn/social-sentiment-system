---
id: T-022
type: task
title: Pipeline tiền xử lý văn bản tiếng Việt
status: todo
priority: Cao
module: Tiền xử lý & Dataset
ch: [CH1]
links: [MODEL-013, R-005, FR-007]
created_by: Claude (khởi tạo)
---

## Mô tả
Module `preprocessing/`: chuẩn hóa Unicode (NFC), chữ thường, URL/mention/hashtag, emoji, ký tự đặc biệt, teencode, tách từ (bắt buộc cho PhoBERT), phát hiện ngôn ngữ, **che PII trong nội dung**.

## Việc cần làm
- [ ] Chuẩn hóa Unicode & dấu thanh
- [ ] Xử lý URL, mention, hashtag, emoji
- [ ] Chuẩn hóa teencode/viết tắt (T-023)
- [ ] Tách từ (MODEL-013)
- [ ] Phát hiện ngôn ngữ, loại bản ghi không phải tiếng Việt
- [ ] Che SĐT/email/tên riêng (R-005)
- [ ] Unit test với mẫu bình luận thật

## Kết quả / Bằng chứng

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
