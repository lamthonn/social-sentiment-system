# Hướng dẫn chạy dự án

Tài liệu này hướng dẫn chạy toàn bộ hệ thống từ đầu: Database → Backend (API)
→ Frontend → Collector (thu thập dữ liệu). Viết dựa trên môi trường **WSL
(Ubuntu) trên Windows** — nếu chạy Linux/macOS thuần thì bỏ qua các phần ghi
chú riêng cho WSL.

Xem `README.md` để biết tổng quan kiến trúc/cấu trúc thư mục dự án.

---

## 0. Yêu cầu

- Python 3.10+
- Node.js 18+ (cài **trong WSL**, không dùng `npm`/`node` của Windows — xem mục Troubleshooting #4 nếu nhầm)
- Docker & Docker Compose
- (Tùy chọn nhưng khuyên dùng) `tmux` — để chạy collector định kỳ bền vững

Kiểm tra nhanh trước khi bắt đầu:
```bash
python3 --version
node --version && npm --version
docker --version && docker compose version
```

---

## 1. Cài đặt lần đầu

```bash
# 1. Tạo virtual environment (Python)
python3 -m venv .venv
source .venv/bin/activate     # nhớ chạy lại dòng này mỗi khi mở terminal mới

# 2. Cài thư viện Python
pip install -r requirements.txt

# 3. Tạo file cấu hình
cp .env.example .env
```

Mở `.env`, đổi tối thiểu:
- `POSTGRES_PASSWORD` — mật khẩu DB
- `ANONYMIZATION_SALT` — chuỗi ngẫu nhiên dài, giữ bí mật (dùng để băm định danh người dùng)

**Không commit file `.env` lên Git** (đã có trong `.gitignore`).

---

## 2. Chạy Database (PostgreSQL qua Docker)

```bash
docker compose up -d
docker compose ps        # xác nhận sss_postgres và sss_adminer đều "Up", có cột PORTS
```

Tạo bảng:
```bash
python3 -c "from storage.database import init_db; init_db(); print('DB initialized')"
```

**Xem dữ liệu qua Adminer**: http://localhost:8080
| Trường | Giá trị |
|---|---|
| System | **PostgreSQL** (không phải MySQL) |
| Server | `db` (tên service trong `docker-compose.yml` — **không phải** `localhost`, vì Adminer chạy trong container riêng) |
| Username/Password/Database | lấy từ `.env` (`POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`) |

> Nếu `docker compose up -d` báo lỗi "port already allocated" → xem Troubleshooting #1.

---

## 3. Chạy Backend (FastAPI)

```bash
source .venv/bin/activate    # nếu chưa activate
make api
```
→ http://localhost:8000 — thử `/health` phải ra `{"status":"ok"}`.

Backend đã bật CORS cho origin `http://localhost:5500` (biến `CORS_ORIGINS` trong
`.env`). **Đổi `.env` xong phải restart `make api`** để nhận cấu hình mới (`.env`
chỉ được đọc lúc khởi động).

---

## 4. Chạy Frontend (React + Ant Design)

```bash
cd frontend
npm install        # chỉ cần lần đầu, hoặc khi package.json đổi
npm run dev
```
→ http://localhost:5500

Frontend có 3 tab:
- **Tổng quan**: số liệu thống kê (tổng bài thu thập, đã phân tích...)
- **Dữ liệu thu thập**: bảng xem trực tiếp các bài/comment đã thu thập
- **Cấu hình thu thập**: quản lý từ khóa search + video theo dõi cố định (xem mục 6)

> Nếu báo `vite: not found` → chưa `npm install` (xem Troubleshooting #5).
> Nếu port 5500 bị chiếm bởi tiến trình khác → đổi port trong `frontend/vite.config.ts` (`server.port`) và cập nhật lại `CORS_ORIGINS` trong `.env`.

---

## 5. Thu thập dữ liệu (Collector)

### 5.1. YouTube — lấy API key

1. [Google Cloud Console](https://console.cloud.google.com/) → tạo/chọn project
2. **APIs & Services → Library** → bật **YouTube Data API v3**
3. **APIs & Services → Credentials** → **Create credentials → API key**
4. (Khuyến nghị) Giới hạn key: **API restrictions → Restrict key → YouTube Data API v3**
5. Dán vào `.env`: `YOUTUBE_API_KEY=...`

### 5.2. TikTok (tùy chọn — cần đăng ký & chờ duyệt)

Xem hướng dẫn chi tiết trong `collector/README.md`. Cần `TIKTOK_CLIENT_KEY` +
`TIKTOK_CLIENT_SECRET` trong `.env`. **Lưu ý**: code TikTok chưa được xác minh
bằng key thật — đọc kỹ cảnh báo trong `collector/README.md` trước khi tin dữ
liệu ẩn danh của nền tảng này.

### 5.3. Chạy thử thủ công (1 lần)

```bash
# Theo video ID/URL cụ thể
python -m collector run --platform youtube --video <video_id_hoặc_URL>

# Tìm theo từ khóa (không cần biết trước video)
python -m collector search --query "giá vàng" --max-videos 5 --days 7
```

### 5.4. Cấu hình thu thập tự động qua UI

Mở frontend → tab **"Cấu hình thu thập"**:
- **Từ khóa tìm kiếm** (chỉ YouTube): thêm từ khóa, số video tối đa/lượt, số ngày gần đây, bật/tắt
- **Video theo dõi cố định** (YouTube hoặc TikTok): dán video ID hoặc URL, theo dõi liên tục

Lưu qua UI ghi thẳng vào DB — **chỉ có tác dụng khi có tiến trình `schedule` đang
chạy** để đọc và thực thi (xem mục 5.5). Lưu xong mà không chạy scheduler thì
không có gì được thu thập.

### 5.5. Chạy định kỳ (scheduler) — BẮT BUỘC để tự động thu thập

```bash
make collect-schedule
# hoặc: python -m collector schedule
```
Đọc lại cấu hình từ DB **mỗi lượt chạy** (mặc định mỗi 60 phút, đổi qua
`COLLECTOR_POLL_INTERVAL_MINUTES` trong `.env`) — sửa cấu hình qua UI trong lúc
scheduler đang chạy có hiệu lực ngay ở lượt kế tiếp, không cần restart.

**Chạy trực tiếp trong terminal sẽ chết khi đóng terminal/tắt máy.** Muốn chạy
bền vững, dùng `tmux`:
```bash
sudo apt install -y tmux      # cài 1 lần nếu chưa có
tmux new -s collector
source .venv/bin/activate
make collect-schedule
# Ctrl+B rồi D để thoát ra ngoài mà không tắt tiến trình
```
Xem lại log sau này: `tmux attach -t collector`. Xem các session đang chạy: `tmux ls`.

---

## 6. Dừng toàn bộ

```bash
# Ctrl+C ở từng terminal đang chạy: make api / npm run dev / make collect-schedule
docker compose down     # dừng Postgres + Adminer
```

---

## Troubleshooting — các lỗi hay gặp

### 1. `docker compose up -d` báo "port already allocated" (5432)
Có tiến trình khác (Postgres native, hoặc container cũ) đang chiếm cổng 5432.
```bash
sudo lsof -i :5432          # xem cái gì đang chiếm
docker compose down && docker compose up -d   # thử lại sau khi dừng cái chiếm cổng
```
Hoặc đổi cổng: sửa `.env` → `POSTGRES_PORT=5433` rồi chạy lại (không cần sửa gì thêm,
`config/settings.py` cũng đọc biến này).

### 2. `make: command not found`
```bash
sudo apt install make
```
Hoặc chạy thẳng lệnh Python/npm bên trong `Makefile` (xem file đó để biết lệnh gốc).

### 3. `python: command not found` (chỉ có `python3`)
```bash
sudo apt install python-is-python3
```

### 4. `npm install`/`npm run dev` lỗi kỳ lạ (đường dẫn `D:\...`, hoặc `ENOENT`)
`npm` đang trỏ vào `npm.exe` của **Windows** qua WSL interop, không phải Node cài
trong WSL. Kiểm tra: `which npm` — nếu ra `/mnt/c/...` thì đúng bệnh này. Cài Node
thật trong WSL:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install --lts
```

### 5. `sh: vite: not found`
Chưa `npm install` trong `frontend/` (hoặc `node_modules` bị thiếu). Chạy `npm
install` trong thư mục `frontend/` trước khi `npm run dev`.

### 6. `.venv` báo lỗi lạ / không tìm thấy `activate`
Venv Python **không dùng chéo được giữa Windows và WSL** (khác cấu trúc thư mục:
`Scripts/` vs `bin/`). Nếu từng tạo `.venv` bên Windows rồi dùng trong WSL (hoặc
ngược lại), xóa và tạo lại đúng trong môi trường đang dùng:
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 7. Adminer báo lỗi "Connection refused" dù Postgres đang chạy
Server phải là `db` (tên service trong `docker-compose.yml`), **không phải**
`localhost` — vì Adminer chạy trong container riêng, `localhost` từ trong đó trỏ
vào chính container Adminer chứ không phải Postgres.

### 8. Đổi `.env` (VD `CORS_ORIGINS`) xong mà không có tác dụng
`.env` chỉ được đọc **lúc khởi động** process. Phải restart lại `make api` (Ctrl+C
rồi chạy lại) để nhận giá trị mới.

### 9. Cấu hình từ khóa/video qua UI xong mà "Tổng bài thu thập" không tăng
Cấu hình qua UI chỉ lưu vào DB — **không tự chạy gì**. Phải có tiến trình
`python -m collector schedule` đang chạy để đọc và thực thi. Kiểm tra:
```bash
ps aux | grep collector
```
Không thấy gì → chưa chạy hoặc đã bị kill (do đóng terminal) → xem mục 5.5, chạy
qua `tmux` để không bị tắt khi đóng terminal.

### 10. Video ID dán nhầm (VD dính cả `?list=...` của playlist)
Không cần lo — CLI/API đều tự trích đúng video ID dù bạn dán ID trần hay nguyên
URL đầy đủ (kể cả kèm tham số playlist/timestamp thừa).

### 11. Port 5500 (frontend) hoặc 5173 bị chiếm bởi ứng dụng khác
Đổi port trong `frontend/vite.config.ts` (`server.port`), nhớ cập nhật lại
`CORS_ORIGINS` trong `.env` cho khớp, rồi restart cả `make api` lẫn `npm run dev`.
