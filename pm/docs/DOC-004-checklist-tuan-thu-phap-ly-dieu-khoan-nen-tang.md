---
id: DOC-004
type: doc
title: Checklist tuân thủ pháp lý & điều khoản nền tảng
status: draft
owner: Lâm
created_by: Claude (khởi tạo)
---

## Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 (hiệu lực 01/01/2026)
- [x] Không lưu định danh gốc tác giả; băm SHA-256 + salt ngay khi thu thập (BR-01)
- [x] Chỉ thu thập nội dung công khai
- [ ] Che/loại PII xuất hiện **trong nội dung** bình luận (SĐT, email, tên riêng, địa chỉ) trước khi đưa vào dataset hoặc công bố (R-005)
- [ ] Mô tả rõ mục đích xử lý dữ liệu (nghiên cứu khoa học) trong báo cáo & phụ lục
- [ ] Chính sách thời gian lưu trữ & xóa dữ liệu thô (D-014)
- [ ] Phân quyền truy cập dữ liệu thô (chỉ Admin/Analyst) (T-038)
- [ ] Mã hóa kết nối & sao lưu có kiểm soát (T-040)
- [ ] Nhật ký truy cập dữ liệu (T-041)
- [ ] Xác định cảm xúc/quan điểm có thuộc **dữ liệu cá nhân nhạy cảm** không và biện pháp tương ứng (Q-029)
- [ ] Không công bố bộ dữ liệu kèm nội dung có thể truy ngược tác giả

## YouTube API Services Terms
- [x] Dùng API key chính thức, giới hạn key cho YouTube Data API v3
- [ ] Kiểm tra quy định lưu trữ/làm mới dữ liệu API (thời hạn lưu dữ liệu lấy từ API) và ghi vào báo cáo
- [ ] Không vượt quota; không tạo nhiều project để lách quota

## TikTok Research API Terms
- [ ] Kiểm tra điều kiện được cấp quyền (đối tượng, khu vực) — R-002
- [ ] Tuân thủ giới hạn sử dụng, mục đích phi thương mại

## Căn cứ pháp lý cần thống nhất trong tài liệu
- [ ] `docs/business_analysis_and_survey_framework.md` đang dẫn Nghị định 13/2023/NĐ-CP, thuyết minh dẫn Luật 91/2025/QH15 → thống nhất (Q-029)

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
