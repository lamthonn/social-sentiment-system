# Hệ thống thu thập & phân tích cảm xúc, xu hướng mạng xã hội

Khung dự án (**Giai đoạn 0**) cho đề tài "Nghiên cứu các kỹ thuật máy học hiện đại kết hợp đảm bảo an ninh, an toàn... để nhận diện và phân loại cảm xúc, xu hướng của người dùng".

Giai đoạn 0 dựng sẵn: cấu trúc thư mục, PostgreSQL qua Docker, tầng cấu hình, tầng CSDL (ORM), hàm ẩn danh dữ liệu, khung API (FastAPI) và dashboard (Streamlit).

## Yêu cầu

- Python 3.10+
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

```bash
make up          # khởi động PostgreSQL + Adminer (giao diện DB ở http://localhost:8080)
make initdb      # tạo bảng trong cơ sở dữ liệu
make api         # chạy API ở http://localhost:8000  (thử /health)
make dashboard   # chạy dashboard ở http://localhost:8501
make down        # dừng các container
```

Nếu không dùng `make`, xem các lệnh tương ứng trong `Makefile`.

## Cấu trúc thư mục

```
config/          cấu hình tập trung (đọc từ .env)
storage/         kết nối CSDL + định nghĩa bảng (RawPost, AnalysisResult)
security/        ẩn danh (băm định danh người dùng)
collector/       thu thập dữ liệu            (Giai đoạn 2)
preprocessing/   tiền xử lý NLP tiếng Việt   (Giai đoạn 1)
models/
  sentiment/     mô hình cảm xúc             (Giai đoạn 1)
  trend/         mô hình xu hướng            (Giai đoạn 4)
api/             FastAPI
dashboard/       Streamlit
data/            dữ liệu (không commit dữ liệu thô)
notebooks/       thử nghiệm & đánh giá
```

## Lưu ý về an toàn dữ liệu

Định danh người dùng được **băm ngay tại khâu thu thập** bằng `security/anonymize.hash_identifier()` — hệ thống không lưu định danh gốc, phù hợp Luật số 91/2025/QH15. Không commit file `.env` và không commit dữ liệu thô lên kho mã.

## Các bước tiếp theo

- Giai đoạn 1: tải bộ dữ liệu UIT-VSMEC/UIT-VSFC, viết tiền xử lý và pipeline fine-tune PhoBERT/ViSoBERT.
- Giai đoạn 2: viết collector cho một nền tảng, lập lịch, ghi vào `raw_posts`.
