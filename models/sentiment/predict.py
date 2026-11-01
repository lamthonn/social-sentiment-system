"""Nạp mô hình đang được chọn (model_runs.selected) cho một task và dự đoán nhãn + độ tin cậy."""
from __future__ import annotations

import json

import numpy as np
from sqlalchemy import select

from pipeline import ROOT
from preprocessing.text import emoji_tags
from storage.database import SessionLocal
from storage.models import ModelRun


class Predictor:
    def __init__(self, run: ModelRun):
        self.run_code = run.run_code
        self.model_key = run.model_key
        self.name = f"{run.model_key}:{run.run_code}"[:64]
        path = ROOT / run.artifact_path
        if run.model_key.startswith("tfidf"):
            import joblib
            self._sk = joblib.load(path / "model.joblib")
            return
        import torch
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        if run.model_key == "bilstm":
            from models.sentiment import bilstm as B
            self._lstm, self._vocab, self._labels, meta = B.load(path, self._device)
            self._max_len = meta["max_len"]
            return
        from transformers import AutoModelForSequenceClassification

        from models.sentiment.train import make_tokenizer
        meta_file = path / "pipeline_meta.json"  # lần chạy cũ (trước khi có file này) là ViSoBERT
        self._meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {"tokenizer": "spm", "word_segment": False, "max_len": 128}
        self._tok = make_tokenizer("visobert" if self._meta["tokenizer"] == "spm" else "phobert", path)
        self._hf = AutoModelForSequenceClassification.from_pretrained(path).to(self._device).eval()

    def predict(self, texts: list[str], batch_size: int = 32) -> list[tuple[str, float]]:
        if not texts:
            return []
        if self.model_key.startswith("tfidf"):
            feats = [emoji_tags(t) for t in texts]
            clf = self._sk
            if hasattr(clf, "predict_proba"):
                proba = clf.predict_proba(feats)
            else:  # LinearSVC không có xác suất -> softmax trên decision_function làm độ tin cậy tương đối
                d = clf.decision_function(feats)
                e = np.exp(d - d.max(axis=1, keepdims=True))
                proba = e / e.sum(axis=1, keepdims=True)
            classes = clf.classes_
            return [(str(classes[i]), float(p[i])) for p, i in zip(proba, proba.argmax(axis=1))]
        import torch
        out = []
        with torch.no_grad():
            if self.model_key == "bilstm":
                from models.sentiment import bilstm as B
                for i in range(0, len(texts), 256):
                    ids = B.pad_batch([self._vocab.encode(t, self._max_len) for t in texts[i:i + 256]]).to(self._device)
                    conf, idx = torch.softmax(self._lstm(ids), -1).max(-1)
                    out += [(self._labels[int(j)], float(c)) for j, c in zip(idx, conf)]
                return out
            if self._meta["word_segment"]:
                from models.sentiment.train import word_segment
                texts = word_segment(texts)
            for i in range(0, len(texts), batch_size):
                enc = self._tok(texts[i:i + batch_size], truncation=True, max_length=self._meta["max_len"], padding=True, return_tensors="pt").to(self._device)
                prob = torch.softmax(self._hf(**{k: v for k, v in enc.items() if k in ("input_ids", "attention_mask")}).logits, -1)
                conf, idx = prob.max(-1)
                out += [(self._hf.config.id2label[int(j)], float(c)) for j, c in zip(idx, conf)]
        return out


def load_selected(task: str) -> Predictor | None:
    with SessionLocal() as s:
        run = s.scalars(select(ModelRun).where(ModelRun.task == task, ModelRun.selected.is_(True))).first()
        return Predictor(run) if run else None


def load_run(run_code: str) -> Predictor:
    with SessionLocal() as s:
        return Predictor(s.scalars(select(ModelRun).where(ModelRun.run_code == run_code)).one())
