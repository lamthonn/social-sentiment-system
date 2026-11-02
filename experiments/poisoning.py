"""T-45 + T-29: tấn công đầu độc dữ liệu (lật nhãn) và phòng vệ bằng phát hiện nhãn đáng ngờ.

Tấn công: lật ngẫu nhiên p% nhãn của tập huấn luyện sang một nhãn khác.
Phòng vệ (data validation): dự đoán chéo 5-fold trên tập đã bị đầu độc; mẫu nào mô hình gán xác suất
rất thấp cho chính nhãn của nó (< 0.15) bị coi là đáng ngờ và loại trước khi huấn luyện lại.
Mô hình: TF-IDF + Logistic Regression (M-01) - đủ nhanh để quét nhiều mức p.
Chạy: python -m experiments.poisoning
"""
from __future__ import annotations

import numpy as np
from sklearn.model_selection import StratifiedKFold

from experiments import r4, save_result
from models.sentiment.train import _baseline_pipeline, _features, evaluate, load_split

RATES = (0.0, 0.1, 0.2, 0.3, 0.4)
THRESHOLD = 0.15
C = {"sentiment": 2.0, "emotion": 1.0}  # C tốt nhất trên validation ở R-01, R-03


def flip(labels: np.ndarray, rate: float, classes: list[str], rng) -> tuple[np.ndarray, np.ndarray]:
    y = labels.copy()
    idx = rng.choice(len(y), int(rate * len(y)), replace=False)
    for i in idx:
        y[i] = rng.choice([c for c in classes if c != y[i]])
    mask = np.zeros(len(y), bool)
    mask[idx] = True
    return y, mask


def run() -> None:
    rows, findings = [], []
    for task in ("sentiment", "emotion"):
        train, test = load_split(task, "train"), load_split(task, "test")
        x, x_test = _features(train["clean_text"]), _features(test["clean_text"])
        classes = sorted(train["label"].unique())
        for rate in RATES:
            rng = np.random.default_rng(42)
            y, poisoned = flip(train["label"].to_numpy(), rate, classes, rng)
            model = _baseline_pipeline("tfidf-lr", C[task]).fit(x, y)
            f1 = evaluate(test["label"].tolist(), model.predict(x_test).tolist(), classes)["f1_macro"]
            # phòng vệ: xác suất ngoài-fold của chính nhãn đã cho
            own_prob = np.zeros(len(y))
            for tr, va in StratifiedKFold(5, shuffle=True, random_state=0).split(x, y):
                m = _baseline_pipeline("tfidf-lr", C[task]).fit([x[i] for i in tr], y[tr])
                proba = m.predict_proba([x[i] for i in va])
                col = {c: j for j, c in enumerate(m.classes_)}
                own_prob[va] = proba[np.arange(len(va)), [col[c] for c in y[va]]]
            suspicious = own_prob < THRESHOLD
            keep = ~suspicious
            defended = _baseline_pipeline("tfidf-lr", C[task]).fit([x[i] for i in np.where(keep)[0]], y[keep])
            f1_def = evaluate(test["label"].tolist(), defended.predict(x_test).tolist(), classes)["f1_macro"]
            tp = int((suspicious & poisoned).sum())
            rows.append({
                "Bài toán": "Quan điểm (VSFC)" if task == "sentiment" else "Cảm xúc (VSMEC)", "Tỉ lệ lật nhãn": f"{int(rate * 100)}%",
                "F1-macro không phòng vệ": r4(f1), "F1-macro có phòng vệ": r4(f1_def),
                "Mẫu bị loại": int(suspicious.sum()),
                "Precision phát hiện": r4(tp / suspicious.sum()) if suspicious.sum() and poisoned.sum() else None,
                "Recall phát hiện": r4(tp / poisoned.sum()) if poisoned.sum() else None,
            })
            print(rows[-1])
    for task in ("Quan điểm (VSFC)", "Cảm xúc (VSMEC)"):
        r = [x for x in rows if x["Bài toán"] == task]
        base, worst = r[0], r[-1]
        findings.append(f"{task}: lật 40% nhãn làm F1-macro giảm từ {base['F1-macro không phòng vệ']} xuống {worst['F1-macro không phòng vệ']}; "
                        f"có phòng vệ còn {worst['F1-macro có phòng vệ']} (phát hiện đúng {worst['Recall phát hiện']:.0%} mẫu bị lật).")
        mid = r[2]
        findings.append(f"{task}, mức lật 20%: phòng vệ {'cải thiện' if mid['F1-macro có phòng vệ'] > mid['F1-macro không phòng vệ'] else 'không cải thiện'} F1-macro "
                        f"({mid['F1-macro không phòng vệ']} -> {mid['F1-macro có phòng vệ']}).")
    zero = [x for x in rows if x["Tỉ lệ lật nhãn"] == "0%"]
    findings.append("Khi KHÔNG bị tấn công (0%), phòng vệ vẫn loại "
                    + ", ".join(f"{z['Mẫu bị loại']} mẫu ở {z['Bài toán']} (F1 {z['F1-macro không phòng vệ']} -> {z['F1-macro có phòng vệ']})" for z in zero)
                    + " - đó là mẫu khó/nhập nhằng có nhãn đúng; chỉ nên bật phòng vệ khi giám sát nghi ngờ dữ liệu bị nhiễm, hoặc dùng ngưỡng chặt hơn.")
    save_result("poisoning", "Tấn công đầu độc dữ liệu (lật nhãn) và phòng vệ", "CH4 - an toàn mô hình học máy (T-45, T-29)",
                f"Lật ngẫu nhiên p% nhãn của tập huấn luyện; mô hình TF-IDF + Logistic Regression. Phòng vệ: dự đoán chéo 5-fold, loại mẫu có xác suất nhãn của chính nó < {THRESHOLD} rồi huấn luyện lại. Đánh giá trên tập test sạch. Huấn luyện chỉ trên tập train (không gộp validation như R-01/R-03) nên mốc 0% thấp hơn R-01/R-03 một chút.",
                [{"title": "F1-macro theo mức đầu độc", "columns": list(rows[0].keys()), "rows": rows}], findings)


if __name__ == "__main__":
    run()
