# Công cụ quản lý đề tài (`pm/`)

Nơi quản lý đầu việc, việc cần chốt, câu hỏi khảo sát, mô hình, ứng dụng, yêu cầu, rủi ro, thực nghiệm, sửa thuyết minh, biên bản họp và thảo luận của đề tài. Mọi thứ là file Markdown trong git, nên ai cũng xem được trên GitHub và sửa tay được khi cần.

## Chạy

```bash
python pm/server.py          # mở http://localhost:8765 (tự bật trình duyệt)
python pm/server.py 8800     # đổi cổng
python pm/server.py --no-browser
```

- Cần Python 3.10 trở lên, không phải cài thêm gì. Không cần `.venv` của dự án.
- Giao diện tải thư viện markdown và sơ đồ từ CDN nên cần có mạng.
- Lần đầu mở, chọn tên của bạn. Tên được lưu ở `pm/.user` (không đưa lên git) và dùng làm tác giả bình luận và commit.

## Làm việc hằng ngày (2 người)

1. Mở công cụ rồi bấm **⟳ Đồng bộ** để lấy thay đổi của người kia.
2. Làm việc: sửa trạng thái, nội dung, checklist; thảo luận (dán ảnh bằng **Ctrl+V**, kéo thả file); tạo mục mới.
3. Bấm **⟳ Đồng bộ** để đẩy lên.

Nút "Đồng bộ" chạy lần lượt:

1. Commit thư mục `pm/`, và chỉ thư mục này. Code của đề tài không bị đụng tới.
2. `git pull --rebase --autostash`.
3. Tự đổi mã nếu bị trùng.
4. Sinh lại `INDEX.md`.
5. `git push`.

Huy hiệu trên nút cho biết:
- **↑N:** còn N thay đổi chưa đẩy lên.
- **↓N:** người kia có N commit mới chưa lấy về (kiểm tra mỗi 5 phút).

## Vì sao 2 người sửa cùng lúc mà không xung đột

- **Mỗi mục là 1 file** (`items/T-012-*.md`). Hai người sửa hai mục khác nhau thì không bao giờ xung đột.
- **Thảo luận chỉ thêm vào cuối file.** `.gitattributes` đặt `merge=union`, nên khi hai người cùng bình luận vào một mục, git giữ cả hai bình luận.
- **Hai người cùng sửa một trường** (ví dụ cùng đổi trạng thái): file sẽ có trường bị lặp. Giao diện hiện ⚠️ ở trang Tổng quan và trang mục. Chỉ cần chọn lại giá trị đúng, lưu là hết cảnh báo.
- **Hai người cùng tạo mục mới khi chưa đồng bộ** (cùng ra T-056): người đồng bộ sau sẽ được tự đổi mã sang mã kế tiếp và nhận thông báo.
- **Pull lỗi** (mạng, hoặc xung đột ở code ngoài `pm/`): server tự hoàn tác rebase và hiện log. Dữ liệu cục bộ không mất.

## Cấu trúc

```
pm/
  server.py, index.html, app.js, style.css   công cụ
  config.json        loại mục, trạng thái, trường, thành viên, mô-đun, CH1–CH5
  docs/DOC-*.md      tài liệu: tổng quan, nghiệp vụ, kiến trúc, tuân thủ
  items/<MÃ>-*.md    mỗi mục 1 file
  assets/            ảnh/file dán vào nội dung và thảo luận
  INDEX.md           bảng tổng hợp tự sinh khi đồng bộ (đừng sửa tay)
```

**Định dạng một mục:**

```markdown
---
id: D-003
type: decision
title: …
status: open
owner: Nam
links: [T-025, TM-007]
---
## Bối cảnh
…
## Thảo luận
### 2026-10-29 21:30:12 · Nam
Nội dung bình luận…
```

Có thể sửa tay file `.md` bằng editor, chỉ cần giữ đúng phần `---` đầu file và dòng tiêu đề `### <ngày giờ> · <tên>` của từng bình luận.

## Các loại mục

| Mã | Loại | Dùng để |
|---|---|---|
| `DOC` | Tài liệu | Tổng quan, nghiệp vụ, kiến trúc (có sơ đồ Mermaid), checklist tuân thủ |
| `T` | Đầu việc | Việc cần làm, có checklist việc con; % hoàn thành tính theo checklist |
| `D` | Việc cần chốt | Phương án, đề xuất, kết luận |
| `Q` | Câu hỏi khảo sát | Theo 5 mô-đun của khung khảo sát; có trường "Hỏi ai" và "Trả lời ngắn" |
| `MODEL` | Mô hình | Ứng viên cho bài toán cảm xúc, xu hướng, tiền xử lý; danh sách có cột **Kết quả** để so sánh |
| `APP` | Ứng dụng của đề tài | Chấm điểm theo 5 tiêu chí (1–5) trong "Thông tin thêm"; danh sách tự xếp theo **tổng điểm** |
| `FR` / `NFR` | Yêu cầu | Trạng thái: đã có / một phần / chưa có / ngoài phạm vi |
| `R` | Rủi ro | Khả năng xảy ra, mức ảnh hưởng, cách giảm thiểu |
| `E` | Thực nghiệm | Mô hình, dataset, Accuracy, Macro-F1; số liệu dùng cho báo cáo |
| `TM` | Sửa thuyết minh | Lỗi và điểm chưa khớp trong `TM_final.docx` |
| `M` | Biên bản họp | Nội dung, quyết định, việc phát sinh |

**Mẹo:**
- Gõ mã mục khác (ví dụ `D-003`) trong nội dung hoặc thảo luận là thành link. Mục được nhắc sẽ có phần "Được nhắc tới ở".
- Gắn **Câu hỏi NC** (CH1–CH5) cho đầu việc (trong "Thông tin thêm") để trang **Khác → Truy vết** tự tổng hợp mục nào trả lời câu hỏi nghiên cứu nào.
- Thêm loại mục, trạng thái, trường, thành viên hay mô-đun bằng cách sửa `config.json`, rồi tải lại trang.
