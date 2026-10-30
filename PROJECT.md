# PROJECT — Kỹ thuật máy học hiện đại kết hợp an ninh an toàn: thu thập dữ liệu mạng xã hội, nhận diện và phân loại cảm xúc, xu hướng người dùng

<!--
QUY ƯỚC ĐỊNH DẠNG (công cụ `node tools/server.js` đọc/ghi theo đúng quy ước này — sửa tay cũng phải giữ):
1. Mỗi đối tượng là MỘT khối, bắt đầu bằng heading cấp 3: `### <MÃ> <Tên>`, ví dụ `### T-03 Làm sạch dữ liệu`.
   Mã gồm tiền tố + số (T-01, DS-02, M-10…). Mã cố định, KHÔNG BAO GIỜ đánh lại hay dùng lại, kể cả khi bỏ đối tượng.
   Muốn bỏ một đối tượng: đổi Trạng thái thành "Hủy" (model: "Loại" hoặc "Hủy"), không xóa khối.
2. Thuộc tính viết ngay dưới heading, mỗi dòng một thuộc tính, mỗi giá trị trên MỘT dòng:
   `- **Trạng thái:** Đang làm`
3. Sau thuộc tính có thể viết nội dung markdown tự do (đoạn văn, danh sách, bảng nhỏ). Trong khối chỉ dùng heading từ `####` trở xuống.
4. Nhật ký/bình luận nằm cuối khối, sau dòng `**Nhật ký:**`, mỗi mục MỘT dòng, CHỈ THÊM VÀO CUỐI, không sửa/xóa mục cũ:
   `- [Nam · 2026-11-02 14:30] [Vướng mắc] nội dung`
   Loại cho đầu việc: Kết quả / Vướng mắc / Đề xuất điều chỉnh. Các khối khác: Bình luận.
5. Mỗi mục `##` có dòng `<!-- loại: X -->` cho biết đối tượng mới loại X được thêm vào đâu. Không xóa dòng này.
6. Không lưu bảng tổng hợp hay số liệu thống kê (% hoàn thành, đếm theo trạng thái…) trong file — công cụ tự tính.
7. Không có hạn/deadline theo ngày. Tiến độ theo dõi bằng Trạng thái và Giai đoạn (GD-xx = nội dung nghiên cứu trong mục 7 thuyết minh).
   Ngày giờ chỉ ghi sự việc đã xảy ra (nhật ký, ngày chạy huấn luyện, ngày chốt quyết định, khoảng thời gian dữ liệu).
8. Trạng thái chung (đầu việc, bước pipeline, làm sạch, lưu trữ, lần huấn luyện, bài toán): Chưa bắt đầu / Đang làm / Bị chặn / Hoàn thành / Hủy.
   Nguồn dữ liệu: Chưa thu thập / Đang thu thập / Đã thu thập / Dừng / Hủy.
   Model: Đề xuất / Đang thử / Đã đánh giá / Loại / Được chọn / Hủy.
9. Người: Nam, Lâm. Nguồn nội dung: thuyết minh `TM_final.docx`. "(đề xuất)" = nhóm/Claude đề xuất, chưa có trong thuyết minh.
   "(hiện trạng code)" = lấy từ mã nguồn trong repo. "Chưa có trong thuyết minh" = cần bổ sung.
-->

## 1. Tổng quan
<!-- loại: TQ -->

### TQ-01 Giới thiệu đề tài

**Tên đề tài:** Nghiên cứu các kỹ thuật máy học hiện đại kết hợp đảm bảo an ninh an toàn ứng dụng trong phát triển thử nghiệm hệ thống thông tin hỗ trợ thu thập, lưu trữ tự động dữ liệu mạng xã hội để nhận diện và phân loại cảm xúc và xu hướng của người dùng.

**Nói ngắn gọn:** nghiên cứu các kỹ thuật máy học hiện đại (Transformer tiếng Việt, LLM, mô hình chủ đề) **kết hợp an ninh an toàn** (ẩn danh, bảo mật, học máy bảo toàn quyền riêng tư), rồi áp dụng vào một **hệ thống thông tin thử nghiệm** gồm 3 phần:
1. **Thu thập, lưu trữ tự động** dữ liệu mạng xã hội.
2. **Nhận diện và phân loại cảm xúc** của người dùng.
3. **Nhận diện và phân loại xu hướng** của người dùng.

- **Loại đề tài:** KH-CN cấp trường (người học) — Trường ĐH Điện lực, Khoa Điện toán và Công nghệ số năng lượng.
- **Nhóm thực hiện trên repo:** Nam, Lâm · GV hướng dẫn: ThS. Lê Thanh Trà.
- **Điểm mới:** gộp thu thập – phân tích cảm xúc – phân tích xu hướng – an ninh an toàn thành một hệ thống liền mạch cho tiếng Việt, thay vì làm rời từng phần.

### TQ-02 Mục tiêu

Đề tài phải trả lời được 5 câu hỏi nghiên cứu:

| Mã | Mục tiêu | Câu hỏi nghiên cứu |
|---|---|---|
| MT1 | Tổng quan, chọn phương pháp | — |
| MT2 | Thu thập và lưu trữ tự động | CH3: kiến trúc nào chạy ổn định, mở rộng được? |
| MT3 | Nhận diện, phân loại cảm xúc | CH1: mô hình nào tốt nhất cho tiếng Việt MXH? |
| MT4 | Phát hiện, phân loại xu hướng | CH2: phát hiện xu hướng theo thời gian thế nào? |
| MT5 | An ninh, an toàn, tuân thủ luật | CH4: bảo vệ dữ liệu mà vẫn giữ được độ chính xác? |
| MT6 | Hệ thống tích hợp + dashboard | CH5: ghép được cả 4 phần không? |
| MT7 | Đánh giá thực nghiệm, đề xuất | — |

### TQ-03 Sản phẩm đầu ra

Đề tài bàn giao 5 nhóm sản phẩm:

- **Phần mềm:** prototype hệ thống (thu thập, lưu trữ, phân tích cảm xúc, xu hướng, dashboard, phân quyền).
- **Dữ liệu:** bộ dữ liệu thô, đã làm sạch, đã gán nhãn và tập train/validation/test, kèm tài liệu quy trình.
- **Kết quả thực nghiệm:** bảng so sánh các mô hình (ML cổ điển, học sâu, Transformer).
- **Báo cáo:** báo cáo tổng kết đề tài.
- **Bài báo:** chưa cam kết — thuyết minh chỉ nói "có thể", tùy kết quả.

## 1.1. Giai đoạn (nội dung nghiên cứu — mục 7 thuyết minh)
<!-- loại: GD -->

### GD-01 Khảo sát, tổng quan và xác định bài toán nghiên cứu
- **Kết quả dự kiến:** Báo cáo tổng quan; xác định bài toán, mục tiêu, phạm vi và hướng nghiên cứu.
- **Người thực hiện (theo thuyết minh):** Vũ Vương Lâm

Nghiên cứu các hệ thống thu thập dữ liệu MXH; khảo sát phương pháp lưu trữ, xử lý dữ liệu lớn; nghiên cứu ML, DL, Transformer trong nhận diện cảm xúc và phát hiện xu hướng.

### GD-02 Nghiên cứu cơ sở lý thuyết và công nghệ
- **Kết quả dự kiến:** Tài liệu cơ sở lý thuyết; lựa chọn công nghệ và phương pháp phù hợp.
- **Người thực hiện (theo thuyết minh):** Nguyễn Viết Doanh

NLP, Text Embedding, Machine Learning, Deep Learning, Transformer; Kafka/RabbitMQ, cơ sở dữ liệu và các công nghệ phục vụ thu thập, xử lý dữ liệu.

### GD-03 Thiết kế kiến trúc hệ thống thử nghiệm
- **Kết quả dự kiến:** Sơ đồ kiến trúc hệ thống; thiết kế các module và luồng xử lý dữ liệu.
- **Người thực hiện (theo thuyết minh):** Vũ Hải Nam

Thiết kế kiến trúc thu thập, truyền tải, tiền xử lý, lưu trữ và phân tích dữ liệu; thiết kế các thành phần xử lý cảm xúc và xu hướng.

### GD-04 Xây dựng module thu thập và lưu trữ dữ liệu mạng xã hội
- **Kết quả dự kiến:** Module thu thập dữ liệu; kho dữ liệu thử nghiệm; dữ liệu được lưu trữ tự động.
- **Người thực hiện (theo thuyết minh):** Vũ Vương Lâm

Cơ chế thu thập tự động; chuẩn hóa dữ liệu; lưu trữ dữ liệu thô và dữ liệu đã xử lý; nghiên cứu cơ chế hàng đợi dữ liệu.

### GD-05 Tiền xử lý và xây dựng Dataset
- **Kết quả dự kiến:** Dataset được tiền xử lý và chuẩn hóa; bộ dữ liệu Train/Validation/Test.
- **Người thực hiện (theo thuyết minh):** Nguyễn Viết Doanh

Làm sạch dữ liệu; loại bỏ trùng lặp; chuẩn hóa văn bản; phát hiện ngôn ngữ; Tokenization; xử lý dữ liệu nhiễu; xây dựng Dataset phục vụ huấn luyện, kiểm thử.

### GD-06 Nghiên cứu và thử nghiệm nhận diện, phân loại cảm xúc
- **Kết quả dự kiến:** Các mô hình nhận diện cảm xúc; kết quả Accuracy, Precision, Recall, F1-score.
- **Người thực hiện (theo thuyết minh):** Vũ Hải Nam

Traditional ML (SVM/Logistic Regression); Deep Learning (LSTM/BiLSTM); Transformer (BERT/PhoBERT).

### GD-07 Nghiên cứu và thử nghiệm phát hiện chủ đề, xu hướng
- **Kết quả dự kiến:** Các nhóm chủ đề; danh sách từ khóa/hashtag nổi bật; kết quả phát hiện xu hướng.
- **Người thực hiện (theo thuyết minh):** Vũ Hải Nam

Phân tích tần suất từ khóa, hashtag; LDA, K-means, Embedding-based Clustering, Transformer Embeddings; biến động chủ đề theo thời gian.

### GD-08 Nghiên cứu giải pháp an ninh, an toàn hệ thống và ML Pipeline
- **Kết quả dự kiến:** Giải pháp bảo mật hệ thống; ML Pipeline có cơ chế kiểm tra và giám sát an toàn.
- **Người thực hiện (theo thuyết minh):** Vũ Vương Lâm

Data Validation, Outlier Detection, Dataset Monitoring, Model Validation, Authentication, Authorization/RBAC, API Security, mã hóa và bảo vệ dữ liệu.

### GD-09 Tích hợp và xây dựng hệ thống thử nghiệm
- **Kết quả dự kiến:** Hệ thống thử nghiệm hoàn chỉnh; Dashboard và các chức năng phân tích.
- **Người thực hiện (theo thuyết minh):** Vũ Hải Nam

Tích hợp các module thu thập, xử lý, lưu trữ, ML, phân tích cảm xúc và xu hướng; xây dựng Dashboard.

### GD-10 Đánh giá, thực nghiệm và so sánh kết quả
- **Kết quả dự kiến:** Bộ kết quả thực nghiệm; bảng so sánh mô hình; đánh giá ưu, nhược điểm và khả năng ứng dụng.
- **Người thực hiện (theo thuyết minh):** Nguyễn Viết Doanh

Đánh giá hiệu năng hệ thống; so sánh các mô hình ML; đánh giá độ chính xác phát hiện cảm xúc và xu hướng; đánh giá các cơ chế an ninh, an toàn.

### GD-11 Hoàn thiện báo cáo và đề xuất hướng phát triển
- **Kết quả dự kiến:** Báo cáo tổng kết; kết luận; các đề xuất và hướng phát triển tiếp theo.
- **Người thực hiện (theo thuyết minh):** Vũ Hải Nam, Vũ Vương Lâm, Nguyễn Viết Doanh

Tổng hợp kết quả; đánh giá mức độ đạt mục tiêu; phân tích hạn chế; đề xuất hướng nghiên cứu tiếp theo.

## 2. Nghiệp vụ
<!-- loại: NV -->

### NV-01 Bối cảnh và bài toán

Người Việt bày tỏ cảm xúc, quan điểm rất nhiều trên mạng xã hội (Facebook, YouTube, TikTok, Zalo). Doanh nghiệp và cơ quan quản lý cần nắm được **dư luận đang tích cực hay tiêu cực** và **chủ đề nào đang nổi lên**, nhưng đọc thủ công thì không xuể.

Bài toán gồm 4 phần, bám theo tên đề tài:
1. **Thu thập, lưu trữ tự động** bình luận công khai, liên tục.
2. **Nhận diện và phân loại cảm xúc**: bình luận tích cực, tiêu cực hay trung tính, và mang cảm xúc cụ thể nào (vui, buồn, giận, sợ, ghê tởm, ngạc nhiên).
3. **Phát hiện và phân loại xu hướng**: chủ đề nào đang nổi, đang tăng hay giảm, cảm xúc của người dùng về chủ đề đó đổi ra sao.
4. **Bảo đảm an ninh an toàn** cho cả hệ thống (bảo mật, phân quyền) lẫn quá trình học máy (ẩn danh, học máy bảo toàn quyền riêng tư, chống tấn công mô hình).

Trọng tâm nghiên cứu là **kỹ thuật máy học hiện đại kết hợp an ninh an toàn** (Transformer tiếng Việt, LLM, mô hình chủ đề, differential privacy); hệ thống thông tin là nơi thử nghiệm các kỹ thuật đó.

Khó khăn riêng của tiếng Việt trên mạng: teencode, viết tắt, không dấu, emoji, trộn tiếng Anh, nói mỉa.

### NV-02 Đối tượng

**Ai được lợi từ hệ thống:**
- Doanh nghiệp, tổ chức — theo dõi phản hồi về sản phẩm, thương hiệu.
- Cơ quan quản lý, đơn vị bảo đảm an ninh mạng — nắm dư luận, phát hiện sớm vấn đề.
- Nhóm nghiên cứu, sinh viên, học viên — mô hình tham khảo.

**Ai dùng hệ thống** (đề xuất — thuyết minh chỉ nói "có phân quyền"):

| Vai trò | Làm được gì |
|---|---|
| Quản trị (Admin) | Quản lý tài khoản, cấu hình nguồn thu thập, quản lý mô hình, xem nhật ký |
| Phân tích viên (Analyst) | Đặt từ khóa/video theo dõi, xem dữ liệu chi tiết, chạy phân tích, xuất báo cáo |
| Người xem (Viewer) | Chỉ xem dashboard tổng hợp |

**Đối tượng bị thu thập dữ liệu:** người dùng mạng xã hội để lại bình luận công khai — cần được ẩn danh (xem NV-09).

### NV-03 Phạm vi

**Làm:**
- Văn bản tiếng Việt (bình luận, bài đăng công khai).
- Thu thập qua API chính thức, theo từ khóa, video/kênh, khoảng thời gian.
- Cảm xúc hai tầng: quan điểm 3 lớp tích cực / tiêu cực / trung tính (mục 6.6 thuyết minh) và cảm xúc chi tiết 7 nhãn theo UIT-VSMEC (đã chốt QD-04).
- Xu hướng: phát hiện chủ đề đang nổi và phân loại xu hướng (mới nổi / đang tăng / đang giảm / ổn định), gắn với cảm xúc. Chỉ phân tích ở mức cộng đồng, không lập hồ sơ từng người dùng (đã chốt QD-05).
- An ninh an toàn 4 lớp (dữ liệu, ứng dụng, API, mô hình) và thử nghiệm học máy bảo toàn quyền riêng tư bằng differential privacy (đã chốt QD-06); federated learning chỉ mô phỏng, tùy chọn.
- Prototype có dashboard.

**Không làm (hướng phát triển sau):** phân tích thời gian thực, video/âm thanh/hình ảnh, cảm xúc theo khía cạnh (ABSA), học liên kết triển khai thật, cảnh báo khủng hoảng.

**Chưa chốt:**
- Nền tảng cụ thể — hiện code làm YouTube (chạy được) và TikTok (chờ key API).
- Lĩnh vực/chủ đề áp dụng (ví dụ giá điện, giá vàng, thương hiệu…).

### NV-04 Khảo sát

**Mục đích:** chốt các yêu cầu thuyết minh còn để ngỏ trước khi thiết kế chi tiết.

**Hỏi ai:** GV hướng dẫn; chuyên gia AI/dữ liệu; đơn vị dự kiến dùng thử (đề xuất).

**Cách làm:** phỏng vấn hoặc phiếu hỏi theo khung 5 nhóm trong `docs/business_analysis_and_survey_framework.md`.

| Nhóm | Câu hỏi chính cần chốt |
|---|---|
| Thu thập | Nền tảng nào? Theo từ khóa hay kênh? Bao nhiêu bản ghi/ngày? Quét bao lâu một lần? Có cần xử lý video/âm thanh? |
| Phân tích | Cảm xúc mấy lớp? Mức chính xác tối thiểu? Có cần phát hiện mỉa mai, spam? Thế nào thì gọi là "xu hướng"? |
| Bảo mật, pháp lý | Có cần che thông tin cá nhân trong nội dung? Vai trò người dùng nào? Lưu dữ liệu bao lâu? |
| Lưu trữ, hiệu năng | Có cần CSDL vector? Dashboard tải nhanh cỡ nào? |
| Đầu ra | Dashboard cần biểu đồ gì? Có cần cảnh báo, xuất Excel/PDF? |

**Kết quả cần có:** biên bản trả lời → cập nhật NV-03 Phạm vi, NV-08 Yêu cầu chất lượng và ghi vào Nhật ký quyết định.

### NV-05 Dữ liệu

| Nguồn | Nội dung | Cách lấy | Tình trạng |
|---|---|---|---|
| YouTube | Bình luận công khai dưới video | YouTube Data API v3 | Đang chạy |
| TikTok | Bình luận công khai | TikTok Research API | Chờ cấp key |
| UIT-VSMEC, UIT-VSFC | Bộ dữ liệu có sẵn nhãn cảm xúc | Tải về | Chưa tải |

**Mỗi bản ghi lưu:** nội dung, thời điểm đăng, nền tảng, mã bài; tác giả chỉ lưu dạng đã băm. Cần bổ sung: hashtag, lượt thích, chủ đề/video gốc.

**Chưa chốt:** khối lượng cần thu, cách gán nhãn (ai gán, bao nhiêu mẫu).

### NV-06 Quy trình nghiệp vụ

1. **Cấu hình** — Phân tích viên nhập từ khóa hoặc video cần theo dõi.
2. **Thu thập** — hệ thống định kỳ lấy bình luận mới, băm danh tính tác giả, lưu vào kho.
3. **Làm sạch** — chuẩn hóa chữ, xử lý teencode/emoji, lọc trùng, lọc spam.
4. **Gán nhãn & huấn luyện** — tạo bộ dữ liệu có nhãn, huấn luyện và so sánh mô hình.
5. **Phân tích** — mô hình được chọn gán nhãn cảm xúc cho dữ liệu mới; gom chủ đề theo thời gian.
6. **Theo dõi** — xem dashboard cảm xúc, xu hướng; xuất báo cáo.
7. **Giám sát** — kiểm tra dữ liệu bất thường, ghi nhật ký truy cập.

Chi tiết từng bước kỹ thuật: xem mục 4. Pipeline.

### NV-07 Chức năng

| Mã | Chức năng | Người dùng | Hiện có |
|---|---|---|---|
| UC-01 | Đăng nhập, phân quyền | Tất cả | Chưa |
| UC-02 | Cấu hình nguồn, từ khóa | Phân tích viên | Có |
| UC-03 | Thu thập tự động, theo dõi trạng thái thu thập | Hệ thống, Quản trị | Có thu thập; chưa có màn hình theo dõi |
| UC-04 | Tìm kiếm, lọc dữ liệu | Phân tích viên | Một phần |
| UC-05 | Phân tích cảm xúc | Hệ thống | Chưa |
| UC-06 | Phát hiện chủ đề, xu hướng | Hệ thống | Chưa |
| UC-07 | Dashboard | Người xem | Mới có số liệu tổng |
| UC-08 | Nhật ký hoạt động, giám sát | Quản trị | Chưa |

### NV-08 Yêu cầu chất lượng

| Khía cạnh | Đo bằng |
|---|---|
| Độ chính xác cảm xúc | Accuracy, Precision, Recall, **F1-macro** (vì dữ liệu lệch lớp) |
| Phát hiện xu hướng | Precision/Recall, độ trễ phát hiện |
| Hiệu năng | Thời gian thu thập, throughput, độ trễ, thời gian suy luận, CPU/RAM/GPU |
| Bảo mật | Tỉ lệ phát hiện/ngăn chặn tấn công, báo nhầm/bỏ sót |
| Vận hành | Chạy liên tục ổn định, thêm nền tảng mới dễ dàng |

Con số mục tiêu: thuyết minh cố ý **không đặt trước**, sẽ xác định sau thực nghiệm.

### NV-09 Bảo vệ dữ liệu cá nhân và pháp lý

Người bình luận không biết dữ liệu của họ được thu thập, nên hệ thống phải tự bảo vệ họ:

- **Căn cứ:** Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 (hiệu lực 01/01/2026). Cảm xúc, quan điểm có thể là dữ liệu nhạy cảm.
- **Ẩn danh:** băm danh tính tác giả ngay khi thu thập, không lưu tên hay ID gốc — *đã làm*. Che số điện thoại, email, tên riêng trong nội dung — *chưa làm (đề xuất)*.
- **Điều khoản nền tảng:** chỉ lấy dữ liệu công khai qua API chính thức, đúng quota (YouTube 10.000 đơn vị/ngày) và điều khoản của từng nền tảng.
- **Chưa chốt:** cơ sở pháp lý để xử lý (xin đồng ý hay ngoại lệ nghiên cứu), thời gian lưu dữ liệu, cách xử lý yêu cầu xóa.

### NV-10 An ninh hệ thống

| Lớp | Biện pháp | Hiện có |
|---|---|---|
| Truy cập | Đăng nhập, phân quyền theo vai trò | Chưa |
| Dữ liệu | Mã hóa khi truyền (HTTPS) và khi lưu, sao lưu, giữ bí mật API key/salt | Chỉ giữ bí mật trong `.env` |
| Ứng dụng & API | Kiểm tra đầu vào, chống SQL injection/XSS/CSRF, giới hạn tần suất gọi | Có kiểm tra đầu vào, dùng ORM |
| Lưu vết | Ghi nhật ký ai làm gì, giám sát hệ thống | Chưa |
| Mô hình | Kiểm tra dữ liệu đầu vào, phát hiện bất thường, kiểm định mô hình; chống đầu độc dữ liệu, đánh cắp mô hình | Chưa |
| Quyền riêng tư khi học | Thử differential privacy (DP-SGD), đo đánh đổi với độ chính xác; federated learning mô phỏng nếu kịp | Chưa — trong phạm vi theo QD-06, đầu việc T-44, T-48 |

### NV-11 Vấn đề còn mở

Các điểm cần chốt trước khi đi sâu (theo dõi ở T-38, chốt xong ghi vào Nhật ký quyết định):

1. Nền tảng và lĩnh vực áp dụng.
2. Vai trò người dùng và quyền.
3. Cách gán nhãn: ai gán, bao nhiêu mẫu, đo độ đồng thuận thế nào. *(Tập nhãn đã chốt ở QD-04.)*
4. Tiêu chí định lượng thế nào là một xu hướng (ngưỡng tăng trưởng, số người tham gia, khung thời gian). *(Nghĩa của "xu hướng" đã chốt ở QD-05.)*
5. ~~Có làm differential privacy / federated learning không.~~ Đã chốt ở QD-06.
6. Cơ sở pháp lý, thời gian lưu dữ liệu.
7. Phân công lại phần việc thuyết minh giao cho Nguyễn Viết Doanh.
8. ~~Hiểu "xu hướng của người dùng" theo nghĩa nào.~~ Đã chốt ở QD-05.

## 3. Đầu việc
<!-- loại: T -->

### T-01 Khảo sát các hệ thống thu thập dữ liệu mạng xã hội
- **Mô tả:** Khảo sát các hệ thống/công cụ thu thập, social listening và kiến trúc thu thập (API chính thức, crawler, hàng đợi).
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-01
- **Trạng thái:** Đang làm
- **Liên kết:** MT1, CH3, PL-01

### T-02 Khảo sát phương pháp lưu trữ, xử lý dữ liệu lớn
- **Mô tả:** So sánh các phương án lưu trữ và xử lý dữ liệu lớn phù hợp quy mô đề tài.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-01
- **Trạng thái:** Đang làm
- **Liên kết:** MT1, CH3, PL-04

### T-03 Khảo sát kỹ thuật ML, DL, Transformer cho cảm xúc và xu hướng
- **Mô tả:** Tổng hợp công trình trong và ngoài nước (PhoBERT, ViSoBERT, UIT-VSMEC, BERTopic, BERTrend…).
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-01
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT1, CH1, CH2

### T-04 Viết báo cáo tổng quan, chốt bài toán, mục tiêu, phạm vi
- **Mô tả:** Báo cáo tổng quan; chốt nền tảng, miền dữ liệu và các mục "Chưa có trong thuyết minh".
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-01
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT1, NV-03

### T-05 Nghiên cứu NLP, Text Embedding, ML, DL, Transformer
- **Mô tả:** Tài liệu cơ sở lý thuyết. Thuyết minh giao Nguyễn Viết Doanh — cần phân công lại cho Nam hoặc Lâm.
- **Người phụ trách:** 
- **Giai đoạn:** GD-02
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT1

### T-06 Nghiên cứu hàng đợi (Kafka/RabbitMQ), CSDL và chọn công nghệ
- **Mô tả:** Lựa chọn công nghệ thu thập, truyền tải, lưu trữ. Thuyết minh giao Nguyễn Viết Doanh — cần phân công lại.
- **Người phụ trách:** 
- **Giai đoạn:** GD-02
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT2, CH3, PL-04

### T-07 Thiết kế kiến trúc thu thập, truyền tải, tiền xử lý, lưu trữ, phân tích
- **Mô tả:** Sơ đồ kiến trúc tổng thể và luồng xử lý dữ liệu.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-03
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT6, CH3, CH5

### T-08 Thiết kế các module xử lý cảm xúc và xu hướng
- **Mô tả:** Thiết kế thành phần phân tích cảm xúc, xu hướng và cách tích hợp vào pipeline.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-03
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, MT4, PL-07

### T-09 Thu thập bình luận YouTube theo video và theo từ khóa
- **Mô tả:** Hiện trạng code: collector/youtube_client.py, collector/pipeline.py; CLI `python -m collector run|search`.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-04
- **Trạng thái:** Hoàn thành
- **Liên kết:** MT2, PL-01, DS-01

### T-10 Lập lịch thu thập tự động, cấu hình nguồn qua giao diện
- **Mô tả:** Hiện trạng code: collector/scheduler.py (APScheduler) đọc bảng search_queries, tracked_videos; tab "Cấu hình thu thập" trên frontend.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-04
- **Trạng thái:** Hoàn thành
- **Liên kết:** MT2, PL-01, UC-02

### T-11 Thu thập TikTok qua Research API
- **Mô tả:** Code đã viết (collector/tiktok_client.py) nhưng chưa kiểm tra bằng key thật; chưa rõ trường định danh tác giả bình luận.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-04
- **Trạng thái:** Bị chặn
- **Liên kết:** MT2, PL-01, DS-02

### T-12 Chuẩn hóa và lưu dữ liệu thô, dữ liệu đã xử lý
- **Mô tả:** Dữ liệu thô đã lưu (raw_posts); còn thiếu lưu metadata, hashtag và dữ liệu đã xử lý.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-04
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT2, PL-04, ST-01

### T-13 Nghiên cứu và thử nghiệm cơ chế hàng đợi dữ liệu
- **Mô tả:** Hàng đợi giữa thu thập và xử lý theo kiến trúc thuyết minh.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-04
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT2, CH3, PL-04

### T-14 Làm sạch, chuẩn hóa văn bản, phát hiện ngôn ngữ, tokenization
- **Mô tả:** Thực hiện các bước CL-xx. Thuyết minh giao Nguyễn Viết Doanh — cần phân công lại.
- **Người phụ trách:** 
- **Giai đoạn:** GD-05
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, PL-02

### T-15 Xử lý dữ liệu nhiễu, spam, bot
- **Mô tả:** Lọc spam, seeding, nội dung trùng lặp. Cần phân công.
- **Người phụ trách:** 
- **Giai đoạn:** GD-05
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, PL-02, CL-07

### T-16 Gán nhãn dữ liệu
- **Mô tả:** Tạo Labeled Dataset (mục 8). Cách gán nhãn, số mẫu, người gán, đo đồng thuận: Chưa có trong thuyết minh.
- **Người phụ trách:** 
- **Giai đoạn:** GD-05
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, PL-03

### T-17 Xây dựng bộ Train / Validation / Test
- **Mô tả:** Chia dữ liệu, thống kê phân bố nhãn, lưu phiên bản dataset.
- **Người phụ trách:** 
- **Giai đoạn:** GD-05
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, PL-03, ST-04

### T-18 Thử nghiệm Traditional ML (SVM, Logistic Regression)
- **Mô tả:** Baseline cho bài toán cảm xúc; ghi mỗi lần chạy thành một R-xx.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-06
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, CH1, PL-05, BT-01

### T-19 Thử nghiệm Deep Learning (LSTM, BiLSTM)
- **Mô tả:** Mô hình học sâu cho bài toán cảm xúc.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-06
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, CH1, PL-05, BT-01

### T-20 Thử nghiệm Transformer (BERT, PhoBERT)
- **Mô tả:** Fine-tune BERT, PhoBERT, ViSoBERT cho BT-01 (quan điểm 3 lớp); ghi mỗi lần chạy thành một R-xx.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-06
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, CH1, PL-05, BT-01

### T-21 Đánh giá mô hình cảm xúc (Accuracy, Precision, Recall, F1)
- **Mô tả:** So sánh các lần huấn luyện, chọn model cho BT-01.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-06
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, MT7, PL-06, BT-01

### T-22 Phân tích tần suất từ khóa, hashtag
- **Mô tả:** Thống kê theo thời gian, phát hiện từ khóa/hashtag nổi bật.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-07
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT4, CH2, PL-07, BT-02

### T-23 Thử nghiệm LDA, K-means, Embedding-based Clustering
- **Mô tả:** Gom cụm chủ đề, so sánh phương pháp.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-07
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT4, CH2, PL-05, BT-02

### T-24 Phân tích biến động chủ đề theo thời gian
- **Mô tả:** Phát hiện chủ đề mới, mức tăng/giảm quan tâm, kết hợp với cảm xúc.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-07
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT4, CH2, PL-07, BT-02

### T-25 Ẩn danh định danh người dùng ngay khi thu thập
- **Mô tả:** Hiện trạng code: security/anonymize.py — SHA-256 + salt, gọi trong collector trước khi ghi DB.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Hoàn thành
- **Liên kết:** MT5, NV-09, PL-01

### T-26 Xác thực và phân quyền (Authentication, Authorization/RBAC)
- **Mô tả:** Đăng nhập, vai trò, phân quyền API và giao diện.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, NV-10, UC-01

### T-27 Bảo mật API
- **Mô tả:** Input/request validation, rate limiting, CORS, HTTPS.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, NV-10

### T-28 Mã hóa và bảo vệ dữ liệu
- **Mô tả:** Mã hóa kết nối và dữ liệu lưu, quản lý bí mật, sao lưu.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, NV-10, ST-01

### T-29 An toàn ML Pipeline (Data Validation, Outlier Detection, Dataset Monitoring, Model Validation)
- **Mô tả:** Cơ chế kiểm tra và giám sát an toàn cho pipeline học máy.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, NV-10, PL-08

### T-30 Ghi nhật ký hoạt động (Audit Logging) và giám sát
- **Mô tả:** Theo mục 8 thuyết minh.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, NV-10, UC-08

### T-31 Tích hợp các module thành hệ thống thử nghiệm
- **Mô tả:** Kết nối thu thập, xử lý, lưu trữ, ML, phân tích cảm xúc và xu hướng.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-09
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT6, CH5, PL-07

### T-32 Dashboard trực quan hóa
- **Mô tả:** Hiện trạng code: frontend React + Ant Design mới có số liệu tổng, danh sách dữ liệu, cấu hình thu thập.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-09
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT6, UC-07

### T-33 Đánh giá hiệu năng hệ thống
- **Mô tả:** Thời gian thu thập, throughput, latency, thời gian suy luận, CPU/RAM/GPU. Thuyết minh giao Nguyễn Viết Doanh — cần phân công lại.
- **Người phụ trách:** 
- **Giai đoạn:** GD-10
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT7, NV-08

### T-34 So sánh mô hình và đánh giá độ chính xác cảm xúc, xu hướng
- **Mô tả:** Bảng so sánh mô hình; đánh giá ưu, nhược điểm. Cần phân công.
- **Người phụ trách:** 
- **Giai đoạn:** GD-10
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT7, CH1, CH2, PL-06

### T-35 Đánh giá các cơ chế an ninh, an toàn
- **Mô tả:** Kịch bản phát hiện → bảo vệ → ghi nhật ký → cảnh báo; tỉ lệ False Positive/Negative. Cần phân công.
- **Người phụ trách:** 
- **Giai đoạn:** GD-10
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT7, CH4

### T-36 Tổng hợp kết quả và viết báo cáo tổng kết
- **Mô tả:** Báo cáo tổng kết; đánh giá mức độ đạt mục tiêu; phân tích hạn chế.
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-11
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT7

### T-37 Đề xuất hướng phát triển
- **Mô tả:** Theo các hướng ở mục 4.3.5 thuyết minh.
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-11
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT7

### T-38 Bổ sung các thông tin còn thiếu trong thuyết minh
- **Mô tả:** (đề xuất) Chốt các vấn đề còn mở ở NV-11 với GV hướng dẫn (qua khảo sát NV-04).
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-01
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** NV-11, NV-03, NV-09

### T-39 Thử nghiệm nhận diện cảm xúc 7 nhãn trên UIT-VSMEC
- **Mô tả:** PhoBERT, ViSoBERT cho BT-03; so với baseline. (QD-04)
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-06
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, CH1, BT-03, PL-05

### T-40 Thử LLM zero-shot / few-shot cho cảm xúc
- **Mô tả:** Nêu trong CH1 và MT3; ưu tiên LLM chạy local để không gửi dữ liệu ra ngoài. (đề xuất)
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-06
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, CH1, M-11, BT-01, BT-03

### T-41 Phân tích lỗi: teencode, emoji, không dấu, mỉa mai
- **Mô tả:** MT3 yêu cầu xử lý các đặc thù này; đo F1 trên từng nhóm lỗi, thử tiền xử lý tương ứng. (đề xuất)
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-06
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT3, CH1, PL-06

### T-42 Phân loại xu hướng (mới nổi / tăng / giảm / ổn định) gắn cảm xúc
- **Mô tả:** Làm BT-04 trên kết quả của BT-02 và BT-01/BT-03. (QD-05)
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-07
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT4, CH2, BT-04, PL-07

### T-43 Che thông tin cá nhân trong nội dung bình luận
- **Mô tả:** Thực hiện CL-08 trước khi dữ liệu vào dataset hoặc được công bố. (đề xuất)
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-05
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, NV-09, CL-08, PL-02

### T-44 Thử nghiệm DP-SGD và đánh đổi riêng tư – độ chính xác
- **Mô tả:** Huấn luyện M-19 với vài mức ε, vẽ đường ε – F1-macro. Trả lời trực tiếp CH4. (QD-06)
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, CH4, M-19, PL-05

### T-45 Kiểm thử tấn công mô hình
- **Mô tả:** Biến thể đối kháng (teencode, bỏ dấu), đầu độc dữ liệu huấn luyện, trích xuất mô hình qua API dự đoán. (đề xuất)
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, CH4, NV-10, PL-06

### T-46 Rà soát tuân thủ Luật 91/2025/QH15
- **Mô tả:** Đánh giá tác động xử lý dữ liệu; chốt cơ sở pháp lý, thời gian lưu, cách xử lý yêu cầu xóa. (đề xuất)
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, NV-09, NV-11

### T-47 Thực hiện khảo sát yêu cầu
- **Mô tả:** Theo NV-04; ghi kết quả vào Nhật ký quyết định. (đề xuất)
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-01
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT1, NV-04, NV-11

### T-48 Mô phỏng học liên kết (federated learning)
- **Mô tả:** Tùy chọn theo QD-06: chỉ làm nếu còn thời gian; mô phỏng nhiều bên trên một máy (M-20).
- **Người phụ trách:** Lâm
- **Giai đoạn:** GD-08
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** MT5, CH4, M-20

### T-49 Cập nhật thuyết minh theo các quyết định đã chốt
- **Mô tả:** Sửa mục 6.6 (thêm cảm xúc 7 nhãn — QD-04), mục 6.7 (định nghĩa xu hướng — QD-05), mục 7 (thêm nội dung differential privacy — QD-06).
- **Người phụ trách:** Nam
- **Giai đoạn:** GD-01
- **Trạng thái:** Chưa bắt đầu
- **Liên kết:** QD-04, QD-05, QD-06, NV-11

## 4. Pipeline
<!-- loại: PL -->

### PL-01 Thu thập
- **Đầu vào:** API nền tảng; từ khóa, video theo dõi cấu hình trên giao diện
- **Đầu ra:** Bản ghi bình luận thô (bảng raw_posts), tác giả đã băm
- **Công cụ/thuật toán:** YouTube Data API v3, httpx, APScheduler (hiện trạng code)
- **Model đang chọn:** Không áp dụng
- **Trạng thái:** Đang làm
- **An ninh an toàn:** Giữ bí mật API key; tôn trọng quota và rate limit; chỉ lấy nội dung công khai; băm danh tính tác giả ngay khi thu thập (đề xuất)

### PL-02 Làm sạch / tiền xử lý
- **Đầu vào:** Bản ghi thô
- **Đầu ra:** Văn bản đã làm sạch, chuẩn hóa (Clean Dataset)
- **Công cụ/thuật toán:** Xem các bước CL-xx
- **Model đang chọn:** Không áp dụng
- **Trạng thái:** Chưa bắt đầu
- **An ninh an toàn:** Che thông tin cá nhân trong nội dung (CL-08); lọc spam, bot và dữ liệu bất thường có thể là đầu độc dữ liệu (đề xuất)

### PL-03 Gán nhãn
- **Đầu vào:** Văn bản đã làm sạch
- **Đầu ra:** Labeled Dataset; tập Train / Validation / Test
- **Công cụ/thuật toán:** Chưa có trong thuyết minh. (đề xuất) Label Studio; LLM gán nhãn sơ bộ, người duyệt lại; đo Cohen's Kappa
- **Model đang chọn:** Không áp dụng
- **Trạng thái:** Chưa bắt đầu
- **An ninh an toàn:** Chỉ người được phân quyền gán nhãn; gán chéo để phát hiện nhãn sai; người gán không thấy danh tính tác giả (đề xuất)

### PL-04 Lưu trữ
- **Đầu vào:** Dữ liệu thô, dữ liệu đã xử lý, nhãn, kết quả phân tích
- **Đầu ra:** Kho dữ liệu thử nghiệm
- **Công cụ/thuật toán:** PostgreSQL 16 (hiện trạng code); hàng đợi Kafka/RabbitMQ theo kiến trúc thuyết minh
- **Model đang chọn:** Không áp dụng
- **Trạng thái:** Đang làm
- **An ninh an toàn:** Mã hóa khi truyền và khi lưu; phân quyền truy cập; sao lưu; giới hạn thời gian lưu (đề xuất)

### PL-05 Huấn luyện
- **Đầu vào:** Tập Train / Validation
- **Đầu ra:** Mô hình đã huấn luyện (mỗi lần chạy ghi một R-xx)
- **Công cụ/thuật toán:** Xem các model M-xx; Hugging Face Transformers, scikit-learn; Opacus cho DP-SGD (đề xuất)
- **Model đang chọn:** 
- **Trạng thái:** Chưa bắt đầu
- **An ninh an toàn:** Kiểm tra dữ liệu huấn luyện (data validation, outlier); thử huấn luyện với differential privacy (DP-SGD) (đề xuất)

### PL-06 Đánh giá
- **Đầu vào:** Tập Test, mô hình đã huấn luyện
- **Đầu ra:** Accuracy, Precision, Recall, F1 (macro), confusion matrix
- **Công cụ/thuật toán:** Theo mục 6.6, 6.10 thuyết minh
- **Model đang chọn:** 
- **Trạng thái:** Chưa bắt đầu
- **An ninh an toàn:** Kiểm thử độ bền trước biến thể teencode, không dấu (adversarial); đo đánh đổi riêng tư – độ chính xác (đề xuất)

### PL-07 Dự đoán / ứng dụng
- **Đầu vào:** Bản ghi mới đã làm sạch
- **Đầu ra:** Nhãn cảm xúc (bảng analysis_results), chủ đề và xu hướng, dashboard
- **Công cụ/thuật toán:** Xem các bài toán BT-xx
- **Model đang chọn:** 
- **Trạng thái:** Chưa bắt đầu
- **An ninh an toàn:** API dự đoán phải xác thực và giới hạn tần suất (chống trích xuất mô hình); dashboard chỉ hiện số liệu tổng hợp (đề xuất)

### PL-08 Giám sát
- **Đầu vào:** Dữ liệu vào, kết quả dự đoán, nhật ký hệ thống
- **Đầu ra:** Cảnh báo bất thường, báo cáo giám sát
- **Công cụ/thuật toán:** Dataset Monitoring, Outlier Detection, Model Validation, Monitoring (mục 6.8, 7, 8)
- **Model đang chọn:** Không áp dụng
- **Trạng thái:** Chưa bắt đầu
- **An ninh an toàn:** Ghi nhật ký truy cập; theo dõi trôi dữ liệu và bất thường; cảnh báo (đề xuất)

## 4.1. Nguồn dữ liệu
<!-- loại: DS -->

### DS-01 YouTube — bình luận công khai
- **Nền tảng:** YouTube
- **Phạm vi:** Video tìm theo từ khóa và video theo dõi cố định, cấu hình trên giao diện (bảng search_queries, tracked_videos)
- **Cách lấy:** API chính thức (YouTube Data API v3)
- **Tần suất:** Mỗi 60 phút (COLLECTOR_POLL_INTERVAL_MINUTES, mặc định)
- **Ghi chú pháp lý:** YouTube API Services Terms; quota 10.000 unit/ngày; chỉ nội dung công khai; tác giả băm SHA-256 + salt
- **Trạng thái:** Đang thu thập
- **Số bản ghi:** Chưa cập nhật
- **Khoảng thời gian dữ liệu:** Chưa cập nhật
- **Nơi lưu:** ST-01

Trạng thái thực tế, số bản ghi và khoảng thời gian cần Lâm cập nhật từ DB.

### DS-02 TikTok — bình luận công khai
- **Nền tảng:** TikTok
- **Phạm vi:** Video theo dõi cố định (cấu hình trên giao diện)
- **Cách lấy:** API chính thức (TikTok Research API)
- **Tần suất:** Theo scheduler chung
- **Ghi chú pháp lý:** Cần đăng ký và được duyệt Research API; Research API Terms of Service
- **Trạng thái:** Chưa thu thập
- **Số bản ghi:** 0
- **Khoảng thời gian dữ liệu:** 
- **Nơi lưu:** ST-01

### DS-03 UIT-VSMEC — bộ dữ liệu công khai nhận diện cảm xúc
- **Nền tảng:** Bộ dữ liệu công khai (trích dẫn [6] trong thuyết minh)
- **Phạm vi:** Bình luận MXH tiếng Việt có nhãn cảm xúc
- **Cách lấy:** Tải bộ dữ liệu
- **Tần suất:** Một lần
- **Ghi chú pháp lý:** Kiểm tra điều kiện sử dụng của nhóm tác giả
- **Trạng thái:** Chưa thu thập
- **Số bản ghi:** 
- **Khoảng thời gian dữ liệu:** 
- **Nơi lưu:** ST-04

### DS-04 UIT-VSFC — bộ dữ liệu công khai phản hồi sinh viên
- **Nền tảng:** Bộ dữ liệu công khai (mục 4.3.2 thuyết minh)
- **Phạm vi:** Phản hồi sinh viên có nhãn cảm xúc
- **Cách lấy:** Tải bộ dữ liệu
- **Tần suất:** Một lần
- **Ghi chú pháp lý:** Kiểm tra điều kiện sử dụng của nhóm tác giả
- **Trạng thái:** Chưa thu thập
- **Số bản ghi:** 
- **Khoảng thời gian dữ liệu:** 
- **Nơi lưu:** ST-04

## 4.2. Làm sạch dữ liệu
<!-- loại: CL -->

### CL-01 Loại bỏ trùng lặp
- **Thuật toán/thư viện:** Ràng buộc duy nhất (nền tảng, mã bình luận) khi ghi DB (hiện trạng code); trùng nội dung gần giống: Chưa có trong thuyết minh
- **Tham số:** 
- **Áp dụng cho nguồn:** DS-01, DS-02
- **Số bản ghi trước:** 
- **Số bản ghi sau:** 
- **Trạng thái:** Đang làm

### CL-02 Chuẩn hóa Unicode, chữ hoa/thường
- **Thuật toán/thư viện:** Chuẩn hóa NFC, chuẩn hóa vị trí dấu thanh (đề xuất)
- **Tham số:** 
- **Áp dụng cho nguồn:** 
- **Số bản ghi trước:** 
- **Số bản ghi sau:** 
- **Trạng thái:** Chưa bắt đầu

### CL-03 Xử lý URL, hashtag, mention, emoji, ký tự đặc biệt
- **Thuật toán/thư viện:** Chưa có trong thuyết minh
- **Tham số:** 
- **Áp dụng cho nguồn:** 
- **Số bản ghi trước:** 
- **Số bản ghi sau:** 
- **Trạng thái:** Chưa bắt đầu

### CL-04 Xử lý teencode, viết tắt, tiếng lóng, sai chính tả, không dấu
- **Thuật toán/thư viện:** Từ điển chuẩn hóa (đề xuất)
- **Tham số:** 
- **Áp dụng cho nguồn:** 
- **Số bản ghi trước:** 
- **Số bản ghi sau:** 
- **Trạng thái:** Chưa bắt đầu

### CL-05 Tách từ (tokenization)
- **Thuật toán/thư viện:** VnCoreNLP hoặc underthesea (đề xuất; PhoBERT yêu cầu đầu vào đã tách từ)
- **Tham số:** 
- **Áp dụng cho nguồn:** 
- **Số bản ghi trước:** 
- **Số bản ghi sau:** 
- **Trạng thái:** Chưa bắt đầu

### CL-06 Phát hiện ngôn ngữ
- **Thuật toán/thư viện:** Chưa có trong thuyết minh
- **Tham số:** 
- **Áp dụng cho nguồn:** 
- **Số bản ghi trước:** 
- **Số bản ghi sau:** 
- **Trạng thái:** Chưa bắt đầu

### CL-07 Lọc spam, bot, dữ liệu không phù hợp
- **Thuật toán/thư viện:** Chưa có trong thuyết minh
- **Tham số:** 
- **Áp dụng cho nguồn:** 
- **Số bản ghi trước:** 
- **Số bản ghi sau:** 
- **Trạng thái:** Chưa bắt đầu

### CL-08 Che thông tin cá nhân trong nội dung
- **Thuật toán/thư viện:** (đề xuất) Biểu thức chính quy cho số điện thoại, email; nhận diện tên riêng
- **Tham số:** 
- **Áp dụng cho nguồn:** 
- **Số bản ghi trước:** 
- **Số bản ghi sau:** 
- **Trạng thái:** Chưa bắt đầu

## 4.3. Lưu trữ
<!-- loại: ST -->

### ST-01 PostgreSQL — dữ liệu thô
- **Hệ lưu trữ:** PostgreSQL 16 (Docker, container sss_postgres)
- **Định dạng:** Bảng quan hệ
- **Schema:** raw_posts(id, platform, post_id, author_hash, content, posted_at, collected_at); duy nhất theo (platform, post_id)
- **Vị trí:** Docker volume pgdata trên máy chạy
- **Thời gian giữ:** Chưa có trong thuyết minh
- **Sao lưu:** Chưa có
- **Kiểm soát truy cập:** Tài khoản DB trong .env; API đọc dữ liệu chưa có xác thực
- **Ẩn danh:** author_hash = SHA-256(salt + định danh tác giả)
- **Trạng thái:** Đang làm

### ST-02 PostgreSQL — cấu hình thu thập
- **Hệ lưu trữ:** PostgreSQL 16
- **Định dạng:** Bảng quan hệ
- **Schema:** search_queries(id, platform, query, max_videos, published_within_days, enabled, created_at); tracked_videos(id, platform, video_id, label, enabled, created_at)
- **Vị trí:** Cùng CSDL với ST-01
- **Thời gian giữ:** Không giới hạn
- **Sao lưu:** Chưa có
- **Kiểm soát truy cập:** API cấu hình chưa có xác thực
- **Ẩn danh:** Không chứa dữ liệu cá nhân
- **Trạng thái:** Hoàn thành

### ST-03 PostgreSQL — kết quả phân tích cảm xúc
- **Hệ lưu trữ:** PostgreSQL 16
- **Định dạng:** Bảng quan hệ
- **Schema:** analysis_results(id, raw_post_id, sentiment_label, sentiment_score, model_name, analyzed_at)
- **Vị trí:** Cùng CSDL với ST-01
- **Thời gian giữ:** Chưa có trong thuyết minh
- **Sao lưu:** Chưa có
- **Kiểm soát truy cập:** Chưa có
- **Ẩn danh:** Liên kết tới raw_posts, không chứa định danh gốc
- **Trạng thái:** Chưa bắt đầu

Bảng đã tạo nhưng chưa có thành phần nào ghi vào.

### ST-04 Bộ dữ liệu huấn luyện (Train / Validation / Test)
- **Hệ lưu trữ:** Chưa có trong thuyết minh
- **Định dạng:** 
- **Schema:** 
- **Vị trí:** Thư mục data/ (không commit dữ liệu thô — hiện trạng .gitignore)
- **Thời gian giữ:** Chưa có trong thuyết minh
- **Sao lưu:** 
- **Kiểm soát truy cập:** 
- **Ẩn danh:** Cần che PII trong nội dung (CL-08)
- **Trạng thái:** Chưa bắt đầu

## 4.4. Model
<!-- loại: M -->

### M-01 TF-IDF + Logistic Regression
- **Loại:** Baseline cổ điển
- **Bài toán phù hợp:** BT-01
- **Lý do chọn:** Mô hình cơ sở theo mục 6.5 và nội dung 6 của thuyết minh
- **Trạng thái:** Đề xuất

### M-02 TF-IDF + SVM
- **Loại:** Baseline cổ điển
- **Bài toán phù hợp:** BT-01
- **Lý do chọn:** Mô hình cơ sở theo mục 6.5 và nội dung 6 của thuyết minh
- **Trạng thái:** Đề xuất

### M-03 Naive Bayes
- **Loại:** Baseline cổ điển
- **Bài toán phù hợp:** BT-01
- **Lý do chọn:** Nhóm 1 – mô hình truyền thống, mục 6.5
- **Trạng thái:** Đề xuất

### M-04 Random Forest
- **Loại:** Baseline cổ điển
- **Bài toán phù hợp:** BT-01
- **Lý do chọn:** Nhóm 1 – mô hình truyền thống, mục 6.5
- **Trạng thái:** Đề xuất

### M-05 CNN
- **Loại:** Deep learning
- **Bài toán phù hợp:** BT-01
- **Lý do chọn:** Nhóm 2 – Deep Learning, mục 6.5
- **Trạng thái:** Đề xuất

### M-06 LSTM / BiLSTM
- **Loại:** Deep learning
- **Bài toán phù hợp:** BT-01, BT-03
- **Lý do chọn:** Nhóm 2 – Deep Learning, mục 6.5 và nội dung 6
- **Trạng thái:** Đề xuất

### M-07 BERT
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-01, BT-03
- **Lý do chọn:** Nhóm 3 – Transformer, mục 6.5 và nội dung 6
- **Trạng thái:** Đề xuất

### M-08 RoBERTa / XLM-R
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-01, BT-03
- **Lý do chọn:** Nhóm 3 – Transformer (mục 6.5); XLM-R đa ngôn ngữ được trích dẫn [3]
- **Trạng thái:** Đề xuất

### M-09 PhoBERT
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-01, BT-03
- **Lý do chọn:** Mô hình tiền huấn luyện cho tiếng Việt, nêu trong CH1, MT3 và nội dung 6
- **Trạng thái:** Đề xuất

### M-10 ViSoBERT
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-01, BT-03
- **Lý do chọn:** Chuyên văn bản MXH tiếng Việt, nêu trong CH1 và MT3
- **Trạng thái:** Đề xuất

### M-11 LLM zero-shot / few-shot
- **Loại:** LLM
- **Bài toán phù hợp:** BT-01, BT-02, BT-03
- **Lý do chọn:** Nêu trong CH1 và MT3; tên mô hình cụ thể: Chưa có trong thuyết minh
- **Trạng thái:** Đề xuất

### M-12 LDA
- **Loại:** Baseline cổ điển
- **Bài toán phù hợp:** BT-02
- **Lý do chọn:** Mô hình chủ đề truyền thống, nội dung 7 thuyết minh
- **Trạng thái:** Đề xuất

### M-13 K-means / Embedding-based Clustering
- **Loại:** Baseline cổ điển
- **Bài toán phù hợp:** BT-02
- **Lý do chọn:** Gom cụm chủ đề, nội dung 7 thuyết minh
- **Trạng thái:** Đề xuất

### M-14 BERTopic
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-02, BT-04
- **Lý do chọn:** Nêu trong MT4 và mục 4.3.1; hợp văn bản ngắn, nhiễu
- **Trạng thái:** Đề xuất

### M-15 BERTrend
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-02, BT-04
- **Lý do chọn:** Nêu trong MT4 và mục 4.3.1; phát hiện chủ đề đang nổi
- **Trạng thái:** Đề xuất

### M-16 PhoBERT-base-v2
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-01, BT-03
- **Lý do chọn:** Bản PhoBERT huấn luyện trên nhiều dữ liệu hơn, cùng cách dùng với M-09 (đề xuất)
- **Trạng thái:** Đề xuất

### M-17 Phát hiện bùng nổ trên chuỗi thời gian (z-score, burst detection)
- **Loại:** Baseline cổ điển
- **Bài toán phù hợp:** BT-02, BT-04
- **Lý do chọn:** MT4 nêu "phân tích chuỗi thời gian"; mốc so sánh đơn giản cho phát hiện chủ đề tăng đột biến (đề xuất)
- **Trạng thái:** Đề xuất

### M-18 Mô hình embedding câu tiếng Việt
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-02
- **Lý do chọn:** Thành phần dùng chung cho BERTopic và K-means trên embedding; tên mô hình cụ thể chưa chọn (đề xuất)
- **Trạng thái:** Đề xuất

### M-19 ViSoBERT / PhoBERT huấn luyện với differential privacy (DP-SGD)
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-01, BT-03
- **Lý do chọn:** Trả lời CH4 và MT5: đo đánh đổi giữa mức bảo vệ quyền riêng tư (ε) và F1-macro (QD-06)
- **Trạng thái:** Đề xuất

### M-20 Học liên kết mô phỏng (federated learning)
- **Loại:** Transformer
- **Bài toán phù hợp:** BT-01
- **Lý do chọn:** Nêu trong MT5; chỉ mô phỏng nhiều bên trên một máy, tùy chọn (QD-06)
- **Trạng thái:** Đề xuất

## 4.5. Lần huấn luyện
<!-- loại: R -->

Chưa có lần huấn luyện nào. Mỗi lần chạy thêm một khối R-xx (Model, Dữ liệu, Phiên bản dữ liệu, Tham số, Accuracy, F1-macro, Precision, Recall, Theo lớp, Ngày chạy, Người chạy, Đường dẫn kết quả, Nhận xét, Trạng thái).

## 4.6. Bài toán ứng dụng
<!-- loại: BT -->

### BT-01 Phân loại quan điểm (tích cực / tiêu cực / trung tính)
- **Đầu vào:** Văn bản bình luận / bài đăng tiếng Việt đã làm sạch
- **Đầu ra:** Nhãn cảm xúc và độ tin cậy
- **Tập nhãn:** Positive, Negative, Neutral; mở rộng Very Positive, Positive, Neutral, Negative, Very Negative nếu dữ liệu cho phép (mục 6.6)
- **Model được chọn:** 
- **Metric mục tiêu:** F1 macro (mục 6.6); giá trị mục tiêu không đặt trước (mục 8)
- **Trạng thái:** Chưa bắt đầu

Ghi chú: thuyết minh trích dẫn bộ UIT-VSMEC (nhận diện cảm xúc, nhiều nhãn hơn 3 lớp) — cách ánh xạ nhãn: Chưa có trong thuyết minh.

### BT-02 Phát hiện xu hướng chủ đề
- **Đầu vào:** Luồng bài đăng / bình luận theo thời gian
- **Đầu ra:** Chủ đề đang được quan tâm, chủ đề mới xuất hiện, độ quan tâm theo thời gian (mục 6.7)
- **Tập nhãn:** Chủ đề do mô hình sinh; tiêu chí "xu hướng": Chưa có trong thuyết minh
- **Model được chọn:** 
- **Metric mục tiêu:** Precision/Recall, độ trễ phát hiện xu hướng (mục 6.10)
- **Trạng thái:** Chưa bắt đầu

### BT-03 Nhận diện và phân loại cảm xúc chi tiết
- **Đầu vào:** Văn bản bình luận / bài đăng tiếng Việt đã làm sạch
- **Đầu ra:** Có mang cảm xúc hay không; nhãn cảm xúc cụ thể và độ tin cậy
- **Tập nhãn:** Enjoyment, Sadness, Fear, Anger, Disgust, Surprise, Other — theo UIT-VSMEC (QD-04)
- **Model được chọn:**
- **Metric mục tiêu:** F1-macro và F1 theo từng nhãn (dữ liệu lệch lớp mạnh)
- **Trạng thái:** Chưa bắt đầu

Bổ sung để khớp tên đề tài "nhận diện và phân loại cảm xúc": BT-01 chỉ là quan điểm 3 lớp. Thuyết minh trích dẫn UIT-VSMEC [6] nhưng chưa có bài toán tương ứng.

### BT-04 Phân loại xu hướng
- **Đầu vào:** Chủ đề (từ BT-02), chuỗi thời gian độ quan tâm, cảm xúc theo chủ đề (từ BT-01, BT-03)
- **Đầu ra:** Loại xu hướng của từng chủ đề và chiều thay đổi cảm xúc
- **Tập nhãn:** Mới nổi / Đang tăng / Đang giảm / Ổn định; kèm Tích cực hóa / Tiêu cực hóa — tập nhãn cụ thể vẫn là đề xuất; nghĩa "xu hướng" theo QD-05
- **Model được chọn:**
- **Metric mục tiêu:** Precision/Recall so với danh sách sự kiện tham chiếu, độ trễ phát hiện (mục 6.10)
- **Trạng thái:** Chưa bắt đầu

Bổ sung để khớp tên đề tài "phân loại ... xu hướng của người dùng": BT-02 mới dừng ở phát hiện. Phân tích ở mức cộng đồng, không theo từng người.

## 5. Nhật ký quyết định
<!-- loại: QD -->

### QD-01 Thu thập qua API chính thức của nền tảng
- **Ngày:** Chưa ghi
- **Người chốt:** Chưa ghi
- **Lý do:** Tuân thủ điều khoản nền tảng và yêu cầu pháp lý (mục 6.3 thuyết minh)

Ghi nhận từ hiện trạng code (collector dùng YouTube Data API v3, TikTok Research API).

### QD-02 Băm định danh tác giả ngay khi thu thập, không lưu định danh gốc
- **Ngày:** Chưa ghi
- **Người chốt:** Chưa ghi
- **Lý do:** Luật 91/2025/QH15; ẩn danh hóa theo mục 6.8 thuyết minh

Ghi nhận từ hiện trạng code (security/anonymize.py).

### QD-03 Dùng PostgreSQL làm kho dữ liệu chính
- **Ngày:** Chưa ghi
- **Người chốt:** Chưa ghi
- **Lý do:** Chưa ghi

Ghi nhận từ hiện trạng code (docker-compose.yml, storage/).

### QD-04 Cảm xúc phân tích hai tầng: quan điểm 3 lớp và cảm xúc 7 nhãn
- **Ngày:** 2026-10-30
- **Người chốt:** Nam
- **Lý do:** Tên đề tài yêu cầu "nhận diện và phân loại cảm xúc"; mục 6.6 thuyết minh chỉ có 3 lớp quan điểm, còn bộ UIT-VSMEC được trích dẫn có 7 nhãn cảm xúc

Quan điểm 3 lớp (BT-01) dùng cho dashboard; cảm xúc 7 nhãn theo UIT-VSMEC (BT-03) dùng để nhận diện cảm xúc chi tiết và so sánh mô hình. Cần cập nhật mục 6.6 thuyết minh cho khớp.

### QD-05 "Xu hướng của người dùng" là xu hướng chủ đề của cộng đồng
- **Ngày:** 2026-10-30
- **Người chốt:** Nam
- **Lý do:** Khớp mục 6.7 thuyết minh; lập hồ sơ khuynh hướng từng người là rủi ro theo Luật 91/2025/QH15

Phát hiện (BT-02) và phân loại (BT-04) xu hướng chủ đề, gắn với cảm xúc. Mọi phân tích theo người dùng chỉ ở mức nhóm tổng hợp, không theo từng tác giả.

### QD-06 Đưa differential privacy vào phạm vi; federated learning chỉ mô phỏng, tùy chọn
- **Ngày:** 2026-10-30
- **Người chốt:** Nam
- **Lý do:** Trả lời trực tiếp CH4 và MT5 ("kết hợp đảm bảo an ninh an toàn" trong tên đề tài); DP-SGD vừa sức 2 người, FL thật tốn công triển khai

Thử DP-SGD trên mô hình cảm xúc (M-19, T-44), đo đánh đổi ε – F1-macro. Federated learning mô phỏng trên một máy (M-20, T-48) chỉ làm nếu còn thời gian.
