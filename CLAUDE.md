# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Research prototype for a Vietnamese master's/NCKH project: collect public social-media comments (YouTube, TikTok), store them anonymized in PostgreSQL, and later classify sentiment/emotion and detect trends. Work is organized in phases ("Giai đoạn"):

- **Done:** config, DB/ORM, anonymization, collectors (YouTube working; TikTok **never tested with real keys**), scheduler (runs inside the API, toggled from the UI).
- **Done:** a full pipeline (`pipeline/`): preprocessing, datasets (UIT-VSFC, UIT-VSMEC), training of TF-IDF and ViSoBERT models, prediction, trends and monitoring. Also the management webapp, with login, RBAC and an audit log.
- **Not yet:** real collected data (needs `YOUTUBE_API_KEY` in `.env`), labeled gold data from collected posts, differential privacy experiments (QD-06), BERTopic.

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
cp .env.example .env          # set POSTGRES_PASSWORD, ANONYMIZATION_SALT, JWT_SECRET, YOUTUBE_API_KEY
make up                       # Postgres 16 + Adminer (http://localhost:8080, server name "db")
make migrate                  # python -m storage.migrate: create_all + idempotent ALTERs (run after pulling)
make api                      # uvicorn api.main:app --reload on :8000 (GET /health is the only public route)
make frontend-install         # npm install --prefix frontend
make frontend                 # Vite dev server on :5500 (strictPort)
make down
python -m security.users add <name> --role admin   # first account; then manage users in the webapp

# Pipeline (each run is logged to pipeline_runs)
python -m pipeline datasets                                   # download + clean UIT-VSFC / UIT-VSMEC into data/datasets/
python -m pipeline train --task sentiment|emotion --model tfidf-lr|tfidf-svm|bilstm|visobert|phobert [--epochs 4]
python -m experiments.<poisoning|topics_eval|dp|robustness|llm|perf>   # writes data/experiments/<name>.json, shown in webapp
python -m storage.backup                                      # pg_dump -> data/backups/
python -m pipeline collect|clean|predict|trends|monitor       # or: python -m pipeline run  (all five)
python -m pipeline select --task sentiment --run-code <code>  # pin a model manually
python -m unittest preprocessing.test_text                    # the only test suite

# One-off collection via CLI (accepts bare IDs or full URLs)
python -m collector run --platform youtube --video <id_or_url> [--video ...] [--max-pages N]
python -m collector search --query "giá vàng" --max-videos 5 --days 7

# Frontend checks (in frontend/)
npm run lint                  # oxlint
npm run build                 # tsc -b && vite build (type-check)
```

Schema changes to existing tables go in `storage/migrate.py` `UPGRADES` (idempotent SQL), because `init_db()` only creates missing tables.

## Architecture

All components share one PostgreSQL database:

1. **API** (`api/main.py`, FastAPI). Lâm's original endpoints (`/stats`, `/posts`, collector config, `/scheduler`) live there. Webapp endpoints live in `api/app_routes.py`: auth, users, audit, dashboard, `/analysis/posts`, topics, model runs, and pipeline triggers.
   - **Every route is protected by `api/security_mw.py`.** `RULES` maps method plus path regex to a minimum role (viewer < analyst < admin). Unmatched routes are admin-only, so declare the role there when you add an endpoint.
   - The middleware also writes `audit_logs` for every non-GET request and for GETs that view data.
   - Analysts get only `clean_posts.clean_text` (PII masked); raw `content` is returned only to admins.
2. **Scheduler** (`collector/scheduler.py`) runs inside the API process as a `BackgroundScheduler`, toggled from the UI and persisted in `scheduler_state`. There is also a CLI `BlockingScheduler`; don't run both at once. Each tick re-reads config from the DB.
3. **Pipeline** (`python -m pipeline`). Each step is wrapped in `pipeline.runlog.pipeline_run`, which records a `pipeline_runs` row.
   - The webapp triggers steps as subprocesses (`/pipeline/run`). The allowed steps are listed in `STEPS`; `train` and `datasets` are admin-only.
4. **Frontend** (`frontend/`, React 19 + antd 5 + recharts + Vite).
   - Page components (`Dashboard`, `Trends`, `AnalysisPosts`, `Models`, `Pipeline`, `Admin`) are role-filtered in `App.tsx`.
   - The JWT is stored in sessionStorage. A 401 dispatches the `sss-logout` event.
   - The frontend mirrors response shapes by hand in `src/api.ts`.
   - In dev, Vite proxies `/api/*` to `localhost:8000`.

### ML pipeline

- **Preprocessing.** `preprocessing/text.py:clean_text` (NFC, PII masking, URL removal, tone normalization, repeated-character collapse, teencode, spam and language flags) is applied identically to training datasets and collected posts. Changing it bumps `PIPELINE_VERSION`. It has tests in `preprocessing/test_text.py`, including real words such as "cứu/rượu" that must survive.
- **Training.** `models/sentiment/train.py` writes artifacts to `data/models/<run_code>/` and a row to `model_runs`.
- **Model selection.** The selected model per task is the highest F1-macro, chosen automatically (`selected_by='auto'`) unless someone pins one manually.
- **Labels are Vietnamese strings.** Sentiment: Tích cực / Trung tính / Tiêu cực. Emotion: Vui vẻ / Buồn bã / Tức giận / Ghê tởm / Sợ hãi / Ngạc nhiên / Khác.
- **Input meta per artifact.** Transformer artifacts carry `pipeline_meta.json` (`tokenizer`: `spm` or `hf`, `word_segment`, `max_len`); the predictor reads it. PhoBERT input must be word-segmented with underthesea (`train.word_segment`). BiLSTM artifacts are `bilstm.pt` + `bilstm.json`.
- **Experiments.** `experiments/*.py` each write `{title, question, description, tables, findings}` through `experiments.save_result`, and the webapp renders them generically. DP and topic experiments use frozen *pretrained* ViSoBERT embeddings (`experiments/embed.py`, cached under `data/experiments/cache/`), never fine-tuned ones, so the DP guarantee stays meaningful.
- **ViSoBERT tokenizer gotcha.** `uitnlp/visobert` has no tokenizer config, and transformers 5.x builds an all-`<unk>` XLMRobertaTokenizer from it. Use `models/sentiment/spm_tokenizer.SpmXlmrTokenizer` (sentencepiece id + 1, `<s>`=0, `<pad>`=1, `</s>`=2, `<unk>`=3). Training aborts if the `<unk>` ratio exceeds 20%.
- **Prediction.** `analysis_results` holds one row per (post, task, model_name). `task` is `sentiment` or `emotion`, and `sentiment_label`/`sentiment_score` hold the label of either task.
- **Trends.** `models/trend/trends.py` uses TF-IDF + NMF per category, plus a rule-based trend label (last 3 days vs. the previous ≤7). Results go to `topics` / `topic_daily`. Trends are community-level only (QD-05): never aggregate by `author_hash`.

### Collection pipeline (`collector/pipeline.py`)

`<platform>_client.iter_*()` (httpx generator over paginated API) → `_parse_<platform>_comment()` (normalizes to `post_id`, `author_identifier`, `content`, `posted_at`) → `_ingest()` hashes the author with `security.anonymize.hash_identifier()` and inserts into `raw_posts`, skipping `(platform, post_id)` duplicates (also enforced by a unique constraint). Platforms are registered in the `_COLLECTORS` dict. `collect_many()` catches per-video exceptions so one bad video doesn't fail the batch.

To add a platform: write a client with `iter_*` and `extract_video_id`, add a `_parse_xxx_comment()`, register in `_COLLECTORS`, add it to the CLI `--platform` choices in `collector/__main__.py`, and to `_normalize_video_id()` in `api/main.py`.

### Invariants

- **Never store raw user identifiers.** Author IDs must pass through `hash_identifier()` (SHA-256 with `ANONYMIZATION_SALT`) before reaching the DB. This is a stated legal requirement of the project (Vietnamese Law 91/2025/QH15). Changing the salt makes new hashes inconsistent with existing rows.
- Video IDs are normalized server-side and in the CLI via each client's `extract_video_id()`, which tolerates full URLs and junk query params such as `?list=`.
- YouTube quota: `search.list` costs 100 units per call (once per enabled search query per scheduler tick), while `commentThreads.list` costs 1 unit. The free tier is 10,000 units/day. Keep this in mind when changing the poll interval or search behavior.
- TikTok: `_parse_tiktok_comment` falls back to `unknown:<video_id>` as the author because the public Research API docs show no comment-author field. Treat TikTok author hashes as unreliable until verified with real credentials. The token endpoint returns HTTP 200 even on bad credentials, so check for `access_token` in the body.
## Environment notes

- **venv.** The existing `.venv` is a Windows venv (`Lib/`, `Scripts/`) with Python 3.14 and torch 2.14.1+cu126 (GTX 1050 Ti, 4 GB, sm_61). Use the cu126 wheels: newer CUDA builds dropped Pascal GPUs. A venv cannot be shared between Windows and WSL.
- **UTF-8 output.** Set `PYTHONIOENCODING=utf-8` (or rely on `pipeline/__main__.py`, which reconfigures stdout) so Vietnamese prints correctly on the Windows console.
- **Data.** `data/datasets/`, `data/models/` and `data/logs/` are git-ignored and can be regenerated with `python -m pipeline datasets` / `train`.
