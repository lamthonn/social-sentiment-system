# Module thu thập dữ liệu - Giai đoạn 2

Collector cho **YouTube** (sẵn dùng) và **TikTok** (đã scaffold, chờ key thật để
verify). Cả 2 dùng chung 1 pipeline: lấy comment công khai từ video → ẩn danh
tác giả ngay khi thu thập bằng `security.anonymize.hash_identifier()` → ghi
vào bảng `raw_posts`. Trùng comment (đã thu thập trước đó) tự động bị bỏ qua.

---

## YouTube

### 1. Lấy API key
1. Vào [Google Cloud Console](https://console.cloud.google.com/) → tạo project mới (hoặc dùng project có sẵn).
2. Vào **APIs & Services → Library**, bật **YouTube Data API v3**.
3. Vào **APIs & Services → Credentials**, tạo **API key**.
4. (Khuyến nghị) Giới hạn key chỉ dùng cho YouTube Data API v3.

### 2. Cấu hình `.env`
```
YOUTUBE_API_KEY=<key vừa tạo>
COLLECTOR_POLL_INTERVAL_MINUTES=60
```

### 3. Chạy thử (biết trước video ID) - dùng CLI, không phụ thuộc UI/DB
```bash
python -m collector run --platform youtube --video dQw4w9WgXcQ --max-pages 1
```
`videoId` là đoạn sau `v=` trong URL, VD `https://www.youtube.com/watch?v=dQw4w9WgXcQ` → `dQw4w9WgXcQ`
(hoặc dán nguyên URL cũng được - CLI tự trích ID).

### 4. Tìm video mới theo từ khóa (không cần biết trước ID) - dùng CLI, chạy 1 lần
```bash
python -m collector search --query "giá vàng" --max-videos 5 --days 7
```
Tự tìm video YouTube khớp từ khóa, đăng trong N ngày gần đây, rồi thu thập luôn comment
của từng video tìm được.

### 5. Tự động lặp lại định kỳ - cấu hình qua UI (không sửa `.env`)
Mở frontend (`make frontend`) → tab **"Cấu hình thu thập"**:
- **Từ khóa tìm kiếm**: thêm từ khóa + số video tối đa/lượt + số ngày gần đây, bật/tắt từng từ khóa.
- **Video theo dõi cố định**: dán video ID hoặc URL đầy đủ (YouTube/TikTok), theo dõi liên tục không giới hạn thời gian.

Lưu qua UI ghi thẳng vào DB (bảng `search_queries`/`tracked_videos`), scheduler đọc
lại từ DB **mỗi lượt chạy** - thêm/sửa/xóa/tắt qua UI có hiệu lực ngay ở lượt kế
tiếp, không cần restart `make collect-schedule`.

### Giới hạn quota
Mặc định **10.000 unit/ngày** (miễn phí).
- `commentThreads.list` (lấy comment): **1 unit/lần** (tối đa 100 comment/lần) → theo dõi vài chục video, poll mỗi giờ là thoải mái.
- `search.list` (tìm theo từ khóa): **100 unit/lần**, đắt hơn hẳn → VD interval mặc định 60 phút (24 lượt/ngày) x 1 từ khóa = 2.400 unit/ngày. Thêm nhiều từ khóa hoặc rút ngắn interval thì tính lại, tránh hết quota giữa ngày.

---

## TikTok

> ⚠️ **Chưa test bằng key thật.** Code viết theo tài liệu công khai của TikTok
> Research API tại thời điểm viết - endpoint/field có thể đã đổi. Việc đầu
> tiên cần làm khi có key: chạy thử `run --platform tiktok`, xem lỗi (nếu có)
> để chỉnh lại `collector/tiktok_client.py`. Đặc biệt: tài liệu công khai của
> TikTok **không thấy field định danh tác giả comment** rõ ràng (khác YouTube)
> - xem cảnh báo chi tiết trong `collector/pipeline.py` (`_parse_tiktok_comment`)
> và **bắt buộc kiểm tra lại** trước khi tin dữ liệu ẩn danh đã đúng.

### 1. Đăng ký Research API
1. Vào [developers.tiktok.com/products/research-api](https://developers.tiktok.com/products/research-api/)
2. Đăng ký tài khoản TikTok for Developers, nộp đơn Research API (nêu rõ mục đích nghiên cứu, tên đề tài NCKH).
3. Chờ duyệt → nhận `client_key` + `client_secret`.

### 2. Cấu hình `.env`
```
TIKTOK_CLIENT_KEY=<client_key>
TIKTOK_CLIENT_SECRET=<client_secret>
```

### 3. Chạy thử - dùng CLI
```bash
python -m collector run --platform tiktok --video 7123456789012345678 --max-pages 1
```
`videoId` là đoạn số cuối URL, VD `https://www.tiktok.com/@user/video/7123456789012345678` → `7123456789012345678`.

### 4. Theo dõi định kỳ - thêm qua UI (tab "Cấu hình thu thập" → "Video theo dõi cố định",
chọn nền tảng TikTok) - xem mục 5 phần YouTube ở trên, cách làm giống hệt.

---

## Chạy định kỳ (scheduler) - cả 2 nền tảng, mọi mục cấu hình qua UI

```bash
make collect-schedule
# hoặc: python -m collector schedule
```
Chạy foreground, thu thập ngay lần đầu rồi lặp lại mỗi `COLLECTOR_POLL_INTERVAL_MINUTES`
phút - **mỗi lượt đọc lại cấu hình từ DB**, nên thêm/sửa/xóa video/từ khóa qua UI trong
lúc scheduler đang chạy sẽ có tác dụng ở lượt kế tiếp mà không cần restart. Dừng bằng `Ctrl+C`.

## Ghi chú an toàn dữ liệu
- Chỉ hash định danh tác giả ổn định (YouTube: `authorChannelId`) - **không lưu
  bất kỳ thông tin định danh gốc nào**, đúng theo Luật số 91/2025/QH15.
- Chỉ thu thập nội dung **công khai** qua API chính thức của từng nền tảng -
  tuân thủ ToS tương ứng ([YouTube](https://developers.google.com/youtube/terms/api-services-terms-of-service),
  [TikTok](https://developers.tiktok.com/doc/research-api-terms-of-service)).

## Mở rộng thêm nền tảng khác
Theo mẫu `collector/youtube_client.py` hoặc `collector/tiktok_client.py` +
`collector/pipeline.py`: viết 1 client gọi API/nguồn dữ liệu mới, 1 hàm
`_parse_xxx_comment()` trả về `post_id` + `author_identifier` + `content` +
`posted_at`, đăng ký vào `_COLLECTORS` trong `pipeline.py`.
