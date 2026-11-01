"""Các bước pipeline chạy trên dữ liệu thu thập (PL-01, PL-02, PL-07, PL-08). Mỗi bước ghi pipeline_runs."""
from __future__ import annotations

import hashlib
import json
import logging
import math
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select

from config.settings import settings
from pipeline import DATASETS_DIR
from pipeline.runlog import pipeline_run
from preprocessing.text import PIPELINE_VERSION, clean_text, extract_hashtags
from security.detect import ALERT_PREFIX, detect, load_events
from storage.database import SessionLocal
from storage.models import AnalysisResult, CleanPost, ModelRun, PipelineRun, RawPost, Topic, TopicDaily

logger = logging.getLogger(__name__)
BATCH = 1000


def step_collect(by: str = "cli") -> None:
    """PL-01: chạy 1 lượt thu thập theo cấu hình trên giao diện (code thu thập của collector/)."""
    with pipeline_run("collect", by) as run:
        if not settings.youtube_api_key and not settings.tiktok_client_key:
            run.status = "skipped"
            run.info["reason"] = "Chưa có YOUTUBE_API_KEY / TIKTOK_CLIENT_KEY trong .env"
            return
        from collector.scheduler import run_once
        with SessionLocal() as s:
            before = s.scalar(select(func.count()).select_from(RawPost)) or 0
        run_once()
        with SessionLocal() as s:
            after = s.scalar(select(func.count()).select_from(RawPost)) or 0
        run.records_out = after - before
        run.info["total_posts"] = after


def step_clean(by: str = "cli") -> None:
    """PL-02: làm sạch bài mới (chưa có trong clean_posts); đánh dấu ngôn ngữ, spam, trùng lặp."""
    with pipeline_run("clean", by) as run, SessionLocal() as s:
        # trùng lặp = cùng tác giả (đã băm) đăng cùng nội dung đã làm sạch
        seen = {
            hashlib.sha1(f"{a}|{t}".encode()).hexdigest()
            for a, t in s.execute(select(RawPost.author_hash, CleanPost.clean_text).join(CleanPost, CleanPost.raw_post_id == RawPost.id))
        }
        stats = Counter()
        while True:
            rows = s.execute(
                select(RawPost.id, RawPost.author_hash, RawPost.content)
                .outerjoin(CleanPost, CleanPost.raw_post_id == RawPost.id)
                .where(CleanPost.raw_post_id.is_(None)).order_by(RawPost.id).limit(BATCH)
            ).all()
            if not rows:
                break
            for rid, author, content in rows:
                r = clean_text(content)
                key = hashlib.sha1(f"{author}|{r.text}".encode()).hexdigest()
                dup = key in seen
                seen.add(key)
                tags = extract_hashtags(content)
                stats["with_hashtags"] += bool(tags)
                s.add(CleanPost(raw_post_id=rid, clean_text=r.text, lang=r.lang, is_spam=r.is_spam, is_duplicate=dup,
                                pii_masked=r.pii_masked, hashtags=",".join(tags) or None, pipeline_version=PIPELINE_VERSION))
                stats["spam"] += r.is_spam
                stats["duplicate"] += dup
                stats["pii_masked"] += r.pii_masked
                stats[f"lang_{r.lang}"] += 1
            s.commit()
            run.records_in += len(rows)
        run.records_out = run.records_in - stats["spam"] - stats["duplicate"]
        run.info.update(stats)


def _usable(q):
    return q.where(CleanPost.lang == "vi", CleanPost.is_spam.is_(False), CleanPost.is_duplicate.is_(False))


def step_predict(by: str = "cli") -> None:
    """PL-07: gán nhãn quan điểm (BT-01) và cảm xúc (BT-03) bằng mô hình đang được chọn."""
    from models.sentiment.predict import load_selected

    with pipeline_run("predict", by) as run:
        for task in ("sentiment", "emotion"):
            pred = load_selected(task)
            if pred is None:
                run.info[task] = "chưa có mô hình được chọn - chạy: python -m pipeline train"
                continue
            done = 0
            with SessionLocal() as s:
                while True:
                    rows = s.execute(_usable(
                        select(CleanPost.raw_post_id, CleanPost.clean_text)
                        .outerjoin(AnalysisResult, and_(AnalysisResult.raw_post_id == CleanPost.raw_post_id,
                                                        AnalysisResult.task == task, AnalysisResult.model_name == pred.name))
                        .where(AnalysisResult.id.is_(None))
                    ).limit(512)).all()
                    if not rows:
                        break
                    for (rid, _), (label, score) in zip(rows, pred.predict([t for _, t in rows])):
                        s.add(AnalysisResult(raw_post_id=rid, task=task, sentiment_label=label, sentiment_score=score, model_name=pred.name))
                    s.commit()
                    done += len(rows)
            run.records_out += done
            run.info[task] = {"model": pred.run_code, "labeled": done}


def _selected_model_name(s, task: str) -> str | None:
    run = s.scalars(select(ModelRun).where(ModelRun.task == task, ModelRun.selected.is_(True))).first()
    return f"{run.model_key}:{run.run_code}"[:64] if run else None


def step_trends(by: str = "cli", days: int = 60) -> None:
    """PL-07: phát hiện chủ đề và phân loại xu hướng trên dữ liệu `days` ngày gần nhất."""
    from models.trend.trends import analyze, hashtag_trends

    with pipeline_run("trends", by) as run, SessionLocal() as s:
        since = datetime.utcnow() - timedelta(days=days)
        sent_model = _selected_model_name(s, "sentiment")
        when = func.coalesce(RawPost.posted_at, RawPost.collected_at)
        tag_rows = s.execute(_usable(select(CleanPost.hashtags, when, RawPost.category).join(RawPost, RawPost.id == CleanPost.raw_post_id)
                                     .where(when >= since, CleanPost.hashtags.is_not(None)))).all()
        run.info["hashtags"] = hashtag_trends([(h.split(","), d.date(), c) for h, d, c in tag_rows])
        q = _usable(
            select(CleanPost.clean_text, when, RawPost.category, AnalysisResult.sentiment_label)
            .join(RawPost, RawPost.id == CleanPost.raw_post_id)
            .outerjoin(AnalysisResult, and_(AnalysisResult.raw_post_id == CleanPost.raw_post_id,
                                            AnalysisResult.task == "sentiment", AnalysisResult.model_name == (sent_model or "")))
            .where(when >= since)
        )
        posts = [{"text": t, "day": d.date(), "category": c, "sentiment": lab} for t, d, c, lab in s.execute(q)]
        run.records_in = len(posts)
        topics = analyze(posts)
        for t in topics:
            row = Topic(trend_run_id=run.id, **{k: v for k, v in t.items() if k != "daily"})
            s.add(row)
            s.flush()
            for d in t["daily"]:
                s.add(TopicDaily(topic_id=row.id, day=datetime.combine(d["day"], datetime.min.time()),
                                 count=d["count"], positive=d["positive"], negative=d["negative"]))
        s.commit()
        run.records_out = len(topics)
        run.info["trend_labels"] = dict(Counter(t["trend_label"] for t in topics))
        if not topics:
            run.info["note"] = f"Chưa có nhóm nào đủ {20} bài trong {days} ngày gần nhất"


def _js_distance(p: dict, q: dict) -> float:
    keys = set(p) | set(q)
    sp, sq = sum(p.values()) or 1, sum(q.values()) or 1
    P = {k: p.get(k, 0) / sp for k in keys}
    Q = {k: q.get(k, 0) / sq for k in keys}
    M = {k: (P[k] + Q[k]) / 2 for k in keys}
    kl = lambda a: sum(a[k] * math.log2(a[k] / M[k]) for k in keys if a[k] > 0)  # noqa: E731
    return math.sqrt(max(0.0, (kl(P) + kl(Q)) / 2))


def step_monitor(by: str = "cli") -> None:
    """PL-08: số liệu sức khỏe dữ liệu + trôi phân phối nhãn so với dữ liệu huấn luyện + lượt chạy lỗi."""
    with pipeline_run("monitor", by) as run, SessionLocal() as s:
        now = datetime.utcnow()
        week = now - timedelta(days=7)
        info, alerts = {}, []
        info["posts_24h"] = s.scalar(select(func.count()).select_from(RawPost).where(RawPost.collected_at >= now - timedelta(days=1))) or 0
        info["posts_7d"] = s.scalar(select(func.count()).select_from(RawPost).where(RawPost.collected_at >= week)) or 0
        cleaned = s.execute(select(CleanPost.lang, CleanPost.is_spam, CleanPost.is_duplicate).where(CleanPost.processed_at >= week)).all()
        if cleaned:
            info["spam_ratio_7d"] = round(sum(c.is_spam for c in cleaned) / len(cleaned), 4)
            info["non_vi_ratio_7d"] = round(sum(c.lang != "vi" for c in cleaned) / len(cleaned), 4)
            if info["spam_ratio_7d"] > 0.3:
                alerts.append(f"Tỉ lệ spam 7 ngày cao: {info['spam_ratio_7d']:.0%}")
        for task, ds in (("sentiment", "vsfc"), ("emotion", "vsmec")):
            name = _selected_model_name(s, task)
            if not name:
                continue
            rows = s.execute(select(AnalysisResult.sentiment_label, AnalysisResult.sentiment_score)
                             .where(AnalysisResult.task == task, AnalysisResult.model_name == name, AnalysisResult.analyzed_at >= week)).all()
            if not rows:
                continue
            pred_dist = Counter(r[0] for r in rows)
            meta = json.loads((DATASETS_DIR / ds / "meta.json").read_text(encoding="utf-8"))
            train_dist = meta["splits"]["train"]["labels"]
            jsd = round(_js_distance(pred_dist, train_dist), 4)
            low_conf = round(sum(r[1] < 0.5 for r in rows) / len(rows), 4)
            info[task] = {"predicted_7d": dict(pred_dist), "train_distribution": train_dist, "js_distance": jsd, "low_confidence_ratio": low_conf}
            if jsd > 0.3:
                alerts.append(f"{task}: phân phối nhãn dự đoán lệch xa dữ liệu huấn luyện (JS={jsd}) - có thể trôi miền dữ liệu")
            if low_conf > 0.4:
                alerts.append(f"{task}: {low_conf:.0%} dự đoán có độ tin cậy < 0.5")
        failed = s.scalar(select(func.count()).select_from(PipelineRun).where(PipelineRun.status == "failed", PipelineRun.started_at >= week)) or 0
        info["failed_runs_7d"] = failed
        if failed:
            alerts.append(f"{failed} lượt chạy pipeline lỗi trong 7 ngày")
        sec = detect(load_events(s, now - timedelta(days=1)))
        info["security_alerts_24h"] = [{"kind": a.kind, "key": a.key, "at": a.first_at.isoformat(timespec="seconds"), "count": a.count} for a in sec]
        alerts += [f"{ALERT_PREFIX}{a.message} (lúc {a.first_at:%Y-%m-%d %H:%M})" for a in sec]
        info["alerts"] = alerts
        run.info.update(info)
        run.records_in = info["posts_7d"]
        run.records_out = len(alerts)
