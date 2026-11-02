# Công cụ quản lý dự án (`PROJECT.md`)

`PROJECT.md` ở gốc repo là nơi duy nhất lưu tình trạng dự án: tổng quan, nghiệp vụ, đầu việc, pipeline, model, các lần huấn luyện, nhật ký quyết định. File này đọc bình thường được trên GitHub hay VS Code. Công cụ trong thư mục `tools/` giúp xem, sửa, bình luận và đồng bộ git cho file đó.

## Chạy

```bash
node tools/server.js          # mở http://localhost:8765
node tools/server.js 9000     # muốn dùng cổng khác
```

- Cần Node.js 18 trở lên. Không cần `npm install` và không có bước build.
- Giao diện tải 3 thư viện từ CDN (marked 12.0.2, DOMPurify 3.1.6, Mermaid 10.9.1) nên máy cần có mạng.
- Lần đầu mở, chọn **Nam** hoặc **Lâm** ở góc phải. Lựa chọn được nhớ trong trình duyệt và dùng để ghi tên vào nhật ký và commit.

## Các màn hình

| Màn hình | Dùng để |
|---|---|
| **Tổng quan** | Xem % hoàn thành, việc bị chặn, tiến độ từng giai đoạn (GD-01…GD-11 theo mục 7 thuyết minh), trạng thái pipeline, model được chọn cho từng bài toán, hoạt động gần đây |
| **Nghiệp vụ** | Đọc tổng quan, giai đoạn, nghiệp vụ, nhật ký quyết định như một tài liệu; sửa từng mục (markdown thô) và bình luận từng mục |
| **Đầu việc** | Xem dạng Kanban (kéo thả thẻ để đổi trạng thái) hoặc dạng Bảng; lọc theo người, giai đoạn, trạng thái; bấm vào việc để sửa và ghi *Kết quả / Vướng mắc / Đề xuất điều chỉnh* |
| **Pipeline** | Xem sơ đồ 8 bước tô màu theo trạng thái; bấm vào một bước để xem và sửa nguồn dữ liệu, bước làm sạch, nơi lưu, model… của bước đó |
| **Model & thí nghiệm** | Chọn model cho từng bài toán; so sánh các lần huấn luyện theo metric (bấm tiêu đề cột để sắp xếp); xem danh sách model |

**Sửa dữ liệu:**
- Bấm vào một đối tượng bất kỳ để mở ngăn chi tiết. Ở đó có form theo từng trường (dropdown cho trạng thái, người, giai đoạn, model) và nút **Sửa markdown thô** cho cả khối.
- Muốn "xóa" một đối tượng thì bấm **Đánh dấu Hủy**. Khối vẫn nằm trong file và mã không bao giờ bị dùng lại.

## Đồng bộ git

- **Thanh trên cùng** cho biết: PROJECT.md có thay đổi chưa commit hay không, đang đi trước hay sau remote bao nhiêu commit, và có đang gộp dở hay không.
- **Pull:** lấy thay đổi về. Nếu PROJECT.md đang có thay đổi chưa commit thì tool không pull mà nhắc bạn dùng Commit & Push.
- **Commit & Push:**
  1. Commit **chỉ file PROJECT.md**, với message tự sinh kiểu `Nam: cập nhật T-03, R-02`.
  2. Pull.
  3. Push.
  - Tool không bao giờ force push.
- **Khi có xung đột:**
  - Tool không tự gộp ngầm. Nó hiện từng đoạn xung đột với bản của bạn và bản từ remote, và bạn chọn bản giữ lại cho từng đoạn.
  - Riêng các dòng nhật ký (vốn chỉ được thêm vào cuối) của cả hai bên luôn được giữ, nên không mất bình luận của ai.
  - Bấm "Hủy gộp" để quay về trạng thái trước khi pull.
- **Xung đột ở file khác** (code): xử lý trong VS Code.

## An toàn

- Server chỉ nghe trên `127.0.0.1`.
- Server từ chối yêu cầu có Host hoặc Origin lạ, để trang web khác không gọi được vào.
- Server chỉ chạy một số lệnh git cố định (status, fetch, pull, add, commit, push, merge --abort) và không nhận lệnh tùy ý từ trình duyệt.

## Cách ghi file an toàn

- Tool chỉ sửa đúng các dòng của khối được sửa. Ví dụ đổi trạng thái thì `git diff` chỉ có đúng 1 dòng.
- Trước khi ghi, tool đọc lại file từ đĩa. Nếu file vừa bị đổi (người khác sửa, git pull, sửa tay bằng editor), thao tác được áp lên bản mới chứ không ghi đè.
- Nếu chính trường bạn đang sửa đã bị người khác đổi trước đó, tool báo và tải bản mới để bạn quyết định lại.

## Sửa tay PROJECT.md

Được, miễn giữ đúng quy ước ghi trong comment ở đầu file:
- Mỗi đối tượng là một khối `### MÃ Tên`.
- Thuộc tính viết dạng `- **Khóa:** giá trị`.
- Nhật ký chỉ thêm vào cuối, mỗi dòng có dạng `- [Nam · 2026-11-02 14:30] [Loại] nội dung`.
- Không ghi số liệu tổng hợp vào file.
- Không có hạn/deadline theo ngày.
