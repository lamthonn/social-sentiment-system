# Kiến trúc hệ thống (hiện trạng)

Tài liệu mô tả hệ thống **đang chạy** trong repo, dùng cho chương thiết kế của báo cáo (đầu việc T-07). Kiến trúc mục tiêu theo thuyết minh có thêm hàng đợi Kafka/RabbitMQ; bản hiện tại chưa có hàng đợi (xem mục 5).

## 1. Thành phần và luồng dữ liệu

```mermaid
flowchart LR
  subgraph Nguon["Nguồn dữ liệu"]
    YT["YouTube Data API v3"]
    TT["TikTok Research API<br/>(chờ cấp key)"]
    UIT["UIT-VSFC, UIT-VSMEC<br/>(bộ dữ liệu có nhãn)"]
  end
  subgraph API["Tiến trình API (FastAPI)"]
    MW["Middleware an ninh<br/>JWT · vai trò · giới hạn tần suất · nhật ký"]
    SCH["Scheduler thu thập<br/>(APScheduler)"]
    R["Endpoint webapp"]
  end
  subgraph PIPE["Pipeline (python -m pipeline)"]
    C1["collect"] --> C2["clean<br/>làm sạch · che PII · spam · hashtag"]
    C2 --> C3["predict<br/>quan điểm + cảm xúc"]
    C3 --> C4["trends<br/>chủ đề · xu hướng · hashtag"]
    C4 --> C5["monitor<br/>trôi dữ liệu · cảnh báo"]
    D1["datasets"] --> D2["train<br/>TF-IDF · BiLSTM · ViSoBERT · PhoBERT"]
  end
  DB[("PostgreSQL")]
  FS[("data/<br/>dataset · mô hình · log · sao lưu")]
  WEB["Webapp React + Ant Design"]

  YT --> SCH
  TT --> SCH
  SCH -->|"băm tác giả"| DB
  YT --> C1
  C1 --> DB
  DB <--> PIPE
  UIT --> D1
  D1 --> FS
  D2 --> FS
  D2 -->|"model_runs"| DB
  C3 -.->|"nạp mô hình đang chọn"| FS
  WEB -->|"/api"| MW --> R --> DB
  R -->|"chạy bước pipeline<br/>(tiến trình con)"| PIPE
```

| Thành phần | Mã nguồn | Ghi chú |
|---|---|---|
| Thu thập | `collector/` | API chính thức; băm định danh tác giả SHA-256 + salt trước khi ghi DB |
| Làm sạch | `preprocessing/text.py` | Unicode NFC, dấu thanh, teencode, emoji, che SĐT/email/@tên, spam, ngôn ngữ, hashtag |
| Dataset | `pipeline/datasets.py` | Tải UIT-VSFC/UIT-VSMEC, làm sạch bằng cùng hàm, kiểm tra rò rỉ train↔test |
| Huấn luyện, đánh giá | `models/sentiment/train.py` | Mỗi lần chạy ghi `model_runs` và thư mục `data/models/<mã>` |
| Dự đoán | `models/sentiment/predict.py` | Dùng mô hình đang được chọn (F1-macro cao nhất hoặc quản trị chọn tay) |
| Xu hướng | `models/trend/trends.py` | TF-IDF + NMF theo chủ đề thu thập; luật 3 ngày so với 7 ngày trước |
| Điều phối | `pipeline/` | Mỗi bước ghi `pipeline_runs` (thời gian, số bản ghi vào/ra, lỗi) |
| API + an ninh | `api/`, `security/` | Mọi route cần đăng nhập trừ `/health`; route chưa khai báo mặc định chỉ quản trị |
| Webapp | `frontend/` | Tổng quan, Xu hướng, Dữ liệu đã phân tích, Thu thập, Mô hình, Pipeline, Người dùng & nhật ký |
| Thực nghiệm | `experiments/` | Kết quả ở `data/experiments/*.json`, hiển thị ở mục Mô hình |

## 2. Mô hình dữ liệu

```mermaid
erDiagram
  raw_posts ||--o| clean_posts : "làm sạch"
  raw_posts ||--o{ analysis_results : "gán nhãn"
  pipeline_runs ||--o{ topics : "lượt phân tích xu hướng"
  topics ||--o{ topic_daily : "chuỗi theo ngày"
  raw_posts {
    int id PK
    string platform
    string post_id "duy nhất cùng platform"
    string author_hash "SHA-256 + salt"
    text content
    string category "từ khóa/video nguồn"
    datetime posted_at
  }
  clean_posts {
    int raw_post_id PK
    text clean_text "đã che PII"
    string lang
    bool is_spam
    bool is_duplicate
    text hashtags
  }
  analysis_results {
    int raw_post_id FK
    string task "sentiment | emotion"
    string sentiment_label
    float sentiment_score
    string model_name
  }
  model_runs {
    string run_code
    string task
    float f1_macro
    bool selected
    string selected_by
  }
  topics {
    string category
    string keywords
    string trend_label
    string sentiment_shift
  }
  users {
    string username
    string password_hash "PBKDF2-SHA256"
    string role "viewer | analyst | admin"
  }
  audit_logs {
    datetime at
    string username
    string action
    bool success
  }
```

Các bảng cấu hình thu thập (`search_queries`, `tracked_videos`, `scheduler_state`) và `pipeline_runs` không vẽ để sơ đồ gọn.

## 3. An ninh an toàn theo lớp (thuyết minh mục 6.8)

| Lớp | Biện pháp đã có | Còn thiếu |
|---|---|---|
| Dữ liệu | Băm tác giả khi thu thập; che SĐT/email/@tên; sao lưu `python -m storage.backup`; bí mật trong `.env` | Mã hóa khi lưu, HTTPS, mã hóa bản sao lưu |
| Ứng dụng | Đăng nhập JWT, 3 vai trò, mật khẩu PBKDF2-SHA256, chặn dò mật khẩu, header bảo mật | Phiên làm mới token, 2 lớp xác thực |
| API | Mọi route cần quyền (mặc định chỉ quản trị), giới hạn tần suất theo IP, kiểm tra dữ liệu vào (Pydantic), chỉ chạy lệnh pipeline cố định | API gateway |
| Mô hình | Giám sát trôi phân phối nhãn và độ tin cậy; kiểm tra rò rỉ dataset; thực nghiệm đầu độc dữ liệu + phòng vệ; thực nghiệm DP-SGD; kiểm thử độ bền | DP cho toàn bộ Transformer; chống trích xuất mô hình ngoài giới hạn tần suất |
| Lưu vết | `audit_logs`: đăng nhập, thao tác ghi, xem dữ liệu chi tiết, bị từ chối, vượt giới hạn | Chính sách thời gian lưu nhật ký |

## 4. Phân quyền

| Vai trò | Được làm |
|---|---|
| Người xem | Tổng quan, Xu hướng, Mô hình (chỉ số liệu tổng hợp) |
| Phân tích viên | + dữ liệu chi tiết (đã che PII), cấu hình thu thập, chạy các bước pipeline (trừ huấn luyện) |
| Quản trị | + nội dung gốc, huấn luyện / chọn mô hình, tài khoản, nhật ký truy cập |

## 5. Khác biệt so với kiến trúc mục tiêu trong thuyết minh

- **Hàng đợi (Kafka/RabbitMQ):** chưa có. Các bước trao đổi qua PostgreSQL. Mỗi bước chỉ xử lý bản ghi chưa xử lý, nên chạy lại không bị trùng. Với quy mô thu thập bị giới hạn bởi quota YouTube, cách này đủ dùng. Hàng đợi chỉ cần khi thu thập nhiều nguồn đồng thời (T-13).
- **Phân tích thời gian thực:** pipeline chạy theo lượt (batch), không xử lý luồng liên tục.
