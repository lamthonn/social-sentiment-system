# Lịch sử chỉnh sửa

Mỗi lần sửa dự án thêm **một mục mới lên đầu danh sách** (mới nhất trước), không sửa hay xóa mục cũ. Tổng quan hệ thống ở [TONG_QUAN.md](TONG_QUAN.md).

Mẫu mục:

```markdown
## YYYY-MM-DD · Tên người · Tóm tắt một dòng
- **Sửa gì:** ...
- **File chính:** ...
- **Ghi chú:** việc người kia cần làm (chạy migrate, thêm biến .env...), hoặc "không"
```

Người sửa ghi tên thật (Nam hoặc Lâm). Nếu Claude làm trên máy của ai thì ghi tên người đó, thêm "(cùng Claude)". Các mục trước 2026-11-24 được dựng lại từ lịch sử git, nên chỉ ghi ở mức tổng quát.

---

## 2026-11-25 · Lâm (cùng Claude) · Đưa từ khóa và kênh theo dõi mặc định vào dữ liệu khởi tạo
- **Sửa gì:** Cấu hình thu thập mặc định (5 từ khóa, 11 kênh theo dõi, trong đó VTV24 và Báo Tuổi Trẻ ở trạng thái tắt) nằm trong `config/collector_seed.json`. `python -m storage.migrate` (cũng chạy trong `start.bat`) nạp file này vào DB mới. Chỉ nạp vào bảng **đang trống** (`search_queries`, `tracked_channels` kiểm tra riêng), nên máy đã có cấu hình hoặc đã xóa có chủ ý không bị ghi đè, chạy lại không nhân đôi. Muốn đổi mặc định thì sửa file JSON, không cần sửa code. Đổi mặc định `COLLECTOR_POLL_INTERVAL_MINUTES` trong `.env.example` từ 60 sang 180 (lý do ở mục trước, về quota).
- **File chính:** `config/collector_seed.json` (mới), `storage/seed.py` (mới), `storage/migrate.py` (gọi seed ở cuối `migrate()`), `.env.example`, `tests/test_seed.py` (mới, 2 test)
- **Ghi chú:**
  - Nam: sau khi ghép, DB của bạn nếu đang trống sẽ có sẵn các nguồn này. DB đã có từ khóa hoặc kênh thì không đổi gì.
  - Seed chỉ chứa nguồn thu thập, không chứa nút bật/tắt "Thu thập tự động" (vẫn tắt mặc định, bật trên giao diện).
  - Chưa chạy migrate trên Postgres thật vì lúc làm DB đang tắt; đã kiểm bằng SQLite trong test.

## 2026-11-25 · Lâm (cùng Claude) · Xóa dữ liệu giá vàng cũ, thêm từ khóa và nguồn, lọc video thịnh hành tiếng Anh
- **Sửa gì:**
  - **Bắt đầu lại dữ liệu:** xóa 1.875 bình luận `category = 'giá vàng'` thu trước 24/11 (chưa có dòng nào trong `clean_posts` hay `analysis_results`). Giữ 141 bình luận không có category (bình luận một video nhạc, không phải giá vàng). Đã sao lưu trước khi xóa (`data/backups/20261125-092029-sss_db_nckh.sql.gz`, chưa mã hóa vì chưa đặt `DATA_ENCRYPTION_KEY`).
  - **Thêm từ khóa** (5 video/lượt, trong 3 ngày): `giá xăng`, `chứng khoán`, `bão lũ miền Trung`, `bóng đá Việt Nam`. Từ khóa `giá vàng` giữ nguyên.
  - **Thêm 8 kênh theo dõi** (5 video mới nhất/lượt): Hoàng Thùy Linh, ERIK (âm nhạc), Trực Tiếp Game, Bi Huỳnh Gaming (game), Toga TV (gia đình), W2W Movie (phim), bqThanh (giải trí), Ống Kính Sài Gòn (đời sống). Tắt VTV24 và Báo Tuổi Trẻ vì mọi video đều tắt bình luận.
  - **Chu kỳ thu thập 60 → 180 phút** (`COLLECTOR_POLL_INTERVAL_MINUTES` trong `.env`). Lý do: 5 từ khóa × 100 unit × 24 lượt = 12.000 unit/ngày, vượt hạn mức 10.000. Với 180 phút còn khoảng 8 lượt/ngày, ước tính 6.000–7.000 unit/ngày.
  - **Sửa lỗi trending:** chart `mostPopular` của VN lẫn video quốc tế (skibidi, MrBeast, Marvel), kéo về hơn 17.000 bình luận tiếng Anh chỉ trong một lượt. Nay bỏ video có `defaultLanguage` hoặc `defaultAudioLanguage` khác `vi`; video không khai báo ngôn ngữ vẫn giữ. Thêm 1 test.
- **File chính:** `collector/pipeline.py` (`_is_vietnamese_video`), `tests/test_collector.py`, cấu hình trong DB (`search_queries`, `tracked_channels`), `.env`
- **Ghi chú:**
  - **Cần khởi động lại API** để nhận chu kỳ 180 phút trong `.env`. Trước khi khởi động lại, chu kỳ 60 phút với 5 từ khóa sẽ ngốn quota rất nhanh.
  - Các bình luận tiếng Anh từ video trending đã thu trước khi sửa vẫn còn trong `raw_posts` (category `trending`, khoảng 17.000 dòng, thuộc 3 video skibidi / MrBeast Gaming / Marvel). Chưa xóa, chờ quyết định.
  - Pipeline xu hướng của Nam: category của bình luận chính là chuỗi từ khóa, nên xu hướng được tính riêng theo từng chủ đề.

## 2026-11-25 · Lâm (cùng Claude) · T-10: tab "Video" xem thông tin video và lượt like
- **Sửa gì:** Thêm tab **Video** trong trang Thu thập: bảng video (tiêu đề, kênh, lượt xem, like, bình luận, số bình luận đã thu; tìm theo tiêu đề hoặc kênh; sắp xếp theo xem, thích, bình luận, ngày đăng). Bấm một video mở ngăn chi tiết: mô tả, tag, biểu đồ lượt xem và like theo thời gian (từ `video_stats_snapshots`), 10 bình luận nhiều like nhất. Số liệu trong bảng là lần chụp gần nhất. Bình luận chỉ hiện `clean_text` (đã che PII), không bao giờ trả nội dung gốc.
- **File chính:** `api/main.py` (`GET /videos`, `GET /videos/{video_id}`), `api/schemas.py`, `api/security_mw.py`, `frontend/src/VideosTab.tsx` (mới), `frontend/src/api.ts`, `frontend/src/App.tsx`, `tests/test_videos_api.py` (mới, 4 test)
- **Ghi chú:**
  - Không đổi schema DB, không cần migrate.
  - `RULES` thêm `videos.*` cho phân tích viên trở lên (chỉ GET).
  - Tab Video hiện cho cả analyst; admin thấy thêm tab Dữ liệu thô như cũ.
  - Chưa thử trên Postgres thật vì lúc làm DB đang tắt; đã kiểm bằng SQLite trong test và `npm run build`.

## 2026-11-24 · Lâm (cùng Claude) · Gộp toàn bộ tài liệu .md thành hai file
- **Sửa gì:** Xóa 17 file .md (`PROJECT.md`, `README.md`, `HUONG_DAN_CHAY.md`, `HUONG_DAN_SU_DUNG.md`, `collector/README.md`, `preprocessing/README.md`, `frontend/README.md`, `tools/README.md`, `docs/*.md`, `docs/slide/KICH_BAN_THUYET_TRINH.md`, `team/*.md`). Viết lại thành `TONG_QUAN.md` (ý tưởng, thiết kế, ứng dụng, kết quả, phân công) và file này (lịch sử sửa đổi). `CLAUDE.md` được giữ và sửa lại cho khỏi trỏ vào file đã xóa.
- **File chính:** `TONG_QUAN.md`, `LICH_SU_CHINH_SUA.md`, `CLAUDE.md`
- **Ghi chú:**
  - **`tools/server.js` và giao diện quản lý dự án không còn dùng được**, vì chúng đọc và ghi `PROJECT.md`. Thư mục `tools/` được giữ nguyên chờ quyết định xóa hoặc viết lại.
  - Nhật ký chi tiết của từng đầu việc T-xx, mã quyết định QD-xx, lần huấn luyện R-xx từng nằm ở `PROJECT.md`. Phần đáng giữ đã gộp vào `TONG_QUAN.md` (mục 1.4 và 4); bản đầy đủ lấy lại bằng `git show 17bce11:PROJECT.md`. Tương tự cho mọi file đã xóa, ví dụ lý thuyết mô hình: `git show 17bce11:docs/LY_THUYET_MO_HINH.md`.
  - Docstring trong `collector/youtube_client.py`, `pipeline/__init__.py`, `preprocessing/*.py`, `storage/models.py`, `Makefile` còn nhắc tên các file .md cũ. Chưa sửa vì không ảnh hưởng chạy, sẽ dọn khi sửa các file đó.
  - Phần sửa của Nam: `team/nam.md`, `docs/ARCHITECTURE.md`, `HUONG_DAN_SU_DUNG.md`, `tools/README.md` nằm trong số file bị xóa. Nam xem lại trong PR.

## 2026-11-24 · Lâm (cùng Claude) · T-09: thu thập thêm like, trả lời, thông tin video; thêm nguồn kênh và thịnh hành
- **Sửa gì:**
  - `raw_posts` thêm 4 cột nullable `video_id`, `parent_id`, `like_count`, `reply_count`. Thu thêm trả lời của bình luận. Gặp lại bình luận cũ thì cập nhật số like và số trả lời.
  - Thêm bảng `video_meta` (tiêu đề, mô tả, tags, kênh, `categoryId`, ngày đăng) và `video_stats_snapshots` (view/like/comment mỗi lượt thu thập, tạo chuỗi thời gian).
  - Thêm nguồn **kênh theo dõi** (bảng `tracked_channels`, API `/tracked-channels`, panel trong tab Cấu hình thu thập; nhận `@handle`, URL hoặc ID kênh) và **video thịnh hành** (`COLLECTOR_TRENDING_*`). Rẻ hơn nhiều so với `search.list` (100 unit/lần).
  - Lượt định kỳ chạy chế độ tăng dần: dừng khi gặp trang không có bình luận mới. Video không có bình luận bị bỏ qua. Lỗi một nguồn không làm dừng các nguồn còn lại.
  - Thêm 12 test mới trong `tests/test_collector.py` (SQLite trong bộ nhớ và client YouTube giả). Toàn bộ 41 test pass, `npm run build` qua.
- **File chính:** `collector/youtube_client.py`, `collector/pipeline.py`, `collector/scheduler.py`, `storage/models.py`, `storage/migrate.py`, `api/main.py`, `api/schemas.py`, `api/security_mw.py`, `config/settings.py`, `.env.example`, `frontend/src/CollectorConfig.tsx`, `frontend/src/api.ts`, `tests/test_collector.py`
- **Ghi chú:**
  - **Phải chạy `python -m storage.migrate`** (hoặc `start.bat`) sau khi ghép. Dữ liệu cũ để NULL, code đọc `raw_posts` hiện có không bị ảnh hưởng.
  - Biến `.env` mới, đều tùy chọn và có mặc định: `COLLECTOR_FETCH_REPLIES`, `COLLECTOR_TRENDING_ENABLED`, `COLLECTOR_TRENDING_REGION`, `COLLECTOR_TRENDING_MAX_VIDEOS`.
  - Dòng `RULES` mới trong `api/security_mw.py` cho `/tracked-channels` (phân tích viên trở lên).
  - Cho pipeline xu hướng của Nam: `parent_id IS NULL` là bình luận gốc; `like_count` dùng làm trọng số; `video_stats_snapshots` là chuỗi thời gian; bình luận từ video thịnh hành có `category = 'trending'`.
  - Chưa chạy thật với YouTube vì Postgres không chạy trên máy đã làm việc này. Việc còn lại: bật Postgres, migrate, thêm kênh/video, gạt nút "Thu thập tự động".

## 2026-11-11 · Lâm · Thêm tài liệu lý thuyết và slide thuyết trình
- **Sửa gì:** Thêm `docs/LY_THUYET_MO_HINH.md` (cơ sở lý thuyết các mô hình), `docs/slide/KICH_BAN_THUYET_TRINH.md` (kịch bản 14 slide) và `docs/slide/NCKH_thuyet_trinh.pptx`.
- **File chính:** `docs/`
- **Ghi chú:** không. File .pptx vẫn còn; hai file .md bị xóa ở mục 2026-11-24.

## 2026-11-07 · Nam · Hướng dẫn sử dụng và quy trình làm việc hai người (PR #2)
- **Sửa gì:** Thêm `HUONG_DAN_SU_DUNG.md`, `team/` (hướng dẫn vibe code, sổ việc của Nam và Lâm), `CLAUDE.md`, `docs/ARCHITECTURE.md`. Sửa `api/app_routes.py`, `api/security_mw.py`, `config/settings.py`, `docker-compose.yml`, `frontend/src/App.tsx`, `.gitattributes`, `.gitignore`. Mã hóa nội dung thu thập khi lưu (`security/crypto.py`), HTTPS (`security/tls.py`), sao lưu có mã hóa (`storage/backup.py`), `pipeline/steps.py`. Chia việc theo module giữa Nam và Lâm.
- **File chính:** `CLAUDE.md`, `team/`, `security/`, `api/`
- **Ghi chú:** cần `DATA_ENCRYPTION_KEY` trong `.env` để mã hóa nội dung; chạy `python -m security.crypto genkey`.

## 2026-11-06 · Nam · Ghép `main` vào nhánh `feat/pipeline-webapp`
- **Sửa gì:** Merge `origin/main` vào nhánh pipeline và webapp để giải quyết khác biệt trước khi mở PR.
- **File chính:** không có thay đổi mới về nội dung
- **Ghi chú:** không.

## 2026-11-02 · Lâm · Bộ tiền xử lý riêng, chạy một lệnh
- **Sửa gì:** Thêm bộ tiền xử lý tiếng Việt riêng (`preprocessing/cleaner.py`, `teencode.py`, `tokenizer.py`, `pipeline.py`) và `tests/` cho nó. Thêm `run.py` và `start.bat` để chạy cả hệ thống bằng một lệnh. Ghép nhánh pipeline học máy và webapp của Nam vào nhánh này.
- **File chính:** `preprocessing/`, `tests/`, `run.py`, `start.bat`, `Makefile`, `requirements.txt`
- **Ghi chú:** Hiện có hai bộ làm sạch chạy song song (`preprocessing/text.py` của Nam, bộ của Lâm). Chỉ `text.py` đang được pipeline dùng. Việc hợp nhất chưa chốt (xem `TONG_QUAN.md` mục 1.4).

## 2026-11-01 · Nam · Đánh giá cơ chế an ninh và mô phỏng học liên kết
- **Sửa gì:** Thêm `security/detect.py` (luật phát hiện tấn công trên nhật ký truy cập), `experiments/security_eval.py` (đánh giá cơ chế an ninh) và `experiments/federated.py` (FedAvg 5 bên, IID và Non-IID, 3 seed).
- **File chính:** `security/detect.py`, `experiments/`, `data/experiments/*.json`
- **Ghi chú:** không.

## 2026-11-01 · Nam · Dựng pipeline học máy, thực nghiệm và webapp quản lý (PR #1)
- **Sửa gì:** Thêm `pipeline/` (datasets, train, collect, clean, predict, trends, monitor, ghi `pipeline_runs`), `models/sentiment/` (TF-IDF, BiLSTM, ViSoBERT, PhoBERT, bộ tách từ SPM cho ViSoBERT), `models/trend/` (TF-IDF + NMF), `experiments/` (đầu độc dữ liệu, gom chủ đề, DP-SGD, độ bền, LLM, hiệu năng), `security/` (đăng nhập, vai trò, nhật ký truy cập), `api/app_routes.py` và `api/security_mw.py`, và các trang webapp: Tổng quan, Xu hướng, Dữ liệu đã phân tích, Mô hình, Pipeline, Người dùng và nhật ký. Huấn luyện các lần R-01 đến R-10 trên UIT-VSFC và UIT-VSMEC.
- **File chính:** `pipeline/`, `models/`, `experiments/`, `security/`, `api/`, `frontend/src/`, `preprocessing/text.py`
- **Ghi chú:** `storage/migrate.py` ra đời ở lần này; chạy `python -m storage.migrate` sau mỗi lần cập nhật code.

## 2026-10-30 · Nam · Tạo PROJECT.md
- **Sửa gì:** Tạo `PROJECT.md`: tổng quan đề tài, giai đoạn, nghiệp vụ, 49 đầu việc, pipeline, mô hình, quyết định (QD-01 đến QD-06). Sau đó chỉnh TQ-01 và thêm tài liệu dự án.
- **File chính:** `PROJECT.md`
- **Ghi chú:** file này bị thay thế bởi `TONG_QUAN.md` ở mục 2026-11-24.

## 2026-10-29 · Nam · Công cụ quản lý đề tài `pm/`
- **Sửa gì:** Thêm thư mục `pm/` (công cụ quản lý đề tài, tài liệu DOC-001 đến DOC-004, các ứng dụng mẫu APP-001 đến APP-003, khoảng 175 file) và cập nhật chỉ mục.
- **File chính:** `pm/`
- **Ghi chú:** thư mục này về sau không còn trên cây thư mục hiện tại; bản cũ có trong lịch sử git.

## 2026-09-15 · Lâm · Nút bật/tắt thu thập tự động
- **Sửa gì:** Scheduler chạy nền trong tiến trình API, bật/tắt từ giao diện, trạng thái lưu trong bảng `scheduler_state` nên nhớ qua lần khởi động lại. Thêm endpoint `/scheduler` và `/scheduler/toggle`.
- **File chính:** `collector/scheduler.py`, `api/main.py`, `api/schemas.py`, `storage/models.py`, `frontend/src/CollectorConfig.tsx`
- **Ghi chú:** không.

## 2026-09-04 · Lâm · Gắn chủ đề (category) cho bình luận
- **Sửa gì:** Thêm cột `raw_posts.category` (từ khóa hoặc ghi chú của nguồn đã sinh ra bình luận), tham số `--category` cho CLI, endpoint danh sách category và bộ lọc theo category ở bảng dữ liệu thô. Gộp nhánh `main` với bản trên GitHub.
- **File chính:** `collector/pipeline.py`, `collector/__main__.py`, `collector/scheduler.py`, `api/main.py`, `storage/models.py`, `frontend/src/PostsTable.tsx`
- **Ghi chú:** không.

## 2026-09-03 · Nam, Lâm · Tài liệu nghiệp vụ, kiến trúc thu thập, hướng dẫn chạy
- **Sửa gì:** Nam thêm ba tài liệu: phân tích nghiệp vụ và khung khảo sát, thiết kế kiến trúc thu thập động đa nền tảng, giải đáp bài toán crawl và dự đoán xu hướng. Lâm thêm `HUONG_DAN_CHAY.md`, favicon và chỉnh `README.md`, `App.tsx`.
- **File chính:** `docs/`, `HUONG_DAN_CHAY.md`
- **Ghi chú:** các tài liệu này bị xóa ở mục 2026-11-24; nội dung thiết kế mục tiêu (hàng đợi, các tầng thu thập) chưa được cài đặt.

## 2026-08-30 · Lâm · Khởi tạo dự án và module thu thập
- **Sửa gì:** Khung dự án giai đoạn 0 và code nền: cấu hình, PostgreSQL qua Docker, ORM, ẩn danh bằng băm, FastAPI, frontend React + Ant Design, collector YouTube. Cùng ngày: client TikTok (chưa thử với key thật), scheduler định kỳ, tìm video theo từ khóa, chuyển cấu hình video và từ khóa theo dõi từ `.env` sang giao diện và DB (bảng `search_queries`, `tracked_videos`).
- **File chính:** toàn bộ cây thư mục ban đầu, `collector/`, `api/`, `frontend/src/CollectorConfig.tsx`
- **Ghi chú:** không.
