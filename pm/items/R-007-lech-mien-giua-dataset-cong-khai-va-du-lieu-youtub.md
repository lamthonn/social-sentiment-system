---
id: R-007
type: risk
title: Lệch miền giữa dataset công khai và dữ liệu YouTube
status: open
likelihood: Trung bình
impact: Cao
links: [T-026, MODEL-006]
created_by: Claude (khởi tạo)
---

## Mô tả
Lệch miền giữa dataset công khai và dữ liệu YouTube.

## Ảnh hưởng
Mô hình tốt trên UIT nhưng kém trên dữ liệu thật.

## Cách giảm thiểu
- [ ] Có tập test gold từ dữ liệu YouTube
- [ ] Thử ViSoBERT (pretrain MXH)
- [ ] Fine-tune bổ sung trên dữ liệu tự gán nhãn

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
