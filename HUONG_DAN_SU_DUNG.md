# Hướng dẫn sử dụng hệ thống phân tích cảm xúc và xu hướng

Hệ thống thu thập bình luận công khai trên mạng xã hội (hiện là YouTube), lưu trữ có ẩn danh, rồi tự động:

- nhận diện **quan điểm** (Tích cực / Trung tính / Tiêu cực) và **cảm xúc** (Vui vẻ, Buồn bã, Tức giận, Ghê tởm, Sợ hãi, Ngạc nhiên, Khác);
- gom **chủ đề** và cho biết chủ đề nào đang **mới nổi, tăng, giảm hay ổn định**.

Tài liệu này hướng dẫn **dùng** webapp. Cài đặt chi tiết và xử lý lỗi khi cài xem [HUONG_DAN_CHAY.md](HUONG_DAN_CHAY.md).

---

## 1. Khởi động

**Cách nhanh (Windows):** bấm đúp `start.bat` trong thư mục dự án. Một cửa sổ sẽ tự bật CSDL, API và webapp rồi mở trình duyệt. Muốn dừng, bấm **Ctrl+C** trong cửa sổ đó.

**Hoặc chạy tay** (2 cửa sổ dòng lệnh, đứng ở thư mục dự án):

```powershell
# Cửa sổ 1
docker compose up -d
.venv\Scripts\Activate.ps1
python -m storage.migrate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Cửa sổ 2
npm run dev --prefix frontend
```

Sau đó mở **https://localhost:5500**. Nếu máy chưa tạo chứng chỉ HTTPS thì địa chỉ là http://localhost:5500.

> **Trình duyệt báo "Kết nối không riêng tư".** Lý do là hệ thống dùng chứng chỉ tự ký cho môi trường chạy thử. Bấm **Nâng cao → Tiếp tục truy cập localhost**. Muốn hết cảnh báo hẳn, nhập file `data/certs/cert.pem` vào mục *Trusted Root Certification Authorities* (mở bằng `certmgr.msc`).

---

## 2. Tài khoản và đăng nhập

### Tạo tài khoản đầu tiên

Lần đầu chưa có tài khoản nào. Người quản trị tạo bằng dòng lệnh:

```powershell
python -m security.users add nam --role admin
```

Lệnh sẽ hỏi mật khẩu: **tối thiểu 10 ký tự, có cả chữ và số**. Các tài khoản sau đó tạo trong webapp ở mục **Người dùng & nhật ký** (xem [mục 9](#9-người-dùng--nhật-ký-chỉ-quản-trị)).

### Đăng nhập

Nhập **Tên đăng nhập** và **Mật khẩu** rồi bấm **Đăng nhập**.

- Tên đăng nhập là tên đặt lúc tạo tài khoản (ví dụ `nam`), **không phải tên vai trò**. Chữ "admin" trong lệnh trên là vai trò.
- Nhập sai **5 lần liên tiếp** thì bị khóa đăng nhập **10 phút**.
- Phiên đăng nhập hết hạn sau 8 giờ, khi đó hệ thống tự đưa về màn hình đăng nhập.

Góc trên bên phải có menu tài khoản, gồm **Đổi mật khẩu** và **Đăng xuất**.

### Vai trò

Mỗi tài khoản có một vai trò. Vai trò cao hơn làm được mọi việc của vai trò thấp hơn.

| Vai trò | Xem được | Làm được |
|---|---|---|
| **Người xem** | Tổng quan, Xu hướng, Mô hình (số liệu tổng hợp) | Chỉ xem |
| **Phân tích viên** | + Dữ liệu đã phân tích (nội dung **đã che** SĐT, email, @tên), Pipeline | Cấu hình thu thập, bật/tắt thu thập tự động, chạy các bước xử lý dữ liệu |
| **Quản trị** | + Dữ liệu thô (nội dung gốc), nhật ký truy cập, chi tiết cảnh báo an ninh | Huấn luyện và chọn mô hình, quản lý tài khoản |

Menu bên trái chỉ hiện những trang mà vai trò của bạn được xem.

---

## 3. Quy trình sử dụng điển hình

```
Khai báo nguồn (Thu thập) → Thu thập → Làm sạch → Dự đoán → Xu hướng → Giám sát → Xem kết quả (Tổng quan, Xu hướng)
```

1. **Thu thập → Cấu hình thu thập:** thêm từ khóa tìm kiếm hoặc video cần theo dõi.
2. **Pipeline → Chạy cả chuỗi:** hệ thống lấy bình luận mới, làm sạch, gán nhãn quan điểm và cảm xúc, gom chủ đề và kiểm tra bất thường.
3. Xem kết quả ở **Tổng quan** và **Xu hướng**. Đọc từng bình luận ở **Dữ liệu đã phân tích**.

Bật **Thu thập tự động** (trang Thu thập) thì hệ thống tự lấy dữ liệu theo chu kỳ, mặc định 60 phút một lần.

> Muốn thu thập được, file `.env` phải có `YOUTUBE_API_KEY`. Thiếu khóa này, bước Thu thập sẽ được bỏ qua và các trang kết quả hiện "Chưa có dữ liệu".

---

## 4. Tổng quan

Trang đầu tiên sau khi đăng nhập, tóm tắt toàn bộ dữ liệu:

- **Các ô số liệu:**
  - **Bài thu thập:** tổng số bình luận đã lấy về.
  - **Dùng được để phân tích:** số bài còn lại sau khi loại spam, bài trùng và bài không phải tiếng Việt.
  - **Đã gán quan điểm**, **Đã gán cảm xúc:** số bài đã được mô hình gán nhãn.
- **Phân bố quan điểm** và **Phân bố cảm xúc:** tỉ lệ từng nhãn.
- **Quan điểm theo ngày:** diễn biến số bài tích cực, trung tính, tiêu cực theo thời gian.
- **Quan điểm theo chủ đề thu thập:** so sánh 10 chủ đề có nhiều bài nhất.

Bộ lọc phía trên chọn **khoảng thời gian** (7 ngày, 30 ngày, 90 ngày, 1 năm) và **chủ đề thu thập**.

Khi có vấn đề, trang hiện khung vàng **Cảnh báo giám sát**. Ví dụ:

- tỉ lệ spam cao;
- mô hình dự đoán lệch xa dữ liệu huấn luyện (dấu hiệu dữ liệu mới khác dữ liệu đã học);
- có lượt chạy pipeline bị lỗi;
- có dấu hiệu tấn công, chẳng hạn dò mật khẩu hay tải dữ liệu hàng loạt.

Riêng cảnh báo an ninh: chỉ quản trị thấy chi tiết (tài khoản, IP), các vai trò khác chỉ thấy số lượng.

---

## 5. Xu hướng

Hệ thống tự **gom chủ đề** từ bài của 60 ngày gần nhất, theo từng chủ đề thu thập. Mỗi chủ đề có:

- **Từ khóa đại diện:** các từ mô tả chủ đề.
- **Số bài** và **Độ quan tâm theo ngày** (biểu đồ nhỏ).
- **Xu hướng:** so số bài của 3 ngày gần nhất với tối đa 7 ngày trước đó.

| Nhãn | Ý nghĩa |
|---|---|
| **Mới nổi** | Trước đó gần như không có bài, 3 ngày gần đây có từ 5 bài trở lên |
| **Đang tăng** | Số bài trung bình mỗi ngày tăng từ 50% trở lên |
| **Đang giảm** | Số bài trung bình mỗi ngày giảm từ 50% trở lên |
| **Ổn định** | Thay đổi trong khoảng ±50% |
| Chưa đủ dữ liệu | Quá ít ngày có bài để so sánh |

- **Chiều cảm xúc:** cho biết cảm xúc của chủ đề đang chuyển sang tích cực hay tiêu cực.
- **Tích cực / Tiêu cực:** tỉ lệ bài tích cực so với tiêu cực trong chủ đề.

Bảng **Hashtag** liệt kê các hashtag xuất hiện nhiều nhất kèm xu hướng của chúng.

> Xu hướng chỉ phân tích ở **mức cộng đồng**, không bao giờ theo dõi riêng từng người dùng.

---

## 6. Dữ liệu đã phân tích (phân tích viên trở lên)

Danh sách từng bình luận kèm nhãn mô hình đã gán:

- **Nội dung (đã làm sạch):** số điện thoại, email, @tên được thay bằng `xxsđt`, `xxemail`, `xxngườidùng`.
- **Quan điểm**, **Cảm xúc:** nhãn kèm độ tin cậy.
- **Tác giả (băm):** mã ẩn danh. Hệ thống không lưu tên hay ID thật của người viết.

Phía trên bảng có các bộ lọc:

- **Tìm trong nội dung…:** tìm trên văn bản đã làm sạch.
- **Nền tảng**, **Chủ đề thu thập**, **Quan điểm**, **Cảm xúc**.
- **Hiện cả spam/trùng lặp:** mặc định hệ thống ẩn bài bị đánh dấu spam (ví dụ bài để lại số điện thoại quảng cáo) và bài trùng; bật ô này để xem cả những bài đó.

Quản trị viên còn thấy thêm nội dung gốc chưa che.

---

## 7. Thu thập (phân tích viên trở lên)

### Cấu hình thu thập

- **Thu thập tự động:** công tắc bật/tắt lấy dữ liệu theo chu kỳ.
- **Từ khóa tìm kiếm (YouTube):** hệ thống tự tìm video mới theo từ khóa rồi lấy bình luận.
  - **Từ khóa:** ví dụ "giá vàng".
  - **Chỉ lấy video đăng trong N ngày gần đây.**
  - **Số video tối đa/lượt.**
  - **Bật:** tạm tắt từ khóa mà không cần xóa.
- **Video theo dõi cố định:** dán **URL đầy đủ hoặc chỉ ID** của video cần theo dõi, có thể thêm **Ghi chú** (ví dụ "Video phát biểu ngày 1/1").

Từ khóa hoặc ghi chú trở thành **chủ đề thu thập** của các bài lấy về. Đây chính là bộ lọc "chủ đề" ở các trang khác.

> **Hạn mức YouTube.** Mỗi từ khóa tốn khoảng 100 đơn vị cho mỗi lần tìm; hạn mức miễn phí là 10.000 đơn vị/ngày. Đừng bật quá nhiều từ khóa với chu kỳ quá ngắn.

### Dữ liệu thô (chỉ quản trị)

Hiện nội dung gốc đúng như khi thu thập, lọc được theo nền tảng và chủ đề. Nội dung này chưa che thông tin cá nhân nên chỉ quản trị xem được.

---

## 8. Mô hình

### Kết quả các mô hình

Mỗi bài toán (**Quan điểm 3 lớp**, **Cảm xúc 7 nhãn**) có một bảng các lần huấn luyện với **Accuracy**, **F1-macro**, **Precision** và **Recall**:

- **F1-macro** là chỉ số chính để so sánh mô hình (trung bình đều trên các nhãn, nên không bị lấn át bởi nhãn đông).
- Mô hình gắn thẻ **đang dùng** là mô hình hệ thống đang dùng để gán nhãn dữ liệu mới. Mặc định hệ thống tự chọn mô hình có F1-macro cao nhất.
- Mở một dòng để xem chi tiết:
  - kết quả theo từng nhãn;
  - **Ma trận nhầm lẫn** (hàng là nhãn thật, cột là nhãn dự đoán);
  - quá trình học theo từng epoch.
- Quản trị viên bấm **Chọn dùng** để đổi mô hình đang dùng bằng tay.

### Thực nghiệm bổ sung

Kết quả các thực nghiệm phục vụ báo cáo. Mỗi thực nghiệm có mô tả cách làm, bảng số liệu và nhận xét:

| Thực nghiệm | Trả lời câu hỏi |
|---|---|
| Đầu độc dữ liệu | Mô hình chịu được bao nhiêu nhãn sai, và cách phòng vệ có giúp không |
| Gom chủ đề | Phương pháp gom chủ đề nào khớp với chủ đề thật nhất |
| Quyền riêng tư vi phân (DP-SGD) | Bảo vệ riêng tư chặt hơn thì độ chính xác giảm bao nhiêu |
| Học liên kết (FedAvg) | Nhiều đơn vị cùng học mà không chia sẻ dữ liệu thì kết quả ra sao |
| Độ bền | Mô hình xử lý thế nào với bình luận không dấu, teencode, lỗi gõ |
| LLM cục bộ | Mô hình ngôn ngữ lớn có thay được mô hình đã huấn luyện không |
| Hiệu năng | Hệ thống xử lý nhanh đến đâu |
| Đánh giá an ninh | Các cơ chế phát hiện tấn công bắt được bao nhiêu, báo nhầm bao nhiêu |

---

## 9. Người dùng & nhật ký (chỉ quản trị)

**Người dùng:**

- **Thêm tài khoản:** nhập **Tên đăng nhập** (3–32 ký tự a-z, 0-9, `.`, `_`, `-`), **Mật khẩu**, **Vai trò**.
- Với mỗi tài khoản có thể đổi **Vai trò**, bật/tắt công tắc **Hoạt động** (tắt = khóa tài khoản), hoặc **Đặt lại mật khẩu**. Không tự đổi vai trò hay khóa chính mình được.
- Tài khoản bị khóa hay đổi vai trò có hiệu lực ngay, không cần đợi người đó đăng xuất.

**Nhật ký truy cập:** ghi lại ai làm gì, lúc nào, từ đâu. Nhật ký gồm:

- các lần đăng nhập (kể cả đăng nhập sai);
- các thao tác thay đổi dữ liệu;
- các lần xem dữ liệu chi tiết;
- các lần bị từ chối quyền;
- các lần vượt giới hạn tần suất.

Lọc theo người dùng, thao tác, hoặc tick **Chỉ thao tác thất bại / bị từ chối** để rà soát sự cố.

---

## 10. Pipeline (phân tích viên trở lên)

### Chuỗi xử lý dữ liệu thu thập

Mỗi bước có nút **Chạy** riêng; nút **Chạy cả chuỗi** chạy đủ 5 bước theo thứ tự:

| Bước | Việc làm |
|---|---|
| **Thu thập** | Lấy bình luận mới từ các từ khóa và video đang bật |
| **Làm sạch** | Chuẩn hóa văn bản, che thông tin cá nhân, đánh dấu spam, bài trùng, ngôn ngữ |
| **Dự đoán** | Gán nhãn quan điểm và cảm xúc bằng mô hình đang dùng |
| **Xu hướng** | Gom chủ đề và phân loại xu hướng |
| **Giám sát** | Kiểm tra chất lượng dữ liệu, độ lệch mô hình, lượt chạy lỗi, dấu hiệu tấn công |

Mỗi bước chỉ xử lý dữ liệu mới, nên bấm chạy lại nhiều lần không sinh dữ liệu trùng.

### Dữ liệu huấn luyện và mô hình (chỉ quản trị)

- **Chuẩn bị dataset (UIT-VSFC, UIT-VSMEC):** tải và làm sạch hai bộ dữ liệu huấn luyện. Chỉ cần làm một lần.
- **Huấn luyện:** chọn bài toán (**Quan điểm 3 lớp** hoặc **Cảm xúc 7 nhãn**) và mô hình:

| Mô hình | Thời gian | Ghi chú |
|---|---|---|
| TF-IDF + Logistic Regression / Linear SVM | Vài giây | Nhanh, dễ giải thích |
| BiLSTM | Vài phút | Học sâu cơ bản |
| ViSoBERT, PhoBERT-base-v2 | Vài chục phút | Chính xác nhất, cần GPU |

Huấn luyện xong, mô hình mới tự được dùng nếu F1-macro cao hơn mô hình hiện tại.

### Lịch sử chạy

Bảng ghi mọi lượt chạy, gồm:

- **Bước**, **Trạng thái**, **Bắt đầu**, **Thời lượng**;
- **Vào → ra**: số bản ghi vào và ra;
- **Người chạy**.

Mở một dòng để xem chi tiết, ví dụ các cảnh báo mà bước Giám sát tìm thấy.

---

## 11. Bảo mật: những điều người dùng cần biết

- **Ẩn danh:** tên/ID người viết bình luận được băm ngay khi thu thập, hệ thống không lưu bản gốc.
- **Che thông tin cá nhân:** người xem và phân tích viên chỉ thấy nội dung đã che SĐT, email, @tên.
- **Mã hóa khi lưu:** nội dung gốc trong CSDL và các bản sao lưu đều được mã hóa. Mở CSDL bằng Adminer sẽ chỉ thấy chuỗi bắt đầu bằng `enc1:`; đây là bình thường.
- **Khóa mã hóa** nằm ở dòng `DATA_ENCRYPTION_KEY` trong file `.env`. **Mất khóa là mất toàn bộ dữ liệu đã mã hóa.** Người quản trị cần cất một bản khóa ở nơi riêng, không để chung chỗ với bản sao lưu, và không gửi khóa qua chat hay email.
- **Sao lưu:** quản trị chạy `python -m storage.backup` để tạo bản sao lưu (trong `data/backups/`), và `python -m storage.backup --list` để xem danh sách.
- **Mọi thao tác đều được ghi nhật ký.** Đăng nhập sai nhiều lần, dò quyền hay tải dữ liệu hàng loạt sẽ tạo cảnh báo cho quản trị.

---

## 12. Câu hỏi thường gặp

**Báo "Sai tên đăng nhập hoặc mật khẩu" dù nhập đúng?**
Kiểm tra lại tên đăng nhập; đó là tên tài khoản, không phải tên vai trò. Quản trị xem danh sách bằng `python -m security.users list` và đặt lại mật khẩu bằng `python -m security.users set-password <tên>`.

**Báo "Sai mật khẩu quá nhiều lần"?**
Đợi 10 phút rồi thử lại.

**Các trang đều hiện "Chưa có dữ liệu"?**
Hệ thống chưa thu thập được gì. Kiểm tra theo thứ tự:
1. File `.env` đã có `YOUTUBE_API_KEY` chưa.
2. Đã thêm từ khóa hoặc video ở trang Thu thập chưa.
3. Đã bấm **Chạy cả chuỗi** ở trang Pipeline chưa.

**Không thấy trang Pipeline, Thu thập hay Dữ liệu thô?**
Vai trò của bạn chưa đủ quyền (xem bảng vai trò ở [mục 2](#vai-trò)). Nhờ quản trị đổi vai trò.

**Một bình luận không hiện trong Dữ liệu đã phân tích?**
Bình luận đó có thể bị đánh dấu spam hoặc trùng lặp. Bật **Hiện cả spam/trùng lặp**.

**Nhãn mô hình gán có vẻ sai với bình luận mạng xã hội?**
Mô hình được huấn luyện trên dữ liệu phản hồi sinh viên (UIT-VSFC) và bình luận Facebook (UIT-VSMEC). Văn bản mạng xã hội thực tế (không dấu, teencode, chủ đề khác) có thể làm mô hình kém chính xác hơn. Khi điều này xảy ra, bước Giám sát sẽ cảnh báo "phân phối nhãn dự đoán lệch xa dữ liệu huấn luyện".

**Khởi động báo cổng 5432 đã bị dùng?**
Có một dự án khác đang chiếm cổng của PostgreSQL. Đặt `POSTGRES_PORT=5433` trong `.env` rồi chạy lại `docker compose up -d`.

**Muốn xem tiến độ đề tài?**
Mở công cụ quản lý đề tài bằng `node tools/server.js` rồi vào http://localhost:8765 (xem [tools/README.md](tools/README.md)).
