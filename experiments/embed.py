"""Embedding câu bằng ViSoBERT gốc (đã huấn luyện công khai, KHÔNG fine-tune trên dữ liệu của đề tài),
lấy trung bình các token. Dùng cho: gom chủ đề bằng embedding (T-23) và đặc trưng cho DP-SGD (T-44).
Kết quả được cache ở data/experiments/cache/<khóa>.npy."""
from __future__ import annotations

import hashlib

import numpy as np

from experiments import EXP_DIR


def embed(texts: list[str], batch_size: int = 64, max_len: int = 128) -> np.ndarray:
    key = hashlib.sha1("\n".join(texts).encode("utf-8")).hexdigest()[:16]
    path = EXP_DIR / "cache" / f"visobert-mean-{key}.npy"
    if path.exists():
        return np.load(path)
    import torch
    from transformers import AutoModel

    from models.sentiment.spm_tokenizer import SpmXlmrTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = SpmXlmrTokenizer.from_pretrained("uitnlp/visobert")
    model = AutoModel.from_pretrained("uitnlp/visobert").to(device).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            enc = tok(texts[i:i + batch_size], max_length=max_len).to(device)
            h = model(**enc).last_hidden_state
            m = enc["attention_mask"].unsqueeze(-1).float()
            out.append(((h * m).sum(1) / m.sum(1)).cpu().numpy())
    arr = np.concatenate(out).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, arr)
    return arr
