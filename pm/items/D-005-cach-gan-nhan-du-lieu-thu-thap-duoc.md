---
id: D-005
type: decision
title: Cách gán nhãn dữ liệu thu thập được
status: open
owner: Nam
priority: Cao
module: Tiền xử lý & Dataset
ch: [CH1]
links: [T-026]
created_by: Claude (khởi tạo)
---

## Bối cảnh
Cần tập test gold standard trên dữ liệu YouTube thật để chứng minh mô hình hoạt động trên dữ liệu đề tài thu thập (không chỉ UIT).

## Phương án
### A. 2 người tự gán ~1.000–2.000 mẫu, gán đôi 20% để đo Kappa

### B. LLM gán nhãn sơ bộ, người duyệt lại
Nhanh hơn; cần LLM chạy local nếu muốn tránh gửi dữ liệu ra ngoài.

### C. Chỉ dùng dataset công khai, không gán nhãn

## Đề xuất
**Đề xuất (Claude):** A cho tập test (~1.000 mẫu), có thể kết hợp B cho tập train bổ sung. C làm yếu luận điểm 'hệ thống end-to-end'.

## Kết luận

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
