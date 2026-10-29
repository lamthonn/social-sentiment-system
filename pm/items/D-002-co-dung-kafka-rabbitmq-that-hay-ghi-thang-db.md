---
id: D-002
type: decision
title: Có dùng Kafka/RabbitMQ thật hay ghi thẳng DB?
status: open
owner: Lâm
priority: Cao
module: Lưu trữ
ch: [CH3]
links: [T-020, T-007]
created_by: Claude (khởi tạo)
---

## Bối cảnh
Sơ đồ kiến trúc thuyết minh có Kafka/RabbitMQ; code hiện ghi thẳng PostgreSQL. Quy mô thử nghiệm vài nghìn–vài chục nghìn bản ghi/ngày.

## Phương án
### A. Kafka
Đúng sơ đồ, nặng vận hành (broker, Zookeeper/KRaft).

### B. RabbitMQ
Nhẹ hơn, đủ cho quy mô đề tài.

### C. Hàng đợi bằng bảng PostgreSQL / Redis
Đơn giản nhất, ít thành phần.

### D. Không dùng, ghi rõ ngoài phạm vi

## Đề xuất
**Đề xuất (Claude):** B (RabbitMQ) — vẫn khớp thuyết minh, đủ để đo throughput trả lời CH3, chi phí vận hành thấp. Nếu thiếu thời gian, C và giải thích trong báo cáo.

## Kết luận

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
