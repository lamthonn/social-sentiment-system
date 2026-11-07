# Hệ thống thu thập & phân tích cảm xúc, xu hướng mạng xã hội

Khung dự án (**Giai đoạn 0**) cho đề tài "Nghiên cứu các kỹ thuật máy học hiện đại kết hợp đảm bảo an ninh, an toàn... để nhận diện và phân loại cảm xúc, xu hướng của người dùng".

Giai đoạn 0 dựng sẵn: cấu trúc thư mục, PostgreSQL qua Docker, tầng cấu hình, tầng CSDL (ORM), hàm ẩn danh dữ liệu, khung API (FastAPI) và frontend (React + Ant Design).

> Hướng dẫn chạy chi tiết từng bước (kèm troubleshooting) xem tại **[HUONG_DAN_CHAY.md](HUONG_DAN_CHAY.md)**.
> Hướng dẫn sử dụng webapp (từng màn hình, vai trò, câu hỏi thường gặp): **[HUONG_DAN_SU_DUNG.md](HUONG_DAN_SU_DUNG.md)**.
> Chia việc và quy trình làm việc 2 người (Nam, Lâm) với Claude: **[team/HUONG_DAN_VIBE_CODE.md](team/HUONG_DAN_VIBE_CODE.md)**.
>
> Tình trạng dự án (nghiệp vụ, đầu việc, pipeline, model, thí nghiệm) nằm trong **[PROJECT.md](PROJECT.md)**. Công cụ xem/sửa/đồng bộ: `node tools/server.js`, xem [tools/README.md](tools/README.md).

## Yêu cầu

- Python 3.10+
- Node.js 18+ (frontend)
- Docker & Docker Compose

## Cài đặt

```bash
# 1. Tạo môi trường ảo
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Cài phụ thuộc lõi
pip install -r requirements.txt

# 3. Tạo file cấu hình từ mẫu, rồi sửa mật khẩu & salt
cp .env.example .env
```

Mở `.env` và đổi `POSTGRES_PASSWORD` cùng `ANONYMIZATION_SALT` (salt nên là chuỗi ngẫu nhiên dài, giữ bí mật).

## Chạy

**Cách nhanh (Windows):** bấm đúp `start.bat`, hoặc `python run.py` trên Linux/WSL. Một lệnh làm hết: tạo venv lần đầu, tự cài thư viện khi `requirements.txt`/`package-lock.json` đổi, bật Docker + DB, migrate, chạy API + webapp trong cùng 1 cửa sổ, mở trình duyệt. **Ctrl+C** để dừng tất cả. Muốn ép cài lại thư viện: `start.bat install`.

Hoặc chạy từng bước:

```bash
make up               # khởi động PostgreSQL + Adminer (giao diện DB ở http://localhost:8080)
make migrate          # tạo/nâng cấp bảng (chạy lại sau mỗi lần cập nhật code)
make api              # chạy API ở http://localhost:8000  (thử /health)
make frontend-install # cài phụ thuộc frontend (chạy 1 lần, hoặc khi package.json đổi)
make frontend         # chạy webapp ở http://localhost:5500
make down             # dừng các container
```

### Bảo mật khi chạy (làm 1 lần mỗi máy)

```bash
python -m security.crypto genkey   # dán kết quả vào .env: DATA_ENCRYPTION_KEY=...  (mã hóa nội dung gốc + bản sao lưu)
python -m security.tls             # chứng chỉ HTTPS tự ký -> webapp chạy ở https://localhost:5500
```

- **Mất `DATA_ENCRYPTION_KEY` là mất dữ liệu đã mã hóa.** Cất một bản khóa ở nơi riêng, không để cùng chỗ với bản sao lưu. Nếu đã có dữ liệu cũ dạng rõ, chạy `python -m security.crypto encrypt-existing`.
- Có chứng chỉ thì API chỉ nghe `127.0.0.1`, trình duyệt đi qua Vite (https). Trình duyệt sẽ cảnh báo chứng chỉ tự ký: chấp nhận một lần, hoặc nhập `data/certs/cert.pem` vào Trusted Root (certmgr.msc).
- PostgreSQL và Adminer chỉ mở trên máy này (`127.0.0.1`). Nếu cổng 5432 bị dự án khác chiếm, đặt `POSTGRES_PORT=5433` trong `.env`.

### Tạo tài khoản webapp (lần đầu)

Mọi màn hình và API (trừ `/health`) đều cần đăng nhập. Tạo tài khoản quản trị bằng dòng lệnh:

```bash
python -m security.users add nam --role admin     # hỏi mật khẩu (≥ 10 ký tự, có chữ và số)
python -m security.users list
```

Sau đó quản trị thêm tài khoản khác trong webapp (mục *Người dùng & nhật ký*). Vai trò:

| Vai trò | Được làm |
|---|---|
| Người xem (viewer) | Tổng quan, Xu hướng, Mô hình — chỉ số liệu tổng hợp |
| Phân tích viên (analyst) | + dữ liệu chi tiết (đã che SĐT/email), cấu hình thu thập, chạy các bước pipeline |
| Quản trị (admin) | + xem nội dung gốc, huấn luyện / chọn mô hình, quản lý tài khoản, xem nhật ký truy cập |

### Pipeline (thu thập → làm sạch → dataset → huấn luyện → đánh giá → dự đoán → xu hướng → giám sát)

```bash
make datasets         # tải + làm sạch UIT-VSFC (quan điểm 3 lớp) và UIT-VSMEC (cảm xúc 7 nhãn)
make train-baselines  # TF-IDF + LR/SVM cho cả 2 bài toán (vài chục giây mỗi mô hình)
make train-visobert   # fine-tune ViSoBERT (cần GPU NVIDIA)
make train-more       # BiLSTM + PhoBERT-base-v2 (PhoBERT cần GPU, tách từ bằng underthesea)
make experiments      # thực nghiệm bổ sung: đầu độc dữ liệu, gom chủ đề, DP-SGD, học liên kết, độ bền, LLM, hiệu năng, đánh giá an ninh
make backup           # sao lưu CSDL vào data/backups/
make pipeline         # 1 lượt: thu thập -> làm sạch -> dự đoán -> xu hướng -> giám sát
make test             # kiểm thử tiền xử lý
```

Có thể chạy từng bước bằng `python -m pipeline <bước>` hoặc bấm trong webapp (mục *Pipeline*). Mỗi lượt chạy được ghi vào bảng `pipeline_runs`; mỗi lần huấn luyện ghi vào `model_runs` (kết quả, ma trận nhầm lẫn, tham số). Mô hình dùng để gán nhãn tự chọn theo F1-macro cao nhất, trừ khi quản trị đã chọn tay. Thu thập cần `YOUTUBE_API_KEY` trong `.env`; nếu chưa có, bước thu thập được ghi "Bỏ qua".

Nếu không dùng `make`, xem các lệnh tương ứng trong `Makefile`.

Frontend gọi API qua Vite dev proxy (`/api/*` -> `http://localhost:8000`, xem
`frontend/vite.config.ts`) nên không cần cấu hình gì thêm khi chạy local. API
cũng đã bật CORS cho origin `http://localhost:5500` (biến `CORS_ORIGINS`
trong `.env`, xem `config/settings.py`).

## Cấu trúc thư mục

```
config/          cấu hình tập trung (đọc từ .env)
storage/         kết nối CSDL, định nghĩa bảng, migrate.py (nâng cấp bảng)
security/        ẩn danh (băm định danh), auth.py (mật khẩu, JWT, vai trò, nhật ký), users.py (CLI tài khoản)
collector/       thu thập dữ liệu YouTube/TikTok
preprocessing/   làm sạch văn bản MXH tiếng Việt (teencode, dấu thanh, emoji, che SĐT/email, spam, ngôn ngữ)
pipeline/        điều phối các bước + ghi nhật ký chạy (python -m pipeline)
models/
  sentiment/     huấn luyện/đánh giá/dự đoán quan điểm & cảm xúc (TF-IDF, ViSoBERT)
  trend/         phát hiện chủ đề (TF-IDF + NMF) và phân loại xu hướng
api/             FastAPI (+ security_mw.py: phân quyền mọi route, app_routes.py: endpoint webapp)
frontend/        webapp React + Ant Design (Vite)
data/            dataset, mô hình, log pipeline (không commit)
experiments/     thực nghiệm bổ sung cho báo cáo (kết quả: data/experiments/*.json)
docs/ARCHITECTURE.md  sơ đồ kiến trúc + mô hình dữ liệu + an ninh theo lớp của hệ thống hiện tại
tools/           công cụ quản lý PROJECT.md
```

## Lưu ý về an toàn dữ liệu

Định danh người dùng được **băm ngay tại khâu thu thập** bằng `security/anonymize.hash_identifier()` — hệ thống không lưu định danh gốc, phù hợp Luật số 91/2025/QH15. Không commit file `.env` và không commit dữ liệu thô lên kho mã.

Ngoài ra: nội dung bình luận được che số điện thoại, email, @tên trước khi phân tích; phân tích viên chỉ thấy bản đã che. Mật khẩu webapp băm PBKDF2-SHA256; đăng nhập sai 5 lần/10 phút bị chặn tạm; mọi thao tác ghi và mọi lần xem dữ liệu chi tiết đều được ghi vào nhật ký truy cập (`audit_logs`). API mặc định chỉ cho quản trị với route chưa khai báo quyền (`api/security_mw.py`).
