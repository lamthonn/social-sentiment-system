"""Huấn luyện + đánh giá mô hình cảm xúc (bước PL-05, PL-06).

Bài toán (task):
  sentiment - quan điểm 3 lớp (BT-01) trên UIT-VSFC
  emotion   - cảm xúc 7 nhãn (BT-03) trên UIT-VSMEC
Mô hình (model_key):
  tfidf-lr, tfidf-svm  - baseline cổ điển (M-01, M-02)
  visobert             - Transformer cho văn bản MXH tiếng Việt (M-10), fine-tune trên GPU nếu có

Mỗi lần chạy lưu artifact vào data/models/<run_code>/ và một dòng vào bảng model_runs.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sqlalchemy import select, update

from pipeline import DATASETS_DIR, MODELS_DIR
from preprocessing.text import emoji_tags
from storage.database import SessionLocal
from storage.models import ModelRun

logger = logging.getLogger(__name__)

TASKS = {
    "sentiment": {"dataset": "vsfc", "title": "Quan điểm 3 lớp (UIT-VSFC)"},
    "emotion": {"dataset": "vsmec", "title": "Cảm xúc 7 nhãn (UIT-VSMEC)"},
}
MODEL_NAMES = {
    "tfidf-lr": "TF-IDF + Logistic Regression",
    "tfidf-svm": "TF-IDF + Linear SVM",
    "bilstm": "BiLSTM",
    "visobert": "ViSoBERT (uitnlp/visobert)",
    "phobert": "PhoBERT-base-v2 (vinai/phobert-base-v2)",
}
HF_MODELS = {"visobert": "uitnlp/visobert", "phobert": "vinai/phobert-base-v2"}
# cách đưa văn bản vào mô hình - lưu kèm artifact (pipeline_meta.json) để dự đoán xử lý giống lúc huấn luyện
INPUT_META = {
    "visobert": {"tokenizer": "spm", "word_segment": False},  # ViSoBERT: sentencepiece, không cần tách từ
    "phobert": {"tokenizer": "hf", "word_segment": True},     # PhoBERT bắt buộc tách từ (underthesea)
}


def word_segment(texts) -> list[str]:
    from underthesea import word_tokenize
    return [word_tokenize(t, format="text") for t in texts]


def make_tokenizer(kind: str, name_or_dir):
    if INPUT_META[kind]["tokenizer"] == "spm":
        from models.sentiment.spm_tokenizer import SpmXlmrTokenizer
        return SpmXlmrTokenizer.from_pretrained(name_or_dir)
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(name_or_dir)


def load_split(task: str, split: str) -> pd.DataFrame:
    path = DATASETS_DIR / TASKS[task]["dataset"] / f"{split}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Chưa có {path} - chạy trước: python -m pipeline datasets")
    return pd.read_parquet(path)


def dataset_version(task: str) -> str:
    meta = DATASETS_DIR / TASKS[task]["dataset"] / "meta.json"
    return json.loads(meta.read_text(encoding="utf-8"))["version"] if meta.exists() else "unknown"


def evaluate(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    pm, rm, fm, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(fm), "precision_macro": float(pm), "recall_macro": float(rm),
        "per_class": {lab: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])} for i, lab in enumerate(labels)},
        "confusion": {"labels": labels, "matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist()},
    }


def _features(texts) -> list[str]:
    return [emoji_tags(t) for t in texts]


# ===================== Baseline TF-IDF =====================

def _baseline_pipeline(kind: str, c: float):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.svm import LinearSVC

    feats = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=200_000)),
    ])
    clf = (LogisticRegression(C=c, max_iter=3000, class_weight="balanced") if kind == "tfidf-lr"
           else LinearSVC(C=c, class_weight="balanced"))
    return Pipeline([("tfidf", feats), ("clf", clf)])


def train_baseline(task: str, kind: str) -> dict:
    train, val, test = (load_split(task, s) for s in ("train", "validation", "test"))
    labels = sorted(train["label"].unique().tolist())
    t0 = time.time()
    best = None
    for c in (0.25, 0.5, 1.0, 2.0, 4.0):  # chọn C theo F1-macro trên tập validation
        model = _baseline_pipeline(kind, c).fit(_features(train["clean_text"]), train["label"])
        f1 = evaluate(val["label"].tolist(), model.predict(_features(val["clean_text"])).tolist(), labels)["f1_macro"]
        logger.info("[%s/%s] C=%s val F1-macro=%.4f", task, kind, c, f1)
        if best is None or f1 > best[0]:
            best = (f1, c, model)
    val_f1, c, model = best
    # huấn luyện lại trên train+validation với C tốt nhất rồi đánh giá trên test
    full = pd.concat([train, val])
    model = _baseline_pipeline(kind, c).fit(_features(full["clean_text"]), full["label"])
    metrics = evaluate(test["label"].tolist(), model.predict(_features(test["clean_text"])).tolist(), labels)
    seconds = time.time() - t0

    import joblib
    run_code, out = _new_run_dir(task, kind)
    joblib.dump(model, out / "model.joblib")
    params = {"C": c, "val_f1_macro": round(val_f1, 4), "features": "word 1-2gram + char_wb 2-5gram TF-IDF, emoji->từ",
              "class_weight": "balanced", "train_size": len(full), "test_size": len(test)}
    return _record(task, kind, run_code, out, params, metrics, seconds)


# ===================== Transformer (ViSoBERT) =====================

def train_transformer(task: str, kind: str = "visobert", epochs: int = 4, batch_size: int = 16,
                      max_len: int = 128, lr: float = 2e-5, seed: int = 42) -> dict:
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, get_linear_schedule_with_warmup

    torch.manual_seed(seed)
    np.random.seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train, val, test = (load_split(task, s) for s in ("train", "validation", "test"))
    if INPUT_META[kind]["word_segment"]:
        for df in (train, val, test):
            df["clean_text"] = word_segment(df["clean_text"])
    labels = sorted(train["label"].unique().tolist())
    lab2id = {lab: i for i, lab in enumerate(labels)}
    hf_name = HF_MODELS[kind]
    tok = make_tokenizer(kind, hf_name)
    sample = tok(train["clean_text"].head(200).tolist(), truncation=True, max_length=max_len, padding=True, return_tensors="pt")["input_ids"]
    unk_id = getattr(tok, "unk_token_id", 3)
    unk_ratio = float((sample == unk_id).sum() / (sample > 2).sum())
    if unk_ratio > 0.2:  # chặn trường hợp tokenizer hỏng âm thầm (toàn <unk>)
        raise RuntimeError(f"Tokenizer cho ra {unk_ratio:.0%} <unk> - kiểm tra lại file sentencepiece")
    model = AutoModelForSequenceClassification.from_pretrained(
        hf_name, num_labels=len(labels), id2label=dict(enumerate(labels)), label2id=lab2id).to(device)

    def batches(df: pd.DataFrame, shuffle: bool):
        items = list(zip(df["clean_text"].tolist(), df["label"].map(lab2id).tolist()))

        def collate(b):
            enc = tok([x for x, _ in b], truncation=True, max_length=max_len, padding=True, return_tensors="pt")
            enc["labels"] = torch.tensor([y for _, y in b])
            return enc
        return DataLoader(items, batch_size=batch_size, shuffle=shuffle, collate_fn=collate)

    def predict(df: pd.DataFrame) -> list[str]:
        model.eval()
        out = []
        with torch.no_grad():
            for b in batches(df, False):
                b = {k: v.to(device) for k, v in b.items() if k != "labels"}
                out += model(**b).logits.argmax(-1).tolist()
        return [labels[i] for i in out]

    loader = batches(train, True)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total = len(loader) * epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * total), total)
    run_code, out = _new_run_dir(task, kind)
    t0 = time.time()
    best_f1, best_epoch, history = -1.0, 0, []
    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for step, b in enumerate(loader, 1):
            b = {k: v.to(device) for k, v in b.items()}
            loss = model(**b).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            losses.append(loss.item())
            if step % 100 == 0:
                logger.info("[%s/%s] epoch %d step %d/%d loss %.4f", task, kind, epoch, step, len(loader), np.mean(losses[-100:]))
        val_f1 = evaluate(val["label"].tolist(), predict(val), labels)["f1_macro"]
        history.append({"epoch": epoch, "loss": round(float(np.mean(losses)), 4), "val_f1_macro": round(val_f1, 4)})
        logger.info("[%s/%s] epoch %d: loss %.4f, val F1-macro %.4f", task, kind, epoch, np.mean(losses), val_f1)
        if val_f1 > best_f1:  # giữ checkpoint tốt nhất theo validation (early stopping đơn giản)
            best_f1, best_epoch = val_f1, epoch
            model.save_pretrained(out)
            tok.save_pretrained(out)
            (out / "pipeline_meta.json").write_text(json.dumps({**INPUT_META[kind], "max_len": max_len}), encoding="utf-8")
    model = AutoModelForSequenceClassification.from_pretrained(out).to(device)
    metrics = evaluate(test["label"].tolist(), predict(test), labels)
    seconds = time.time() - t0
    tok_desc = "sentencepiece (XLM-R ids)" if INPUT_META[kind]["tokenizer"] == "spm" else "BPE của mô hình, đầu vào tách từ bằng underthesea"
    params = {"base_model": hf_name, "tokenizer": tok_desc, "unk_ratio": round(unk_ratio, 4),
              "epochs": epochs, "best_epoch": best_epoch, "batch_size": batch_size,
              "max_len": max_len, "lr": lr, "warmup": "10% linear", "seed": seed, "device": device,
              "gpu": torch.cuda.get_device_name(0) if device == "cuda" else "", "history": history,
              "train_size": len(train), "test_size": len(test)}
    return _record(task, kind, run_code, out, params, metrics, seconds)


# ===================== BiLSTM =====================

def train_bilstm(task: str, epochs: int = 10, batch_size: int = 64, max_len: int = 128, lr: float = 1e-3, seed: int = 42) -> dict:
    import torch

    from models.sentiment import bilstm as B

    torch.manual_seed(seed)
    np.random.seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train, val, test = (load_split(task, s) for s in ("train", "validation", "test"))
    labels = sorted(train["label"].unique().tolist())
    lab2id = {lab: i for i, lab in enumerate(labels)}
    vocab = B.Vocab.build(train["clean_text"])
    cfg = {"emb": 200, "hidden": 128, "dropout": 0.3, "max_len": max_len}
    model = B.BiLSTMClassifier(len(vocab.itos), len(labels), cfg["emb"], cfg["hidden"], cfg["dropout"]).to(device)
    # trọng số lớp nghịch với tần suất (dữ liệu lệch lớp mạnh, VD Trung tính chỉ 4% của VSFC)
    freq = train["label"].map(lab2id).value_counts().reindex(range(len(labels)), fill_value=1).to_numpy()
    weight = torch.tensor(len(train) / (len(labels) * freq), dtype=torch.float, device=device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weight)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    x_train = [vocab.encode(t, max_len) for t in train["clean_text"]]
    y_train = train["label"].map(lab2id).tolist()

    def predict(df):
        model.eval()
        out = []
        with torch.no_grad():
            seqs = [vocab.encode(t, max_len) for t in df["clean_text"]]
            for i in range(0, len(seqs), 256):
                out += model(B.pad_batch(seqs[i:i + 256]).to(device)).argmax(-1).tolist()
        return [labels[i] for i in out]

    run_code, out = _new_run_dir(task, "bilstm")
    t0 = time.time()
    best_f1, best_epoch, history = -1.0, 0, []
    for epoch in range(1, epochs + 1):
        model.train()
        order = np.random.permutation(len(x_train))
        losses = []
        for i in range(0, len(order), batch_size):
            idx = order[i:i + batch_size]
            xb = B.pad_batch([x_train[j] for j in idx]).to(device)
            yb = torch.tensor([y_train[j] for j in idx], device=device)
            loss = loss_fn(model(xb), yb)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            losses.append(loss.item())
        val_f1 = evaluate(val["label"].tolist(), predict(val), labels)["f1_macro"]
        history.append({"epoch": epoch, "loss": round(float(np.mean(losses)), 4), "val_f1_macro": round(val_f1, 4)})
        logger.info("[%s/bilstm] epoch %d: loss %.4f, val F1-macro %.4f", task, epoch, np.mean(losses), val_f1)
        if val_f1 > best_f1:
            best_f1, best_epoch = val_f1, epoch
            B.save(model, vocab, labels, cfg, out)
    model, vocab, labels, _ = B.load(out, device)
    metrics = evaluate(test["label"].tolist(), predict(test), labels)
    seconds = time.time() - t0
    params = {**cfg, "vocab_size": len(vocab.itos), "epochs": epochs, "best_epoch": best_epoch, "batch_size": batch_size, "lr": lr,
              "class_weight": "nghịch tần suất", "embedding": "học từ đầu", "seed": seed, "device": device, "history": history,
              "train_size": len(train), "test_size": len(test)}
    return _record(task, "bilstm", run_code, out, params, metrics, seconds)


# ===================== Lưu kết quả =====================

def _new_run_dir(task: str, kind: str) -> tuple[str, Path]:
    run_code = f"{datetime.now():%Y%m%d-%H%M%S}-{task}-{kind}"
    out = MODELS_DIR / run_code
    out.mkdir(parents=True, exist_ok=True)
    return run_code, out


def _record(task, kind, run_code, out, params, metrics, seconds) -> dict:
    meta = {"run_code": run_code, "task": task, "model_key": kind, "model_name": MODEL_NAMES[kind],
            "dataset": TASKS[task]["dataset"], "dataset_version": dataset_version(task), "params": params,
            "train_seconds": round(seconds, 1), **metrics}
    (out / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    with SessionLocal() as s:
        row = ModelRun(
            run_code=run_code, task=task, model_key=kind, model_name=MODEL_NAMES[kind],
            dataset=meta["dataset"], dataset_version=meta["dataset_version"],
            params=json.dumps(params, ensure_ascii=False), accuracy=metrics["accuracy"], f1_macro=metrics["f1_macro"],
            precision_macro=metrics["precision_macro"], recall_macro=metrics["recall_macro"],
            per_class=json.dumps(metrics["per_class"], ensure_ascii=False), confusion=json.dumps(metrics["confusion"], ensure_ascii=False),
            # dấu "/" để đọc được trên cả Windows lẫn Linux/WSL
            train_seconds=round(seconds, 1), artifact_path=out.relative_to(MODELS_DIR.parent.parent).as_posix(),
        )
        s.add(row)
        s.commit()
        # tự chọn mô hình F1-macro cao nhất, trừ khi quản trị đã chọn tay cho task này
        current = s.scalars(select(ModelRun).where(ModelRun.task == task, ModelRun.selected.is_(True))).first()
        if current is None or current.selected_by == "auto":
            select_best(task, s)
    logger.info("[%s/%s] TEST accuracy %.4f, F1-macro %.4f (%.0fs) -> %s", task, kind, metrics["accuracy"], metrics["f1_macro"], seconds, run_code)
    return meta


def select_best(task: str, session=None) -> str | None:
    own = session is None
    s = session or SessionLocal()
    try:
        best = s.scalars(select(ModelRun).where(ModelRun.task == task).order_by(ModelRun.f1_macro.desc())).first()
        if best:
            select_run(best.id, s, by="auto")
        return best.run_code if best else None
    finally:
        if own:
            s.close()


def select_run(run_id: int, session, by: str) -> None:
    """Đánh dấu một lần huấn luyện là mô hình được dùng cho task của nó (bỏ chọn các lần khác).
    by="auto" -> lần huấn luyện tốt hơn sau này sẽ tự thay; tên người -> giữ nguyên tới khi chọn lại."""
    row = session.get(ModelRun, run_id)
    session.execute(update(ModelRun).where(ModelRun.task == row.task).values(selected=False, selected_by=None))
    row.selected = True
    row.selected_by = by
    session.commit()
