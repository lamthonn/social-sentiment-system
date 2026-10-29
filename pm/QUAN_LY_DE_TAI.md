# Quản lý đề tài NCKH

<!-- Sửa qua giao diện: python pm/server.py (http://localhost:8765). Sửa tay được nhưng giữ đúng định dạng 3 mục. -->

## 1. Tổng quan

### Thông tin chung

| Mục | Nội dung |
|---|---|
| Tên đề tài | Nghiên cứu các kỹ thuật máy học hiện đại kết hợp đảm bảo an ninh an toàn ứng dụng trong phát triển thử nghiệm hệ thống thông tin hỗ trợ thu thập, lưu trữ tự động dữ liệu mạng xã hội để nhận diện và phân loại cảm xúc và xu hướng của người dùng |
| Cấp | Đề tài KH-CN cấp trường (người học) — Trường ĐH Điện lực, Khoa Điện toán và Công nghệ số năng lượng |
| Thời gian | 09/2026 → 02/2027 (6 tháng) |
| Nhóm | Chủ nhiệm: Nguyễn Viết Doanh · Thành viên: Vũ Hải Nam, Vũ Vương Lâm · GVHD: ThS. Lê Thanh Trà |
| Kinh phí | 5.000.000 đ (thuyết minh ghi bằng chữ "Ba triệu" — cần sửa) |
| Thuyết minh | `TM_final.docx` ở gốc repo |

### Mục tiêu & câu hỏi nghiên cứu

**Mục tiêu:** xây dựng thử nghiệm hệ thống tự động **thu thập → lưu trữ → phân tích cảm xúc → phát hiện xu hướng** trên dữ liệu mạng xã hội tiếng Việt, bảo đảm an ninh an toàn và tuân thủ **Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15**.

- **CH1** — Mô hình nào (PhoBERT, ViSoBERT, LLM…) tốt nhất cho phân loại cảm xúc MXH tiếng Việt so với baseline?
- **CH2** — Phát hiện, phân loại xu hướng theo thời gian thế nào cho hiệu quả?
- **CH3** — Kiến trúc thu thập, lưu trữ nào bảo đảm hiệu năng, mở rộng, ổn định?
- **CH4** — Cơ chế an ninh nào vừa tuân thủ luật vừa giữ độ chính xác? Đánh đổi ra sao?
- **CH5** — Tích hợp được 4 phần trên thành hệ thống thử nghiệm không, hiệu quả thực nghiệm ra sao?

### Nghiệp vụ

**Người dùng hệ thống (đề xuất):**
- **Admin** — quản trị người dùng, cấu hình nguồn thu thập, quản lý mô hình, xem nhật ký.
- **Analyst** — cấu hình từ khóa/video theo dõi, xem dữ liệu chi tiết, chạy phân tích, xuất báo cáo.
- **Viewer** — chỉ xem dashboard tổng hợp.

**Quy trình chính:**
1. Analyst nhập từ khóa hoặc video cần theo dõi trên giao diện.
2. Scheduler chạy định kỳ: tìm video mới theo từ khóa → lấy bình luận → **băm định danh tác giả** → lưu `raw_posts`.
3. Tiền xử lý (làm sạch, chuẩn hóa, lọc spam, che thông tin cá nhân trong nội dung).
4. Mô hình gán nhãn cảm xúc cho bản ghi mới → `analysis_results`.
5. Tổng hợp chủ đề & xu hướng theo thời gian.
6. Xem dashboard cảm xúc, xu hướng; xuất báo cáo.

**Quy tắc nghiệp vụ:**
- Không lưu định danh gốc người dùng — băm SHA-256 + salt ngay khi thu thập *(đã có)*.
- Không trùng bản ghi theo (nền tảng, mã bình luận) *(đã có)*.
- Chỉ thu thập nội dung công khai qua API chính thức, đúng điều khoản *(đã có)*.
- Tôn trọng quota YouTube 10.000 unit/ngày: tìm kiếm 100 unit/lần, lấy bình luận 1 unit/lần.
- Che số điện thoại, email, tên riêng xuất hiện trong nội dung trước khi đưa vào dataset *(chưa có)*.

### Phạm vi

**Trong phạm vi (đề xuất, cần chốt):**
- Bình luận công khai tiếng Việt trên **YouTube** (TikTok nếu được duyệt Research API).
- Phân loại cảm xúc mức bình luận; phát hiện chủ đề & xu hướng theo thời gian.
- Ẩn danh, đăng nhập & phân quyền, bảo vệ API, nhật ký, kiểm tra an toàn dữ liệu đầu vào mô hình.
- Dashboard trực quan hóa.

**Ngoài phạm vi (đề xuất):**
- Xử lý video/âm thanh/ảnh (Speech-to-Text, OCR).
- Thu thập vượt điều khoản nền tảng (scraping).
- Xử lý thời gian thực dạng streaming, triển khai production.
- Facebook (API gần như không cho đọc dữ liệu công khai).

### Ứng dụng của đề tài

| Ứng dụng | Đánh giá nhanh |
|---|---|
| **Ý kiến người dân về giá điện, mất điện, dịch vụ ngành điện** | Hợp với Trường ĐH Điện lực, dữ liệu YouTube nhiều khi có sự kiện — **đề xuất chọn làm ứng dụng chính** |
| Theo dõi dư luận chủ đề kinh tế – xã hội (giá vàng, giá xăng…) | Dữ liệu dồi dào, sự kiện rõ để đánh giá xu hướng — **phương án dự phòng** |
| Lắng nghe mạng xã hội cho doanh nghiệp / thương hiệu | Giá trị thực tiễn cao, cần chọn thương hiệu cụ thể |
| Cảnh báo sớm khủng hoảng truyền thông | Hấp dẫn nhưng khó đánh giá, dễ báo động giả |
| Phân tích phản hồi người học | Gần bộ UIT-VSFC nhưng ít dữ liệu MXH công khai |
| Hỗ trợ an ninh mạng: phát hiện nội dung tiêu cực / thù ghét | Nhạy cảm pháp lý và đạo đức |

### Kiến trúc

**Hiện trạng (code trên repo):**
- **Collector** YouTube (chạy tốt) và TikTok (chưa kiểm tra bằng key thật) → **PostgreSQL**.
- **Scheduler** (APScheduler) đọc cấu hình từ DB mỗi lượt chạy.
- **API** FastAPI :8000 · **Frontend** React + Ant Design :5500.
- Bảng: `raw_posts`, `analysis_results` (chưa dùng), `search_queries`, `tracked_videos`.

**Mục tiêu (theo thuyết minh):**
Nguồn MXH → Collector → *Hàng đợi (Kafka/RabbitMQ — cần chốt)* → Tiền xử lý / NLP → Lưu trữ + ML pipeline → Phân tích cảm xúc & Phát hiện xu hướng → Dashboard.
Lớp an ninh xuyên suốt: xác thực, phân quyền, bảo vệ API, mã hóa, quyền riêng tư, nhật ký, an toàn mô hình, giám sát & sao lưu.

**Còn thiếu trong CSDL:** hashtag & metadata (like, reply, tiêu đề video), bình luận trả lời, bảng nhãn thủ công, bảng chủ đề/xu hướng, người dùng & vai trò, nhật ký, lượt chạy thu thập.

### Việc cần chốt

| Vấn đề | Đề xuất |
|---|---|
| Nền tảng thu thập | YouTube; thêm TikTok nếu được duyệt trước cuối 10/2026 |
| Có dùng Kafka/RabbitMQ thật? | RabbitMQ (nhẹ, vẫn khớp thuyết minh); thiếu thời gian thì dùng bảng DB làm hàng đợi |
| Phân loại 3 lớp quan điểm hay 7 nhãn cảm xúc (UIT-VSMEC)? | 3 lớp là chính (dashboard), 7 nhãn là thực nghiệm phụ |
| Gán nhãn dữ liệu tự thu thập | 2 người gán ~1.000 mẫu làm tập test, gán chéo 20% để đo độ đồng thuận (Kappa) |
| Có làm học máy bảo toàn quyền riêng tư (FL/DP)? | Làm DP-SGD trên mô hình cảm xúc, đo đánh đổi ε – F1; FL để hướng phát triển |
| Định nghĩa "xu hướng" | Ngưỡng tăng trưởng tần suất làm baseline + BERTopic theo thời gian làm phương pháp chính |
| Mô hình cảm xúc chính | Chốt theo Macro-F1 trên tập test YouTube tự gán nhãn (xem mục 3) |
| Hạ tầng GPU | Google Colab / Kaggle |
| Phần việc của Nguyễn Viết Doanh | Doanh tiếp tục làm hay chia lại cho Nam và Lâm |
| Thời gian lưu dữ liệu thô | 6 tháng sau khi kết thúc đề tài rồi xóa, giữ dataset đã ẩn danh |

### Rủi ro chính

- **Phạm vi quá rộng** so với 6 tháng và 2 người (Kafka, FL/DP, LLM…) → chốt sớm theo hướng tối giản, sửa thuyết minh cho khớp.
- **Thiếu dữ liệu gán nhãn** → bắt đầu với UIT-VSMEC/VSFC, gán nhãn song song.
- **TikTok không được duyệt** → chỉ dùng YouTube.
- **Lộ thông tin cá nhân trong nội dung bình luận** → che trong bước tiền xử lý, không công bố nội dung thô.
- **Hết quota YouTube** → theo dõi số unit đã dùng, hạn chế số từ khóa tìm kiếm.
- **Mô hình tốt trên UIT nhưng kém trên dữ liệu YouTube** → có tập test từ dữ liệu thật, thử ViSoBERT.

### Cần sửa trong thuyết minh

- Kinh phí: số 5.000.000 nhưng chữ ghi "Ba triệu đồng chẵn".
- Xóa ghi chú nháp ở đầu Tài liệu tham khảo; bổ sung thông tin thiếu cho [8], [11], [12], [16].
- Câu bỏ lửng: mục 6.5 "Có thể xây dựng chiến lược:", mục 6.8 "Từ đó nghiên cứu các phương pháp giảm thiểu:", mục 6.7 "Ví dụ".
- Mục tiêu hứa FL/DP, LLM, ViSoBERT nhưng kế hoạch mục 7 không có công việc tương ứng.
- 3 lớp cảm xúc (mục 6.6) chưa khớp 7 nhãn của UIT-VSMEC.
- Điền mã số, ngày ký.

## 2. Việc cần làm

| Mã | Việc | Trạng thái | Người làm | Ghi chú |
|---|---|---|---|---|
| T-01 | Thu thập bình luận YouTube theo video & theo từ khóa | Xong | Lâm | collector/youtube_client.py, CLI run/search |
| T-02 | Lập lịch thu thập định kỳ, cấu hình qua giao diện | Xong | Lâm | collector/scheduler.py, tab Cấu hình thu thập |
| T-03 | Ẩn danh định danh tác giả khi thu thập | Xong | Lâm | security/anonymize.py |
| T-04 | Giao diện xem dữ liệu thu thập | Xong | Lâm | frontend React + Ant Design |
| T-05 | Công cụ quản lý đề tài (pm/) | Xong | Nam |  |
| T-06 | Chốt các việc cần chốt (mục 1) | Đang làm | Nam | Ưu tiên: nền tảng, số lớp cảm xúc, FL/DP, ứng dụng chính |
| T-07 | Sửa thuyết minh theo danh sách ở mục 1 | Chưa làm | Nam |  |
| T-08 | Viết tổng quan tài liệu: thu thập, cảm xúc, xu hướng, an ninh | Chưa làm | Lâm | Nội dung 1 thuyết minh |
| T-09 | Viết cơ sở lý thuyết (NLP, ML/DL, Transformer, topic modeling) | Chưa làm |  | Nội dung 2 — thuyết minh giao Doanh |
| T-10 | Thiết kế CSDL mở rộng (metadata, hashtag, nhãn, xu hướng, người dùng, nhật ký) | Chưa làm | Nam | Cần thêm migration (Alembic) |
| T-11 | Vẽ sơ đồ kiến trúc, use case, luồng dữ liệu cho báo cáo | Chưa làm | Nam |  |
| T-12 | Kiểm tra điều kiện & đăng ký TikTok Research API | Chưa làm | Lâm | Quá cuối 10/2026 chưa có thì bỏ TikTok |
| T-13 | Lưu metadata & hashtag, lấy cả bình luận trả lời | Chưa làm | Lâm |  |
| T-14 | Retry khi lỗi, theo dõi quota, nhật ký lượt chạy thu thập | Chưa làm | Lâm |  |
| T-15 | Hàng đợi dữ liệu giữa thu thập và xử lý | Chưa làm | Lâm | Tùy kết quả chốt Kafka/RabbitMQ |
| T-16 | Tải & chuẩn bị UIT-VSMEC, UIT-VSFC | Chưa làm |  |  |
| T-17 | Pipeline tiền xử lý tiếng Việt (chuẩn hóa, teencode, emoji, tách từ, che thông tin cá nhân) | Chưa làm |  | Thư mục preprocessing/ |
| T-18 | Lọc spam, seeding, nội dung trùng lặp | Chưa làm |  |  |
| T-19 | Gán nhãn tập test từ dữ liệu YouTube + đo độ đồng thuận | Chưa làm |  |  |
| T-20 | Chạy baseline TF-IDF + LR/SVM | Chưa làm | Nam | Ghi kết quả vào mục 3 |
| T-21 | Chạy BiLSTM | Chưa làm | Nam |  |
| T-22 | Fine-tune PhoBERT và ViSoBERT | Chưa làm | Nam |  |
| T-23 | Thử LLM zero/few-shot (nếu chốt làm) | Tạm dừng | Nam | Chờ chốt |
| T-24 | Tích hợp mô hình tốt nhất: gán nhãn tự động ghi analysis_results | Chưa làm | Nam |  |
| T-25 | Thống kê từ khóa/hashtag theo thời gian, topic modeling (LDA vs BERTopic) | Chưa làm | Nam |  |
| T-26 | Phát hiện chủ đề nổi & kết hợp với cảm xúc | Chưa làm | Nam |  |
| T-27 | Đăng nhập & phân quyền Admin / Analyst / Viewer | Chưa làm | Lâm | API hiện đang mở hoàn toàn |
| T-28 | Bảo vệ API, mã hóa, quản lý bí mật, sao lưu DB | Chưa làm | Lâm |  |
| T-29 | Nhật ký hoạt động & giám sát hệ thống | Chưa làm | Lâm |  |
| T-30 | An toàn ML pipeline (kiểm tra dữ liệu, ngoại lai, kiểm định mô hình) | Chưa làm | Lâm |  |
| T-31 | Thử nghiệm DP-SGD & đánh đổi riêng tư – độ chính xác (nếu chốt làm) | Chưa làm | Lâm |  |
| T-32 | Kịch bản kiểm thử bảo mật (SQLi, XSS, brute force, đầu độc dữ liệu) | Chưa làm | Lâm |  |
| T-33 | Dashboard cảm xúc theo thời gian & xu hướng | Chưa làm | Nam |  |
| T-34 | Tìm kiếm, lọc, xuất dữ liệu | Chưa làm | Nam |  |
| T-35 | Đánh giá hiệu năng hệ thống (throughput, latency, CPU/RAM) | Chưa làm |  |  |
| T-36 | Viết báo cáo tổng kết, chuẩn bị slide & demo | Chưa làm |  |  |

## 3. Mô hình

### M-01 · TF-IDF + Logistic Regression
- Bài toán: Cảm xúc
- Nhóm: Baseline
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Mốc so sánh nhanh, chạy CPU, dễ giải thích.

### M-02 · TF-IDF + SVM
- Bài toán: Cảm xúc
- Nhóm: Baseline
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Baseline mạnh truyền thống cho văn bản ngắn.

### M-03 · BiLSTM
- Bài toán: Cảm xúc
- Nhóm: Học sâu
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Đại diện nhóm học sâu theo thuyết minh; embedding PhoW2V hoặc học từ đầu.

### M-04 · PhoBERT-base
- Bài toán: Cảm xúc
- Nhóm: Transformer
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Mô hình nền tảng cho tiếng Việt (VinAI). Đầu vào phải được tách từ trước (VnCoreNLP).

### M-05 · ViSoBERT
- Bài toán: Cảm xúc
- Nhóm: Transformer
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Huấn luyện trên văn bản mạng xã hội tiếng Việt — hợp teencode, emoji. Ứng viên mạnh cho dữ liệu YouTube.

### M-06 · XLM-RoBERTa-base
- Bài toán: Cảm xúc
- Nhóm: Transformer
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Mô hình đa ngôn ngữ, dùng đối chứng với mô hình chuyên tiếng Việt.

### M-07 · LLM zero-shot / few-shot (chạy local)
- Bài toán: Cảm xúc
- Nhóm: LLM
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Không cần dữ liệu huấn luyện; ưu tiên chạy local để không gửi dữ liệu ra ngoài. Có thể dùng để gán nhãn sơ bộ.

### M-08 · Thống kê tần suất từ khóa / hashtag
- Bài toán: Xu hướng
- Nhóm: Baseline
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Đếm theo cửa sổ thời gian, so với trung bình trượt để phát hiện tăng đột biến.

### M-09 · LDA
- Bài toán: Xu hướng
- Nhóm: Chủ đề / Thống kê
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Topic modeling truyền thống, làm mốc so sánh cho BERTopic.

### M-10 · BERTopic
- Bài toán: Xu hướng
- Nhóm: Transformer
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Embedding câu + gom cụm; hợp văn bản ngắn, có sẵn phân tích chủ đề theo thời gian.

### M-11 · BERTrend
- Bài toán: Xu hướng
- Nhóm: Transformer
- Trạng thái: Ứng viên
- Dataset: 
- Accuracy: 
- Precision: 
- Recall: 
- Macro-F1: 
- Mô tả: Phát hiện chủ đề đang nổi (tín hiệu mạnh / yếu / nhiễu). Mới, cần thử trên tiếng Việt.
