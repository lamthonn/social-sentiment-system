"""Chuẩn bị bộ dữ liệu có nhãn (bước PL-03, nguồn DS-03 UIT-VSMEC và DS-04 UIT-VSFC).

Tải bản parquet từ Hugging Face (chỉ khi chưa có), đổi nhãn sang tiếng Việt, làm sạch bằng đúng
hàm dùng cho dữ liệu thu thập (preprocessing.text.clean_text), ghi data/datasets/<tên>/{split}.parquet
và meta.json (phiên bản = hash nội dung, thống kê phân bố nhãn).
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

import pandas as pd

from pipeline import DATASETS_DIR
from preprocessing.text import PIPELINE_VERSION, clean_text

SPLITS = ("train", "validation", "test")
SOURCES = {
    "vsfc": {
        "hf": "uitnlp/vietnamese_students_feedback",
        "title": "UIT-VSFC (phản hồi sinh viên) - quan điểm 3 lớp",
        "text": ["sentence"], "label": ["sentiment"],
        # 0 negative, 1 neutral, 2 positive (theo thẻ dữ liệu của bộ UIT-VSFC)
        "map": {0: "Tiêu cực", 1: "Trung tính", 2: "Tích cực"},
    },
    "vsmec": {
        "hf": "tridm/UIT-VSMEC",
        "title": "UIT-VSMEC (bình luận Facebook) - cảm xúc 7 nhãn",
        "text": ["Sentence", "sentence", "text"], "label": ["Emotion", "emotion", "label"],
        "map": {"Enjoyment": "Vui vẻ", "Sadness": "Buồn bã", "Fear": "Sợ hãi", "Anger": "Tức giận",
                "Disgust": "Ghê tởm", "Surprise": "Ngạc nhiên", "Other": "Khác"},
    },
}


def _download(name: str) -> Path:
    src = DATASETS_DIR / name / "source"
    src.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        path = src / f"{split}.parquet"
        if not path.exists():
            url = f"https://huggingface.co/api/datasets/{SOURCES[name]['hf']}/parquet/default/{split}/0.parquet"
            urllib.request.urlretrieve(url, path)
    return src


def _pick(df: pd.DataFrame, candidates: list[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"Không thấy cột nào trong {candidates}; có: {list(df.columns)}")


def validate(out_dir: Path) -> dict:
    """Kiểm tra dữ liệu huấn luyện (T-29): rò rỉ train↔test, trùng lặp, câu trùng mà nhãn mâu thuẫn, câu quá ngắn."""
    sp = {s: pd.read_parquet(out_dir / f"{s}.parquet") for s in SPLITS}
    train_texts = set(sp["train"]["clean_text"])
    conflicts = sp["train"].groupby("clean_text")["label"].nunique()
    return {
        "test_in_train": int(sp["test"]["clean_text"].isin(train_texts).sum()),
        "validation_in_train": int(sp["validation"]["clean_text"].isin(train_texts).sum()),
        "train_duplicates": int(sp["train"]["clean_text"].duplicated().sum()),
        "train_conflicting_labels": int((conflicts > 1).sum()),
        "train_very_short": int((sp["train"]["clean_text"].str.split().str.len() < 2).sum()),
        "note": "test_in_train > 0: câu test trùng nguyên văn (sau làm sạch) với train - kết quả test có thể hơi lạc quan",
    }


def prepare(name: str) -> dict:
    cfg = SOURCES[name]
    src = _download(name)
    out_dir = DATASETS_DIR / name
    stats, digest = {}, hashlib.sha1(PIPELINE_VERSION.encode())
    for split in SPLITS:
        raw = pd.read_parquet(src / f"{split}.parquet")
        text_col, label_col = _pick(raw, cfg["text"]), _pick(raw, cfg["label"])
        df = pd.DataFrame({"text": raw[text_col].astype(str), "label": raw[label_col].map(cfg["map"])})
        unknown = df["label"].isna().sum()
        if unknown:
            raise ValueError(f"{name}/{split}: {unknown} nhãn lạ: {raw[label_col][df['label'].isna()].unique()[:5]}")
        cleaned = df["text"].map(clean_text)
        df["clean_text"] = cleaned.map(lambda r: r.text)
        df = df[df["clean_text"].str.len() > 0].reset_index(drop=True)
        df.to_parquet(out_dir / f"{split}.parquet", index=False)
        digest.update(pd.util.hash_pandas_object(df[["clean_text", "label"]], index=False).values.tobytes())
        stats[split] = {"rows": len(df), "dropped_empty": int(len(raw) - len(df)), "labels": df["label"].value_counts().to_dict()}
    meta = {"name": name, "title": cfg["title"], "source": f"huggingface.co/datasets/{cfg['hf']}",
            "version": digest.hexdigest()[:10], "preprocessing": PIPELINE_VERSION, "splits": stats,
            "validation": validate(out_dir)}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
