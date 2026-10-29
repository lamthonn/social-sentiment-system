---
id: DOC-001
type: doc
title: Tổng quan đề tài & cách dùng công cụ
status: draft
owner: Nam
created_by: Claude (khởi tạo)
---

## Thông tin chung
| Mục | Nội dung |
|---|---|
| Tên đề tài | Nghiên cứu các kỹ thuật máy học hiện đại kết hợp đảm bảo an ninh an toàn ứng dụng trong phát triển thử nghiệm hệ thống thông tin hỗ trợ thu thập, lưu trữ tự động dữ liệu mạng xã hội để nhận diện và phân loại cảm xúc và xu hướng của người dùng |
| Cấp | Đề tài KH-CN cấp trường (dành cho người học) — Trường ĐH Điện lực, Khoa Điện toán và Công nghệ số năng lượng |
| Mã số | ĐTNH…/2026 (chưa có) |
| Thời gian (theo thuyết minh) | 09/2026 → 02/2027 (6 tháng) |
| Chủ nhiệm (theo thuyết minh) | Nguyễn Viết Doanh |
| GV hướng dẫn | ThS. Lê Thanh Trà |
| Thành viên (theo thuyết minh) | Vũ Hải Nam, Vũ Vương Lâm, Nguyễn Viết Doanh |
| Nhóm thực hiện thực tế trên repo | Nam, Lâm (xem D-010 về phân công) |
| Kinh phí | 5.000.000 đ (xem TM-001: số và chữ đang lệch) |
| File thuyết minh | `TM_final.docx` ở gốc repo |

## Mục tiêu tổng quát
Nghiên cứu, làm chủ và ứng dụng các kỹ thuật máy học hiện đại kết hợp giải pháp an ninh, an toàn thông tin để phát triển thử nghiệm một hệ thống **thu thập, lưu trữ tự động dữ liệu mạng xã hội** và **nhận diện, phân loại cảm xúc + phát hiện, phân loại xu hướng** người dùng (tập trung tiếng Việt), đồng thời **tuân thủ Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15**.

## Câu hỏi nghiên cứu
| Mã | Câu hỏi | Mục tiêu cụ thể |
|---|---|---|
| CH1 | Mô hình nào (PhoBERT, ViSoBERT, LLM) tốt nhất cho cảm xúc MXH tiếng Việt so với baseline? | Huấn luyện & so sánh mô hình cảm xúc |
| CH2 | Phát hiện, phân loại xu hướng theo thời gian thế nào cho hiệu quả? | Topic modeling + chuỗi thời gian |
| CH3 | Kiến trúc thu thập, lưu trữ nào bảo đảm hiệu năng, mở rộng, ổn định? | Mô-đun thu thập & lưu trữ |
| CH4 | Cơ chế an ninh nào vừa tuân thủ luật vừa giữ độ chính xác? Đánh đổi ra sao? | Tích hợp bảo mật & đánh giá đánh đổi |
| CH5 | Có tích hợp được 4 thành phần thành hệ thống thử nghiệm không, hiệu quả ra sao? | Hệ thống end-to-end + dashboard |

Xem trang **🔗 Truy vết CH1–CH5** để biết mục nào đang trả lời câu hỏi nào.

## Phạm vi
**Trong phạm vi (đề xuất, chờ chốt ở D-001, D-002, D-006):**
- Dữ liệu văn bản (bình luận/bài đăng công khai) tiếng Việt, thu thập qua API chính thức.
- Phân loại cảm xúc mức bình luận; phát hiện chủ đề & xu hướng theo thời gian.
- Ẩn danh tác giả, xác thực/phân quyền, bảo vệ API, nhật ký, an toàn ML pipeline.

**Ngoài phạm vi (đề xuất):** xử lý video/âm thanh/ảnh (Speech-to-Text, OCR), thu thập trái ToS (scraping vượt rào), phân tích thời gian thực dạng streaming, triển khai production.

## Sản phẩm bàn giao (theo mục 8 thuyết minh)
- [ ] Báo cáo tổng hợp kết quả nghiên cứu (T-053)
- [ ] Bộ dữ liệu thực nghiệm: Raw / Clean / Labeled / Train-Val-Test (T-025…T-027, T-055)
- [ ] Tài liệu quy trình thu thập, tiền xử lý, gán nhãn (T-055)
- [ ] Kết quả thực nghiệm & bảng so sánh mô hình ML / DL / Transformer (T-049)
- [ ] Phương pháp & kết quả phát hiện xu hướng (T-034…T-037, T-050)
- [ ] Kiến trúc hệ thống thử nghiệm (DOC-003)
- [ ] Prototype: quản lý người dùng & phân quyền, cấu hình nguồn/từ khóa, theo dõi thu thập, tìm kiếm/lọc, phân tích cảm xúc/chủ đề/xu hướng, dashboard
- [ ] Cơ chế an ninh an toàn: Auth, RBAC, bảo vệ API, mã hóa, quyền riêng tư, audit log, monitoring (T-038…T-044)
- [ ] Kịch bản đánh giá an toàn hệ thống (T-044, T-052)
- [ ] Đánh giá hiệu năng: thời gian thu thập, throughput, latency, thời gian suy luận, CPU/RAM/GPU (T-051)

## Cách dùng công cụ này
- Chạy `python pm/server.py` → mở http://localhost:8765. Lần đầu chọn tên của bạn (lưu ở `pm/.user`, không lên git).
- **Mỗi mục là 1 file** `pm/items/<ID>-*.md`; tài liệu ở `pm/docs/`. Ảnh dán vào thảo luận lưu ở `pm/assets/`.
- Trước khi làm: bấm **⟳ Đồng bộ** để lấy thay đổi của người kia. Làm xong: bấm lại để đẩy lên. Nút có số ↑ (chưa đẩy) / ↓ (có cập nhật mới).
- Nhắc mục khác bằng mã (VD `D-003`) → tự thành link; mục được nhắc sẽ hiện "Được nhắc tới ở".
- Gắn câu hỏi nghiên cứu (CH1–CH5) cho đầu việc để trang Truy vết tự tổng hợp.
- Mục nào có ghi **"Đề xuất (Claude)"** là gợi ý ban đầu — cần 2 người xem lại và chốt.

## Thảo luận
<!-- Chỉ thêm bình luận vào cuối file. Mỗi bình luận bắt đầu bằng: ### YYYY-MM-DD HH:MM:SS · Tên -->
