"""Tạo bảng mới và nâng cấp bảng cũ (idempotent - chạy nhiều lần không lỗi).

`init_db()` (create_all) chỉ tạo bảng chưa có, không thêm cột cho bảng đã tồn tại -> các
thay đổi trên bảng cũ viết ở đây bằng lệnh có IF NOT EXISTS.

Chạy: python -m storage.migrate
"""
from sqlalchemy import text

from storage.database import engine, init_db

UPGRADES = [
    # analysis_results: thêm cột task (sentiment / emotion) + chặn trùng (bài, task, model)
    "ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS task VARCHAR(32) NOT NULL DEFAULT 'sentiment'",
    "CREATE INDEX IF NOT EXISTS ix_analysis_results_task ON analysis_results (task)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_post_task_model ON analysis_results (raw_post_id, task, model_name)",
    "ALTER TABLE model_runs ADD COLUMN IF NOT EXISTS selected_by VARCHAR(64)",
    "ALTER TABLE clean_posts ADD COLUMN IF NOT EXISTS hashtags TEXT",
    "UPDATE model_runs SET selected_by = 'auto' WHERE selected AND selected_by IS NULL",
    # bản đầu lưu đường dẫn kiểu Windows ("\") -> đổi sang "/" (chr(92) = "\")
    "UPDATE model_runs SET artifact_path = replace(artifact_path, chr(92), '/') WHERE strpos(artifact_path, chr(92)) > 0",
    # raw_posts.category do Lâm thêm sau - đảm bảo DB tạo từ bản cũ cũng có cột này
    "ALTER TABLE raw_posts ADD COLUMN IF NOT EXISTS category VARCHAR(255)",
    "CREATE INDEX IF NOT EXISTS ix_raw_posts_category ON raw_posts (category)",
]


def migrate() -> None:
    init_db()
    with engine.begin() as conn:
        for sql in UPGRADES:
            conn.execute(text(sql))


if __name__ == "__main__":
    migrate()
    print("Migration OK")
