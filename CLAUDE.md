# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Research prototype for a Vietnamese master's/NCKH project: collect public social-media comments (YouTube, TikTok), store them anonymized in PostgreSQL, and later classify sentiment/emotion and detect trends. Work is organized in phases ("Giai đoạn"):

- **Phase 0 (done):** config, DB/ORM, anonymization, FastAPI skeleton, React + Ant Design frontend.
- **Phase 2 (done):** collectors (YouTube working; TikTok scaffolded but **never tested with real keys**), scheduler, UI-managed collection config.
- **Phase 1 (not started):** Vietnamese NLP preprocessing (`preprocessing/`) and PhoBERT/ViSoBERT fine-tuning on UIT-VSMEC/UIT-VSFC (`models/sentiment/`). The ML dependencies in `requirements.txt` are commented out.
- **Phase 4 (not started):** trend modeling (`models/trend/`).

Code comments, docstrings, log messages, API error messages and UI strings are in Vietnamese — keep new ones consistent. `docs/` holds research/design write-ups (business analysis, crawling Q&A, target dynamic-crawling architecture) that describe intended future design, not current code.

## Project management (`PROJECT.md` + `tools/`)

`PROJECT.md` at the repo root is the single source of project status. It covers overview and phases (GD-xx = research contents from section 7 of the proposal), business analysis (NV-xx), tasks (T-xx), pipeline steps (PL-xx), data sources (DS), cleaning steps (CL), storage (ST), models (M), training runs (R), application problems (BT), and the decision log (QD). The format rules are in the HTML comment at the top of the file:
- one `### ID Title` block per object, with attributes as `- **Key:** value`;
- log lines are append-only: `- [Nam · YYYY-MM-DD HH:MM] [Kind] text`;
- IDs are never reused;
- no aggregate numbers and no deadlines are stored in the file.

The UI is `node tools/server.js` (Node built-ins only, port 8765; see `tools/README.md`). It patches only the lines of the edited block, so keep the format when editing by hand.

Record each training run as a new `R-xx` block with its metrics (Accuracy, F1-macro, Precision, Recall). Content must come from the proposal (`TM_final.docx`): mark your own suggestions "(đề xuất)", and write "Chưa có trong thuyết minh" where the proposal is silent.

## Commands

Run everything from the repo root (`config/settings.py` loads `.env` relative to the CWD). Activate `.venv` first. `HUONG_DAN_CHAY.md` is the detailed run guide (written for WSL) with troubleshooting.

```bash
cp .env.example .env          # set POSTGRES_PASSWORD, ANONYMIZATION_SALT, YOUTUBE_API_KEY
make up                       # Postgres 16 + Adminer (http://localhost:8080, server name "db")
make initdb                   # Base.metadata.create_all
make api                      # uvicorn api.main:app --reload on :8000 (GET /health)
make frontend-install         # npm install --prefix frontend
make frontend                 # Vite dev server on :5500 (strictPort)
make collect-schedule         # python -m collector schedule (long-running)
make down

# One-off collection via CLI (accepts bare IDs or full URLs)
python -m collector run --platform youtube --video <id_or_url> [--video ...] [--max-pages N]
python -m collector search --query "giá vàng" --max-videos 5 --days 7

# Frontend checks (in frontend/)
npm run lint                  # oxlint
npm run build                 # tsc -b && vite build (type-check)
```

There is no test suite, no Python linter config, and no migration tool. `init_db()` only creates missing tables — changing columns on an existing table requires manual SQL or dropping the table.

## Architecture

Three independent processes share one PostgreSQL database; there is no queue or IPC between them:

1. **API** (`api/main.py`, FastAPI) — read endpoints (`/stats`, `/posts`) and CRUD for collector config (`/search-queries`, `/tracked-videos`). Pydantic schemas in `api/schemas.py` are kept separate from ORM models in `storage/models.py`; the frontend mirrors them by hand in `frontend/src/api.ts`, so update both when changing a response shape.
2. **Scheduler** (`collector/scheduler.py`, APScheduler `BlockingScheduler`) — runs one job immediately, then every `COLLECTOR_POLL_INTERVAL_MINUTES`. Each run **re-reads `tracked_videos` and `search_queries` from the DB**, so config changes made through the UI apply on the next tick without restarting. Saving config in the UI does nothing unless this process is running.
3. **Frontend** (`frontend/`, React 19 + antd 5 + Vite) — in dev, calls `/api/*`, which Vite proxies to `localhost:8000` with the `/api` prefix stripped. `VITE_API_BASE_URL` overrides this for production builds. The API's `CORS_ORIGINS` must match the frontend origin if the port changes.

### Collection pipeline (`collector/pipeline.py`)

`<platform>_client.iter_*()` (httpx generator over paginated API) → `_parse_<platform>_comment()` (normalizes to `post_id`, `author_identifier`, `content`, `posted_at`) → `_ingest()` hashes the author with `security.anonymize.hash_identifier()` and inserts into `raw_posts`, skipping `(platform, post_id)` duplicates (also enforced by a unique constraint). Platforms are registered in the `_COLLECTORS` dict. `collect_many()` catches per-video exceptions so one bad video doesn't fail the batch.

To add a platform: write a client with `iter_*` and `extract_video_id`, add a `_parse_xxx_comment()`, register in `_COLLECTORS`, add it to the CLI `--platform` choices in `collector/__main__.py`, and to `_normalize_video_id()` in `api/main.py`.

### Invariants

- **Never store raw user identifiers.** Author IDs must pass through `hash_identifier()` (SHA-256 with `ANONYMIZATION_SALT`) before reaching the DB. This is a stated legal requirement of the project (Vietnamese Law 91/2025/QH15). Changing the salt makes new hashes inconsistent with existing rows.
- Video IDs are normalized server-side and in the CLI via each client's `extract_video_id()`, which tolerates full URLs and junk query params such as `?list=`.
- YouTube quota: `search.list` costs 100 units per call (once per enabled search query per scheduler tick), while `commentThreads.list` costs 1 unit. The free tier is 10,000 units/day. Keep this in mind when changing the poll interval or search behavior.
- TikTok: `_parse_tiktok_comment` falls back to `unknown:<video_id>` as the author because the public Research API docs show no comment-author field. Treat TikTok author hashes as unreliable until verified with real credentials. The token endpoint returns HTTP 200 even on bad credentials, so check for `access_token` in the body.
- `AnalysisResult` (`analysis_results`, FK to `raw_posts`) is the intended output table for the Phase 1 sentiment models. Nothing writes to it yet.

## Environment notes

The existing `.venv` is a Windows venv (`Lib/`, `Scripts/`). A venv cannot be shared between Windows and WSL — recreate it in whichever environment you run from. `collector/__main__.py` reconfigures stdout to UTF-8 so Vietnamese text prints correctly on the Windows console.
