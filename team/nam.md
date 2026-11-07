# Sổ việc của Nam

> Chỉ Nam (và Claude của Nam) sửa file này. Quy tắc: [HUONG_DAN_VIBE_CODE.md](HUONG_DAN_VIBE_CODE.md).
> Trạng thái chính thức và kết quả của từng đầu việc ghi ở `PROJECT.md`; sổ này ghi đang làm gì, làm tiếp gì và ghi chú giữa các phiên.

## Đang làm

| Đầu việc | Nhánh | Ghi chú |
|---|---|---|
| T-27, T-28 (xong, chưa commit) | `feat/pipeline-webapp` | HTTPS + mã hóa khi lưu + sửa quyền `/posts` + hướng dẫn sử dụng. Commit rồi mở PR vào `main` |

## Hàng đợi (làm theo thứ tự)

1. **T-16** Gán nhãn dữ liệu: dựng trang gán nhãn trong webapp, xuất/nhập file, đo độ đồng thuận (Cohen's kappa) giữa Nam và Lâm. *Cần dữ liệu thật (YOUTUBE_API_KEY).*
2. **T-42** Xu hướng gắn cảm xúc: kiểm tra lại trên dữ liệu thật khi có.
3. **T-32** Dashboard: hoàn thiện theo góp ý khi dùng thử.
4. **T-34** So sánh mô hình: thêm đánh giá trên dữ liệu MXH đã gán nhãn (sau T-16).
5. **T-31** Tích hợp: chạy cả chuỗi trên dữ liệu thật, ghi kết quả.
6. **T-05** Cơ sở lý thuyết NLP, embedding, ML/DL, Transformer (viết).
7. **T-47** Khảo sát yêu cầu với GV hướng dẫn → **T-38** bổ sung thông tin còn thiếu → **T-49** sửa thuyết minh theo QD-04..06.
8. **T-36** Báo cáo tổng kết.

## Cần người kia (Lâm)

- Duyệt **QD-10** (chia việc) và **QD-11** (hợp nhất 2 bộ tiền xử lý) trong `PROJECT.md`.
- Sau khi PR T-27/T-28 vào `main`, trên máy Lâm cần chạy:
  - `python -m security.crypto genkey` → dán vào `.env` dòng `DATA_ENCRYPTION_KEY=...`
  - `python -m security.tls` (nếu muốn chạy HTTPS)
  - `docker compose up -d` để áp dụng cổng chỉ nghe 127.0.0.1
- `run.py` và `docker-compose.yml` (phần của Lâm) đã được Nam sửa nhỏ: tự bật https khi có chứng chỉ, giới hạn cổng ở 127.0.0.1. Lâm xem lại trong PR.
- Gán nhãn cùng Nam cho T-16 (cần 2 người để đo độ đồng thuận).

## Đã xong gần đây

- T-35 đánh giá an ninh, T-48 học liên kết (commit `57a8fc2`).
- T-27 HTTPS, T-28 mã hóa khi lưu, sửa lỗ hổng `/posts` lộ nội dung gốc cho analyst (chưa commit).

## Nhật ký phiên

<!-- Mỗi phiên một dòng, thêm vào cuối: - YYYY-MM-DD: làm gì, kết quả, còn dở gì -->
- 2026-11-06: T-27, T-28, sửa quyền `/posts`, viết HUONG_DAN_SU_DUNG.md. Gộp `main` mới của Lâm (cleaner/teencode/tokenizer, run.py) vào nhánh.
- 2026-11-07: Lập quy trình làm việc 2 người (thư mục `team/`, QD-10, QD-11, `.gitattributes`).
