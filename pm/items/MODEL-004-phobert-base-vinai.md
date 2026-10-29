---
id: MODEL-004
type: model
title: PhoBERT-base (VinAI)
status: candidate
task_kind: Cảm xúc
family: Transformer
resource: GPU ~8–16GB khi fine-tune
license: Cần kiểm tra
created_by: Claude (khởi tạo)
---

## Mô tả
Mô hình ngôn ngữ tiền huấn luyện nền tảng cho tiếng Việt [4]. **Yêu cầu đầu vào đã tách từ** (VnCoreNLP RDRSegmenter).

## Ưu điểm
- Mạnh trên nhiều tác vụ tiếng Việt
- Nhiều công trình so sánh

## Nhược điểm
- Pretrain trên văn bản chuẩn (Wikipedia, báo) — kém hơn với teencode
- Giới hạn 256 token

## Yêu cầu tài nguyên
GPU ~8–16GB khi fine-tune

## Kết quả thực nghiệm
Chưa có — ghi vào các mục E-* rồi cập nhật trường 'Kết quả tốt nhất'.

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
