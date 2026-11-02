"""T-23 (CH2): so sánh phương pháp gom chủ đề trên UIT-VSFC - bộ có nhãn chủ đề do người gán
(giảng viên / chương trình đào tạo / cơ sở vật chất / khác) nên đo được khách quan bằng NMI, ARI, purity.

Phương pháp (k = 4): TF-IDF + NMF (đang dùng trong pipeline, M-21), LDA (M-12), K-means trên TF-IDF (M-13),
K-means trên embedding ViSoBERT gốc (M-13 + M-18, cần GPU hoặc chạy chậm trên CPU).
Chạy: python -m experiments.topics_eval [--no-embeddings]
"""
from __future__ import annotations

import sys
import time
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from experiments import r4, save_result
from models.trend.trends import STOPWORDS, _topics_for_group, make_vectorizer
from pipeline import DATASETS_DIR
from preprocessing.text import clean_text

TOPICS = {0: "Giảng viên", 1: "Chương trình đào tạo", 2: "Cơ sở vật chất", 3: "Khác"}
K = 4


def purity(true, pred) -> float:
    return sum(Counter(t for t, p in zip(true, pred) if p == c).most_common(1)[0][1] for c in set(pred)) / len(true)


def describe(true, pred, texts) -> list[str]:
    """Mỗi cụm: chủ đề người gán chiếm đa số + tỉ lệ."""
    out = []
    for c in sorted(set(pred)):
        members = [t for t, p in zip(true, pred) if p == c]
        top, n = Counter(members).most_common(1)[0]
        out.append(f"cụm {c}: {len(members)} câu, {n / len(members):.0%} là '{TOPICS[top]}'")
    return out


def run(with_embeddings: bool) -> None:
    src = DATASETS_DIR / "vsfc" / "source"
    df = pd.concat([pd.read_parquet(src / f"{s}.parquet") for s in ("train", "validation", "test")], ignore_index=True)
    df["clean"] = df["sentence"].map(lambda s: clean_text(s).text)
    texts, true = df["clean"].tolist(), df["topic"].tolist()
    rows, details = [], {}

    def add(name: str, pred, seconds: float, keywords=None):
        rows.append({"Phương pháp": name, "NMI": r4(normalized_mutual_info_score(true, pred)), "ARI": r4(adjusted_rand_score(true, pred)),
                     "Purity": r4(purity(true, pred)), "Thời gian (giây)": round(seconds, 1)})
        details[name] = describe(true, pred, texts) + ([f"từ khóa cụm {i}: {', '.join(k)}" for i, k in enumerate(keywords)] if keywords else [])
        print(rows[-1])

    t0 = time.time()
    kw, assign = _topics_for_group(texts, k=K)
    add("TF-IDF + NMF (M-21, đang dùng)", assign, time.time() - t0, kw)

    t0 = time.time()
    cv = CountVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, token_pattern=r"(?u)\b[^\W\d_]{2,}\b", stop_words=list(STOPWORDS))
    counts = cv.fit_transform(texts)
    lda = LatentDirichletAllocation(n_components=K, random_state=42, learning_method="batch", max_iter=30)
    doc_topic = lda.fit_transform(counts)
    vocab = cv.get_feature_names_out()
    add("LDA (M-12)", doc_topic.argmax(1), time.time() - t0, [[vocab[i] for i in c.argsort()[::-1][:6]] for c in lda.components_])

    t0 = time.time()
    tfidf = make_vectorizer().fit_transform(texts)
    add("K-means trên TF-IDF (M-13)", KMeans(K, n_init=10, random_state=42).fit_predict(tfidf), time.time() - t0)

    if with_embeddings:
        from experiments.embed import embed
        t0 = time.time()
        emb = embed(texts)
        emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
        add("K-means trên embedding ViSoBERT (M-13 + M-18)", KMeans(K, n_init=10, random_state=42).fit_predict(emb), time.time() - t0)

    best = max(rows, key=lambda r: r["NMI"])
    dist = Counter(true)
    findings = [
        f"Tốt nhất theo NMI: {best['Phương pháp']} (NMI {best['NMI']}, ARI {best['ARI']}, purity {best['Purity']}).",
        f"Dữ liệu lệch chủ đề: {', '.join(f'{TOPICS[k]} {v / len(true):.0%}' for k, v in sorted(dist.items()))} - purity tối thiểu (gán hết vào chủ đề lớn nhất) là {max(dist.values()) / len(true):.2f}, nên cần đọc kèm NMI/ARI.",
        "Gom cụm không giám sát chỉ tìm cấu trúc chung; xu hướng trên dữ liệu thật còn phụ thuộc chuỗi thời gian (chưa có dữ liệu YouTube để đánh giá phần phân loại xu hướng).",
    ]
    save_result("topics_eval", "So sánh phương pháp gom chủ đề", "CH2 - phát hiện chủ đề/xu hướng (T-23)",
                f"Gom {len(texts)} câu UIT-VSFC (train+validation+test) thành k = {K} cụm, so với nhãn chủ đề người gán. "
                "NMI/ARI: 1 = khớp hoàn toàn, 0 = ngẫu nhiên. Văn bản làm sạch bằng cùng hàm của pipeline.",
                [{"title": "Chất lượng gom cụm so với chủ đề người gán", "columns": list(rows[0].keys()), "rows": rows}], findings,
                {"details": details})


if __name__ == "__main__":
    run(with_embeddings="--no-embeddings" not in sys.argv)
