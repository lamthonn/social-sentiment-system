# Sổ việc của Lâm

> Chỉ Lâm (và Claude của Lâm) sửa file này. Quy tắc: [HUONG_DAN_VIBE_CODE.md](HUONG_DAN_VIBE_CODE.md).
> Trạng thái chính thức và kết quả của từng đầu việc ghi ở `PROJECT.md`; sổ này ghi đang làm gì, làm tiếp gì và ghi chú giữa các phiên.
> Bản đầu do Claude của Nam soạn từ `PROJECT.md` để khởi tạo. Lâm sửa, sắp xếp lại tùy ý.

## Đang làm

| Đầu việc | Nhánh | Ghi chú |
|---|---|---|
| T-12 Chuẩn hóa và lưu dữ liệu thô, dữ liệu đã xử lý | | Bộ tiền xử lý `preprocessing/cleaner.py`... đã lên `main`. Xem QD-11 về việc hợp nhất với `preprocessing/text.py` |
| T-01 Khảo sát hệ thống thu thập dữ liệu MXH | | |
| T-02 Khảo sát lưu trữ, xử lý dữ liệu lớn | | |

## Hàng đợi (làm theo thứ tự)

1. **Thu thập dữ liệu thật:** đặt `YOUTUBE_API_KEY`, chạy thu thập theo vài từ khóa. Đây là việc mở khóa T-16, T-31, T-34, T-42 của Nam.
2. **T-11** TikTok Research API: chờ key; kiểm tra trường định danh tác giả khi có key.
3. **T-03, T-04** Khảo sát kỹ thuật và viết báo cáo tổng quan (GD-01).
4. **T-06, T-13** Nghiên cứu và thử nghiệm hàng đợi (Kafka/RabbitMQ).
5. **T-46** Rà soát tuân thủ Luật 91/2025/QH15.
6. **T-37** Đề xuất hướng phát triển.

## Cần người kia (Nam)

<!-- Ghi việc cần Nam làm hoặc cần Nam biết. VD: "Thêm endpoint GET /collector/stats - cần thêm dòng RULES" -->

## Đã xong gần đây

- Bộ tiền xử lý `preprocessing/` (cleaner, teencode, tokenizer, pipeline) + `tests/`.
- `run.py` và `start.bat`: chạy cả hệ thống bằng 1 lệnh.

## Nhật ký phiên

<!-- Mỗi phiên một dòng, thêm vào cuối: - YYYY-MM-DD: làm gì, kết quả, còn dở gì -->
