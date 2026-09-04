# TÀI LIỆU THIẾT KẾ & GIẢI ĐÁP BÀI TOÁN CRAWL DỮ LIỆU, PHÂN TÍCH CẢM XÚC VÀ DỰ ĐOÁN TREND

> **Dự án**: Social Sentiment System  
> **Phạm vi**: Đề tài NCKH / Luận văn Thạc sĩ  
> **Cập nhật lần cuối**: September 2026  

---

## I. GIẢI ĐÁP CHI TIẾT CÁC CÂU HỎI THIẾT KẾ HỆ THỐNG CRAWL

### 1. Yêu cầu về Số lượng & Chất lượng dữ liệu theo Môi trường (Dev, Test, Prod)

*   **Môi trường Dev (Phát triển)**:
    *   **Số lượng**: 500 – 1.000 bản ghi thô.
    *   **Yêu cầu**: Nhẹ, chạy trực tiếp trên máy cá nhân để kiểm thử pipeline crawl, tiền xử lý và kiểm tra lỗi code (unit test/integration test).
*   **Môi trường Test / Evaluation (Đánh giá Mô hình AI)**:
    *   **Số lượng**: 3.000 – 10.000 bài đăng/bình luận.
    *   **Yêu cầu**: Chất lượng chuẩn hóa cao, **bắt buộc được gán nhãn thủ công hoặc kiểm định nghiêm ngặt** (*Gold Standard Dataset*). Phải đạt chỉ số nhất quán giữa các người gán nhãn (*Fleiss' Kappa / Cohen's Kappa*) $\ge 0.75$.
*   **Môi trường Prod (Vận hành thực tế / Dự báo Trend)**:
    *   **Số lượng**: 10.000 – 100.000+ bài đăng/bình luận mỗi ngày tùy danh mục chủ đề.
    *   **Yêu cầu**: Độ sạch cao (đã qua bộ lọc spam/seeding), đầy đủ mốc thời gian (`posted_at`, `collected_at`) để dựng mô hình chuỗi thời gian (Time-series Analysis).

---

### 2. Thu thập Dữ liệu theo Ngày cho Bài toán Dự đoán Trend (Streaming vs Polling)

*   **Thực tế**: Không thể crawl *toàn bộ* dữ liệu mạng xã hội (do hạn chế Quota, giới hạn băng thông và băng thông lưu trữ).
*   **Giải pháp cho Bài toán Trend**: Sử dụng phương pháp **Targeted Crawling**:
    *   **Theo Bộ Từ Khóa (Keyword-based)**: Thu thập các bài viết/video chứa từ khóa thuộc các chủ đề cần theo dõi (Kinh tế, Bất động sản, Xe điện, AI...).
    *   **Theo Danh sách Kênh/Creator dẫn dắt (KOL-based)**: Theo dõi các kênh YouTube/TikTok có lượng tương tác lớn và tốc độ phát tán thông tin nhanh.
    *   **Thu thập lũy tiến (Incremental Crawling)**: Sử dụng mốc `publishedAfter` hoặc `cursor` để chỉ quét bài đăng/bình luận mới phát sinh trong khoảng thời gian (theo giờ/ngày), tránh thu thập lặp lại.

---

### 3. Phân biệt Dữ liệu Người dùng & Cấp độ Phân loại Cảm xúc

*   **Các Cấp độ Phân loại Cảm xúc**:
    1.  **Cấp độ Bình luận/Bài đăng (Comment/Post-level)**: Phân loại từng văn bản cụ thể là Tích cực (Positive), Tiêu cực (Negative) hay Trung tính (Neutral).
    2.  **Cấp độ Tổng hợp (Aggregate-level)**: Gom nhóm các bình luận theo Video, Theo Chủ đề hoặc Theo Thời gian (ngày/giờ) để tính **Chỉ số Cảm xúc Tổng thể (Sentiment Index)**.
*   **Xử lý Dữ liệu Người dùng (Bảo mật PII)**:
    *   Theo **Luật Bảo vệ Dữ liệu Cá nhân Việt Nam (Nghị định 13/2023/NĐ-CP & Luật số 91/2025/QH15)**: Không phân tích hay lưu trữ thông tin nhận dạng cá nhân gốc (tên thật, số điện thoại, avatar...).
    *   Mã hóa `author_identifier` thành `author_hash` bằng thuật toán SHA-256. Kỹ thuật này vừa bảo vệ quyền riêng tư vừa hỗ trợ phân tích hành vi nhóm (VD: tỷ lệ người dùng lặp lại bình luận tiêu cực, phát hiện bot/seeding).

---

### 4. Quota, Rate Limit và Chi phí trên các Nền tảng

| Nền tảng | Cơ chế cấp phép | Giới hạn (Quota / Rate Limit) | Giải pháp tối ưu |
| :--- | :--- | :--- | :--- |
| **YouTube** | YouTube Data API v3 | Free 10.000 units/ngày. (`commentThreads.list` = 1 unit, `search.list` = 100 units). | Lưu ETag, dùng `publishedAfter` để chỉ crawl dữ liệu mới, hạn chế gọi search. |
| **TikTok** | TikTok Research API | Miễn phí cho NCKH khi được duyệt đơn. Có rate limit theo tuần/tháng. | Đăng ký tài khoản Developer chính thức cho NCKH; chuẩn bị Playwright/Selenium làm fallback. |
| **Facebook / Shopee** | Graph API / Web Interface | Graph API bị bóp chặt; Web Interface bị chặn IP / Cloudflare CAPTCHA. | Sử dụng Proxy xoay (Rotating Proxy), điều khiển tần suất request ngẫu nhiên (Human-like delay). |

---

### 5. Khía cạnh Pháp lý và Bảo vệ Dữ liệu Cá nhân

*   **Bảo mật dữ liệu cá nhân**: Toàn bộ ID/Username gốc phải được hash ngay tại bước Ingestion trước khi ghi vào Database.
*   **Điều khoản dịch vụ (ToS)**: Chỉ sử dụng API chính thức hoặc tuân thủ `robots.txt` & ToS của nền tảng đối với dữ liệu công khai (Public Data).
*   **Mục đích Nghiên cứu**: Sử dụng dữ liệu cho mục đích NCKH / Luận văn Thạc sĩ (Non-commercial research) được áp dụng cơ chế *Fair Use* theo luật pháp Việt Nam và thông lệ quốc tế.

---

### 6. Phương pháp Xử lý Bài đăng không có Text / Ít Nội dung (Shorts / Reels / TikTok)

Áp dụng phương pháp phân tích Đa thức (**Multimodal Analysis**):
1.  **Chuyển Giọng nói thành Văn bản (ASR)**: Dùng mô hình **OpenAI Whisper AI** để trích xuất âm thanh video thành lời nói (transcript).
2.  **Đọc chữ chèn trên Video (OCR)**: Trích xuất các khung hình tiêu biểu (Keyframes) và dùng **VietOCR** để đọc chữ chèn trên màn hình (subtitles/overlay text).
3.  **Lấy bối cảnh từ Bình luận**: Trong bài toán Sentiment, **nội dung video đóng vai trò Bối cảnh (Context), còn cảm xúc thật sự nằm ở Phần Bình luận (Comments) của cộng đồng.**

---

### 7. Phân tích Cảm xúc (Sentiment) vs Phân tích Nội dung (Content/Topic Modeling)

*   **Kết luận**: **BẮT BUỘC PHẢI PHÂN TÍCH CẢ NỘI DUNG LẪN CẢM XÚC.**
*   **Lý do**: Nếu chỉ biết cảm xúc là "Tiêu cực", hệ thống sẽ không biết dư luận đang bức xúc **về vấn đề gì** (Giá tăng? Chất lượng dịch vụ kém? Drama cá nhân?).
*   **Giải pháp**: Kết hợp **Phân loại Chủ đề (Topic Modeling - BERTopic/LDA)** + **Phân tích Cảm xúc theo Khía cạnh (Aspect-Based Sentiment Analysis - ABSA)**.

---

### 8. Phương pháp Trích xuất Từ khóa và Gán Cảm xúc theo Khía cạnh (ABSA)

*   **Bước 1 (Trích xuất từ khóa)**: Dùng thuật toán `KeyBERT`, `TF-IDF`, hoặc `YAKE` để trích xuất các cụm từ quan trọng (N-grams).
*   **Bước 2 (Gán nhãn Cảm xúc & Khía cạnh)**:
    *   Sử dụng mô hình PhoBERT / XLM-RoBERTa fine-tuned cho ABSA.
    *   Hoặc sử dụng **LLM (Gemini / Qwen / Llama)** với cấu trúc JSON Output:
        ```json
        [
          {"aspect": "Pin", "sentiment": "Positive", "score": 0.85},
          {"aspect": "Giá cả", "sentiment": "Negative", "score": 0.92}
        ]
        ```
*   **Bước 3 (Trực quan hóa)**: Xây dựng WordCloud theo màu cảm xúc (Xanh = Tích cực, Đỏ = Tiêu cực) hoặc Biểu đồ Mạng lưới Từ khóa (Co-occurrence Network).

---

### 9. Phân loại Bài đăng đa chiều (Multi-dimensional Post Classification)

*   **Theo Chủ đề (Topic Category)**: Kinh tế, Công nghệ, Bất động sản, Giải trí, Y tế...
*   **Theo Tiềm năng Lan truyền (Virality Rate)**: Dựa trên tốc độ tăng trưởng Like/Share/Comment trong 1-3 giờ đầu.
*   **Theo Mục đích Nội dung (Content Intent)**: Tin tức (News), Thắc mắc (Question), Than phiền (Complaint), Quảng cáo/Spam (Ad).

---

### 10. Chuẩn hóa Schema Dữ liệu Đa Nền tảng (Multi-platform Data Schema)

Sử dụng cấu trúc **Schema Normalization**:

```sql
CREATE TABLE raw_posts (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,            -- 'youtube', 'tiktok', 'facebook'
    post_id VARCHAR(128) NOT NULL,            -- ID gốc bài đăng / comment
    author_hash VARCHAR(64) NOT NULL,         -- SHA-256 hash người đăng
    content TEXT NOT NULL,                    -- Nội dung văn bản
    posted_at TIMESTAMP WITH TIME ZONE,       -- Thời điểm đăng
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Các chỉ số tương tác chuẩn hóa (Common Metrics)
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    view_count INT DEFAULT NULL,
    
    -- Thuộc tính linh hoạt cho từng nền tảng (Platform Specific Metadata)
    raw_metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT uq_raw_posts_platform_post_id UNIQUE (platform, post_id)
);
```

---

### 11. Đánh giá Lựa chọn CSDL: SQL vs NoSQL

*   **Khuyên dùng**: **Kiến trúc Lai (Hybrid) dựa trên PostgreSQL.**
    *   **PostgreSQL**: Đảm bảo tính toàn vẹn dữ liệu quan hệ (`raw_posts`, `analysis_results`, `tracked_videos`), đồng thời hỗ trợ native `JSONB` cho dữ liệu NoSQL linh hoạt.
    *   **Vector Database (Qdrant / ChromaDB)**: Kết hợp lưu trữ Vector Embedding phục vụ cho bài toán Gom cụm bài viết (Clustering) và Tìm kiếm Ngữ nghĩa (Semantic Search).

---

## II. CÁC CÂU HỎI BỔ SUNG NÂNG CAO CHO ĐỀ TÀI NCKH

### 12. Xử lý Ngôn ngữ Mạng xã hội Tiếng Việt đặc thù (Teencode, Mỉa mai - Sarcasm, Không dấu)
*   **Đặt vấn đề**: Bình luận tiếng Việt MXH chứa rất nhiều teencode (*"j2", "ko", "dc"*), từ lóng thay đổi liên tục, và câu nói mỉa mai (Sarcasm - viết lời khen nhưng mang ý chê).
*   **Giải pháp**:
    *   Xây dựng Dict tiền xử lý chuẩn hóa Teencode trước khi đưa vào PhoBERT.
    *   Huấn luyện mô hình phát hiện Châm biếm (Sarcasm Detection) dựa trên bối cảnh icon/emo đi kèm.

### 13. Lọc Dữ liệu Nhiễu, Spam và Mạng lưới Bot Seeding
*   **Đặt vấn đề**: Botnet và dịch vụ tăng tương tác ảo (seeding) tạo ra hàng loạt bình luận lặp đi lặp lại, gây lệch kết quả phân tích Trend.
*   **Giải pháp**:
    *   Lọc dựa trên `author_hash`: Nếu 1 `author_hash` đăng cùng 1 nội dung trên N bài đăng trong thời gian ngắn $\rightarrow$ Đánh dấu Spam.
    *   Sử dụng thuật toán Cosine Similarity để loại bỏ các câu bình luận trùng lặp $\ge 90\%$.

### 14. Xử lý Sự thay đổi Từ ngữ theo Thời gian (Concept Drift & Out-of-Vocabulary)
*   **Đặt vấn đề**: Từ lóng và chủ đề HOT thay đổi theo từng tuần. Mô hình huấn luyện tháng trước có thể không hiểu từ lóng tháng này.
*   **Giải pháp**:
    *   Định kỳ cập nhật Từ điển Từ khóa mới qua thuật toán Unsupervised Topic Modeling (BERTopic).
    *   Sử dụng cơ chế Fine-tuning định kỳ (Continuous Learning) cho mô hình NLP.

### 15. Lựa chọn Kiến trúc Xử lý: Real-time Streaming vs Batch Processing
*   **Đặt vấn đề**: Bài toán Trend cần cập nhật dữ liệu nhanh đến mức nào?
*   **Giải pháp**:
    *   Sử dụng **Batch Polling (15-60 phút/lần)** bằng Celery / APScheduler cho giai đoạn nghiên cứu thử nghiệm (chi phí thấp, dễ triển khai).
    *   Mở rộng sang **Event-driven / Streaming Architecture (Kafka + Flink)** khi triển khai hệ thống lớn đòi hỏi cảnh báo bài đăng phát tán theo thời gian thực (Real-time Alerting).

### 16. Định nghĩa và Thước đo Đánh giá Hiệu quả Dự đoán Trend (Metrics)
*   **Đặt vấn đề**: Dựa vào tiêu chí nào để khẳng định hệ thống dự đoán Trend chính xác?
*   **Giải pháp**:
    *   **Ngưỡng kích hoạt Trend**: Tốc độ tăng trưởng bài viết/bình luận $> 200\%$ trong 3 giờ liên tiếp.
    *   **Chỉ số đánh giá (Evaluation Metrics)**: 
        *   *Precision@K*: Tỷ lệ các chủ đề hệ thống dự báo là Trend thực sự trở thành Trend trên Google Trends / Social Media.
        *   *Lead Time*: Thời gian hệ thống phát hiện Trend sớm hơn bao nhiêu giờ/ngày so với đỉnh sóng của cộng đồng.

---

> 📌 *Tài liệu này được xuất tự động phục vụ công tác thiết kế hệ thống và viết báo cáo NCKH / Luận văn Thạc sĩ.*
