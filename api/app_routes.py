"""Endpoint của webapp quản lý: đăng nhập, người dùng, nhật ký, dashboard, dữ liệu đã phân tích,
xu hướng, mô hình, điều khiển pipeline. Quyền truy cập khai báo ở api/security_mw.py (RULES)."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import aliased

from pipeline import DATA_DIR, ROOT
from security.auth import (ROLES, audit, create_token, hash_password, login_blocked, record_login_failure,
                           reset_login_failures, validate_password_strength, verify_password)
from storage.database import SessionLocal
from storage.models import AnalysisResult, AuditLog, CleanPost, ModelRun, PipelineRun, RawPost, Topic, TopicDaily, User

router = APIRouter()


def _user(request: Request) -> dict:
    return request.state.user or {}


def _ip(request: Request) -> str:
    return request.client.host if request.client else "?"


# ===================== Đăng nhập & tài khoản =====================

class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(body: LoginIn, request: Request):
    ip, name = _ip(request), body.username.strip().lower()
    if login_blocked(ip, name):
        audit(name, "login", "bị chặn tạm thời do sai nhiều lần", ip, success=False)
        raise HTTPException(429, "Sai mật khẩu quá nhiều lần - thử lại sau 10 phút")
    with SessionLocal() as s:
        user = s.scalars(select(User).where(User.username == name)).first()
        ok = bool(user and user.is_active and verify_password(body.password, user.password_hash))
    if not ok:
        record_login_failure(ip, name)
        audit(name, "login", "sai tên đăng nhập hoặc mật khẩu", ip, success=False)
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    reset_login_failures(ip, name)
    audit(name, "login", None, ip)
    return {"token": create_token(user.username, user.role), "user": {"username": user.username, "role": user.role}}


@router.get("/auth/me")
def me(request: Request):
    return _user(request)


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/auth/change-password")
def change_password(body: ChangePasswordIn, request: Request):
    u = _user(request)
    with SessionLocal() as s:
        user = s.scalars(select(User).where(User.username == u["username"])).first()
        if not verify_password(body.old_password, user.password_hash):
            raise HTTPException(400, "Mật khẩu cũ không đúng")
        try:
            validate_password_strength(body.new_password)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        user.password_hash = hash_password(body.new_password)
        s.commit()
    audit(u["username"], "change-password", None, _ip(request))
    return {"ok": True}


class UserIn(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


def _user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active, "created_at": u.created_at}


@router.get("/users")
def list_users():
    with SessionLocal() as s:
        return [_user_out(u) for u in s.scalars(select(User).order_by(User.id))]


@router.post("/users", status_code=201)
def create_user(body: UserIn):
    if not body.username or not body.password or body.role not in ROLES:
        raise HTTPException(400, "Cần tên đăng nhập, mật khẩu và vai trò hợp lệ")
    try:
        validate_password_strength(body.password)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    with SessionLocal() as s:
        name = body.username.strip().lower()
        if s.scalars(select(User).where(User.username == name)).first():
            raise HTTPException(409, "Tên đăng nhập đã tồn tại")
        u = User(username=name, password_hash=hash_password(body.password), role=body.role)
        s.add(u)
        s.commit()
        return _user_out(u)


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserIn, request: Request):
    with SessionLocal() as s:
        u = s.get(User, user_id)
        if not u:
            raise HTTPException(404, "Không tìm thấy tài khoản")
        if u.username == _user(request)["username"] and (body.is_active is False or (body.role and body.role != "admin")):
            raise HTTPException(400, "Không tự khóa hay tự hạ quyền tài khoản đang đăng nhập")
        if body.role:
            if body.role not in ROLES:
                raise HTTPException(400, "Vai trò không hợp lệ")
            u.role = body.role
        if body.is_active is not None:
            u.is_active = body.is_active
        if body.password:
            try:
                validate_password_strength(body.password)
            except ValueError as e:
                raise HTTPException(400, str(e)) from e
            u.password_hash = hash_password(body.password)
        s.commit()
        return _user_out(u)


@router.get("/audit")
def list_audit(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), username: str | None = None,
               action: str | None = None, failed_only: bool = False):
    with SessionLocal() as s:
        q = select(AuditLog)
        if username:
            q = q.where(AuditLog.username == username)
        if action:
            q = q.where(AuditLog.action.ilike(f"%{action}%"))
        if failed_only:
            q = q.where(AuditLog.success.is_(False))
        total = s.scalar(select(func.count()).select_from(q.subquery()))
        rows = s.scalars(q.order_by(AuditLog.at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"total": total, "items": [{"id": r.id, "at": r.at, "username": r.username, "action": r.action,
                                           "detail": r.detail, "ip": r.ip, "success": r.success} for r in rows]}


# ===================== Dashboard =====================

def _selected(s, task: str) -> ModelRun | None:
    return s.scalars(select(ModelRun).where(ModelRun.task == task, ModelRun.selected.is_(True))).first()


def _model_name(run: ModelRun | None) -> str:
    return f"{run.model_key}:{run.run_code}"[:64] if run else "-"


def _usable(q):
    return q.where(CleanPost.lang == "vi", CleanPost.is_spam.is_(False), CleanPost.is_duplicate.is_(False))


@router.get("/dashboard/summary")
def dashboard(days: int = Query(30, ge=1, le=365), category: str | None = None):
    with SessionLocal() as s:
        when = func.coalesce(RawPost.posted_at, RawPost.collected_at)
        since = datetime.utcnow() - timedelta(days=days)
        sel = {t: _selected(s, t) for t in ("sentiment", "emotion")}

        def scoped(q):
            q = q.where(when >= since)
            return q.where(RawPost.category == category) if category else q

        totals = {
            "raw": s.scalar(scoped(select(func.count()).select_from(RawPost))) or 0,
            "clean": s.scalar(scoped(select(func.count()).select_from(CleanPost).join(RawPost, RawPost.id == CleanPost.raw_post_id))) or 0,
            "usable": s.scalar(scoped(_usable(select(func.count()).select_from(CleanPost).join(RawPost, RawPost.id == CleanPost.raw_post_id)))) or 0,
        }
        dist, series = {}, {}
        for task, run in sel.items():
            base = (select(AnalysisResult.sentiment_label, func.count())
                    .join(RawPost, RawPost.id == AnalysisResult.raw_post_id)
                    .where(AnalysisResult.task == task, AnalysisResult.model_name == _model_name(run)))
            dist[task] = dict(s.execute(scoped(base).group_by(AnalysisResult.sentiment_label)).all())
            totals[f"analyzed_{task}"] = sum(dist[task].values())
            day = func.date_trunc("day", when)
            rows = s.execute(scoped(select(day, AnalysisResult.sentiment_label, func.count())
                                    .join(RawPost, RawPost.id == AnalysisResult.raw_post_id)
                                    .where(AnalysisResult.task == task, AnalysisResult.model_name == _model_name(run)))
                             .group_by(day, AnalysisResult.sentiment_label).order_by(day)).all()
            series[task] = [{"day": d.date().isoformat(), "label": lab, "count": c} for d, lab, c in rows]
        by_cat = s.execute(scoped(select(RawPost.category, AnalysisResult.sentiment_label, func.count())
                                  .join(RawPost, RawPost.id == AnalysisResult.raw_post_id)
                                  .where(AnalysisResult.task == "sentiment", AnalysisResult.model_name == _model_name(sel["sentiment"])))
                           .group_by(RawPost.category, AnalysisResult.sentiment_label)).all()
        monitor = s.scalars(select(PipelineRun).where(PipelineRun.step == "monitor", PipelineRun.status == "success")
                            .order_by(PipelineRun.id.desc())).first()
        categories = s.scalars(select(RawPost.category).where(RawPost.category.is_not(None)).distinct().order_by(RawPost.category)).all()
        return {
            "totals": totals, "distribution": dist, "series": series,
            "by_category": [{"category": c or "(không gắn)", "label": lab, "count": n} for c, lab, n in by_cat],
            "models": {t: ({"run_code": r.run_code, "model_name": r.model_name, "f1_macro": r.f1_macro} if r else None) for t, r in sel.items()},
            "monitor": {"at": monitor.finished_at, **json.loads(monitor.message or "{}")} if monitor else None,
            "categories": categories,
        }


# ===================== Dữ liệu đã phân tích =====================

@router.get("/analysis/posts")
def analysis_posts(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   q: str | None = None, category: str | None = None, platform: str | None = None,
                   sentiment: str | None = None, emotion: str | None = None, include_spam: bool = False):
    is_admin = _user(request).get("role") == "admin"
    with SessionLocal() as s:
        sel = {t: _model_name(_selected(s, t)) for t in ("sentiment", "emotion")}
        sa, ea = aliased(AnalysisResult), aliased(AnalysisResult)
        query = (select(RawPost, CleanPost, sa.sentiment_label, sa.sentiment_score, ea.sentiment_label, ea.sentiment_score)
                 .outerjoin(CleanPost, CleanPost.raw_post_id == RawPost.id)
                 .outerjoin(sa, and_(sa.raw_post_id == RawPost.id, sa.task == "sentiment", sa.model_name == sel["sentiment"]))
                 .outerjoin(ea, and_(ea.raw_post_id == RawPost.id, ea.task == "emotion", ea.model_name == sel["emotion"])))
        if q:
            query = query.where(or_(CleanPost.clean_text.ilike(f"%{q.lower()}%"), RawPost.content.ilike(f"%{q}%")))
        if category:
            query = query.where(RawPost.category == category)
        if platform:
            query = query.where(RawPost.platform == platform)
        if sentiment:
            query = query.where(sa.sentiment_label == sentiment)
        if emotion:
            query = query.where(ea.sentiment_label == emotion)
        if not include_spam:
            query = query.where(or_(CleanPost.raw_post_id.is_(None), and_(CleanPost.is_spam.is_(False), CleanPost.is_duplicate.is_(False))))
        total = s.scalar(select(func.count()).select_from(query.subquery()))
        rows = s.execute(query.order_by(RawPost.collected_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        items = []
        for raw, clean, sl, ss, el, es in rows:
            items.append({
                "id": raw.id, "platform": raw.platform, "category": raw.category, "author_hash": raw.author_hash[:12],
                "posted_at": raw.posted_at, "collected_at": raw.collected_at,
                # Phân tích viên chỉ thấy văn bản đã che SĐT/email (NV-09); nội dung gốc chỉ admin xem được
                "text": clean.clean_text if clean else None, "content": raw.content if is_admin else None,
                "lang": clean.lang if clean else None, "is_spam": clean.is_spam if clean else None,
                "sentiment": sl, "sentiment_score": ss, "emotion": el, "emotion_score": es,
            })
        return {"total": total, "items": items, "page": page, "page_size": page_size}


# ===================== Xu hướng =====================

@router.get("/topics/latest")
def latest_topics(category: str | None = None):
    with SessionLocal() as s:
        run = s.scalars(select(PipelineRun).where(PipelineRun.step == "trends", PipelineRun.status == "success")
                        .order_by(PipelineRun.id.desc())).first()
        if not run:
            return {"run": None, "topics": []}
        q = select(Topic).where(Topic.trend_run_id == run.id)
        if category:
            q = q.where(Topic.category == category)
        topics = s.scalars(q.order_by(Topic.size.desc())).all()
        daily = {}
        for d in s.scalars(select(TopicDaily).where(TopicDaily.topic_id.in_([t.id for t in topics])).order_by(TopicDaily.day)):
            daily.setdefault(d.topic_id, []).append({"day": d.day.date().isoformat(), "count": d.count, "positive": d.positive, "negative": d.negative})
        return {
            "run": {"id": run.id, "finished_at": run.finished_at, **json.loads(run.message or "{}")},
            "topics": [{"id": t.id, "category": t.category, "keywords": t.keywords, "size": t.size, "trend_label": t.trend_label,
                        "growth": t.growth, "sentiment_shift": t.sentiment_shift, "positive_share": t.positive_share,
                        "negative_share": t.negative_share, "neutral_share": t.neutral_share, "daily": daily.get(t.id, [])} for t in topics],
        }


# ===================== Mô hình =====================

def _run_out(r: ModelRun) -> dict:
    return {"id": r.id, "run_code": r.run_code, "task": r.task, "model_key": r.model_key, "model_name": r.model_name,
            "dataset": r.dataset, "dataset_version": r.dataset_version, "params": json.loads(r.params),
            "accuracy": r.accuracy, "f1_macro": r.f1_macro, "precision_macro": r.precision_macro, "recall_macro": r.recall_macro,
            "per_class": json.loads(r.per_class), "confusion": json.loads(r.confusion), "train_seconds": r.train_seconds,
            "selected": r.selected, "selected_by": r.selected_by, "created_at": r.created_at}


@router.get("/models/runs")
def model_runs(task: str | None = None):
    with SessionLocal() as s:
        q = select(ModelRun).order_by(ModelRun.task, ModelRun.f1_macro.desc())
        if task:
            q = q.where(ModelRun.task == task)
        return [_run_out(r) for r in s.scalars(q)]


@router.post("/models/{run_id}/select")
def select_model(run_id: int, request: Request):
    from models.sentiment.train import select_run
    with SessionLocal() as s:
        if not s.get(ModelRun, run_id):
            raise HTTPException(404, "Không tìm thấy lần huấn luyện")
        select_run(run_id, s, by=_user(request)["username"])
        return _run_out(s.get(ModelRun, run_id))


@router.get("/experiments")
def experiments():
    """Kết quả thực nghiệm bổ sung (data/experiments/*.json, do python -m experiments.<tên> tạo)."""
    out = []
    for f in sorted((DATA_DIR / "experiments").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.append({k: d.get(k) for k in ("name", "title", "question", "description", "tables", "findings", "created_at", "env")})
    return out


# ===================== Pipeline =====================

STEPS = {  # bước -> vai trò tối thiểu
    "collect": "analyst", "clean": "analyst", "predict": "analyst", "trends": "analyst", "monitor": "analyst", "run": "analyst",
    "datasets": "admin", "train": "admin",
}
_procs: dict[str, subprocess.Popen] = {}
_lock = threading.Lock()


class RunIn(BaseModel):
    step: str
    task: str | None = None
    model: str | None = None
    epochs: int | None = None


@router.get("/pipeline/runs")
def pipeline_runs(page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100), step: str | None = None):
    with SessionLocal() as s:
        q = select(PipelineRun)
        if step:
            q = q.where(PipelineRun.step.like(f"{step}%"))
        total = s.scalar(select(func.count()).select_from(q.subquery()))
        rows = s.scalars(q.order_by(PipelineRun.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"total": total, "running": sorted(k for k, p in _procs.items() if p.poll() is None),
                "items": [{"id": r.id, "step": r.step, "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at,
                           "records_in": r.records_in, "records_out": r.records_out, "triggered_by": r.triggered_by,
                           "info": json.loads(r.message) if r.message and r.message.startswith("{") else r.message} for r in rows]}


@router.post("/pipeline/run", status_code=202)
def run_step(body: RunIn, request: Request):
    """Chạy một bước pipeline trong tiến trình riêng. Chỉ chạy các lệnh cố định của `python -m pipeline`."""
    from security.auth import role_at_least

    user = _user(request)
    if body.step not in STEPS:
        raise HTTPException(400, "Bước không hợp lệ")
    if not role_at_least(user["role"], STEPS[body.step]):
        raise HTTPException(403, "Bước này chỉ quản trị được chạy")
    args = [sys.executable, "-m", "pipeline", body.step, "--by", user["username"]]
    key = body.step
    if body.step == "train":
        if body.task not in ("sentiment", "emotion") or body.model not in ("tfidf-lr", "tfidf-svm", "bilstm", "visobert", "phobert"):
            raise HTTPException(400, "Cần task (sentiment/emotion) và model (tfidf-lr/tfidf-svm/bilstm/visobert/phobert)")
        args += ["--task", body.task, "--model", body.model, "--epochs", str(max(1, min(body.epochs or 4, 10)))]
        key = "train"  # một lần huấn luyện tại một thời điểm (GPU 4GB)
    with _lock:
        p = _procs.get(key)
        if p and p.poll() is None:
            raise HTTPException(409, f"Bước {key} đang chạy")
        logs = DATA_DIR / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        log = open(logs / f"{datetime.now():%Y%m%d-%H%M%S}-{body.step}.log", "w", encoding="utf-8")  # noqa: SIM115
        _procs[key] = subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    return {"started": body.step, "args": args[3:]}
