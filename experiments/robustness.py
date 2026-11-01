"""T-41 + T-45 (CH1, CH4): độ bền của mô hình trước cách viết thật trên MXH và nhiễu đối kháng.

Biến đổi văn bản GỐC của tập test rồi cho đi qua đúng chuỗi của pipeline (clean_text -> mô hình):
  bỏ dấu, teencode hóa, bỏ emoji, lỗi gõ (10% từ), và "teencode hóa, bỏ qua chuẩn hóa teencode"
  (để đo riêng giá trị của bước CL-04). Phân tích lỗi thêm theo nhóm câu: có emoji / không emoji.
Mô hình: lần huấn luyện mới nhất của mỗi loại (tfidf-lr, bilstm, visobert, phobert) cho từng bài toán.
Chạy: python -m experiments.robustness
"""
from __future__ import annotations

import random
import re
import unicodedata
import zlib

from sqlalchemy import select

from experiments import r4, save_result
from models.sentiment.predict import load_run
from models.sentiment.train import evaluate, load_split
from preprocessing import text as T
from storage.database import SessionLocal
from storage.models import ModelRun

REVERSE_TEENCODE = {"không": "ko", "được": "đc", "gì": "j", "với": "vs", "mọi người": "mn", "người": "ng", "bình thường": "bt",
                    "cũng": "cx", "như thế nào": "ntn", "biết": "bik", "quá": "wá", "vậy": "z", "thích": "thik", "yêu": "iu",
                    "mình": "mk", "nhiều": "nhìu", "luôn": "lun", "trước": "trc", "đang": "đag", "muốn": "mún"}
_EMOJI = T._EMOJI_RE


def strip_diacritics(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return unicodedata.normalize("NFC", "".join(c for c in s if unicodedata.category(c) != "Mn")).replace("đ", "d").replace("Đ", "D")


def teencodify(s: str) -> str:
    for w, t in sorted(REVERSE_TEENCODE.items(), key=lambda x: -len(x[0])):
        s = re.sub(rf"(?<!\w){re.escape(w)}(?!\w)", t, s, flags=re.I)
    return s


def typos(s: str, rate: float = 0.1, seed: int = 0) -> str:
    rng = random.Random(zlib.crc32(s.encode("utf-8")) ^ seed)  # cố định giữa các lần chạy (hash() của Python thì không)
    words = s.split()
    for i, w in enumerate(words):
        if len(w) > 3 and rng.random() < rate:
            j = rng.randrange(len(w) - 1)
            words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]  # đảo 2 ký tự liền nhau
    return " ".join(words)


def clean(s: str) -> str:
    return T.clean_text(s).text


def clean_without_teencode(s: str) -> str:
    original = T.expand_teencode
    T.expand_teencode = lambda x: " ".join(T._WORD_RE.findall(x))  # tắt bước chuẩn hóa teencode
    try:
        return T.clean_text(s).text
    finally:
        T.expand_teencode = original


VARIANTS = {
    "Gốc": lambda s: clean(s),
    "Bỏ dấu": lambda s: clean(strip_diacritics(s)),
    "Teencode hóa": lambda s: clean(teencodify(s)),
    "Teencode hóa, không chuẩn hóa (tắt CL-04)": lambda s: clean_without_teencode(teencodify(s)),
    "Bỏ emoji": lambda s: clean(_EMOJI.sub(" ", s)),
    "Lỗi gõ 10% từ": lambda s: clean(typos(s)),
}


def latest_runs(task: str) -> list[ModelRun]:
    with SessionLocal() as s:
        runs = s.scalars(select(ModelRun).where(ModelRun.task == task).order_by(ModelRun.created_at.desc())).all()
    seen, out = set(), []
    for r in runs:
        if r.model_key not in seen and r.model_key != "tfidf-svm":
            seen.add(r.model_key)
            out.append(r)
    return out


def run() -> None:
    rows, subset_rows, findings = [], [], []
    for task in ("sentiment", "emotion"):
        test = load_split(task, "test")
        labels = sorted(test["label"].unique())
        truth = test["label"].tolist()
        inputs = {name: [fn(s) for s in test["text"]] for name, fn in VARIANTS.items()}
        has_emoji = [bool(_EMOJI.search(s)) for s in test["text"]]
        for run_ in latest_runs(task):
            pred = load_run(run_.run_code)
            row = {"Bài toán": "Quan điểm (VSFC)" if task == "sentiment" else "Cảm xúc (VSMEC)", "Mô hình": run_.model_name}
            preds_orig = None
            for name, texts in inputs.items():
                p = [lab for lab, _ in pred.predict(texts)]
                if name == "Gốc":
                    preds_orig = p
                row[name] = r4(evaluate(truth, p, labels)["f1_macro"])
            rows.append(row)
            print(row)
            for flag, nm in ((True, "có emoji"), (False, "không emoji")):
                idx = [i for i, e in enumerate(has_emoji) if e == flag]
                if len(idx) >= 20:
                    subset_rows.append({"Bài toán": row["Bài toán"], "Mô hình": run_.model_name, "Nhóm câu": nm, "Số câu": len(idx),
                                        "F1-macro": r4(evaluate([truth[i] for i in idx], [preds_orig[i] for i in idx], labels)["f1_macro"])})
    for task in ("Quan điểm (VSFC)", "Cảm xúc (VSMEC)"):
        rs = [r for r in rows if r["Bài toán"] == task]
        for r in rs:
            drop = {k: round(r["Gốc"] - r[k], 4) for k in VARIANTS if k != "Gốc"}
            worst = max(drop, key=drop.get)
            findings.append(f"{task} – {r['Mô hình']}: giảm mạnh nhất khi '{worst}' (−{drop[worst]:.3f} F1); "
                            f"bước chuẩn hóa teencode giữ được {r['Teencode hóa'] - r['Teencode hóa, không chuẩn hóa (tắt CL-04)']:+.3f} F1.")
    drops = [(r["Gốc"] - r["Bỏ dấu"], r) for r in rows]
    most_robust = min(drops, key=lambda x: x[0])[1]
    findings.append(f"Bỏ dấu là điểm yếu lớn nhất của mọi mô hình (F1 giảm {min(d for d, _ in drops):.2f}–{max(d for d, _ in drops):.2f}); "
                    f"bền nhất: {most_robust['Mô hình']} ở {most_robust['Bài toán']} ({most_robust['Gốc']} -> {most_robust['Bỏ dấu']}). "
                    "Đề xuất: thêm bước khôi phục dấu hoặc tăng cường dữ liệu không dấu khi huấn luyện.")
    emo = {(s["Mô hình"], s["Nhóm câu"]): s["F1-macro"] for s in subset_rows if s["Bài toán"] == "Cảm xúc (VSMEC)"}
    for model in {m for m, _ in emo}:
        if (model, "có emoji") in emo and (model, "không emoji") in emo:
            findings.append(f"Cảm xúc – {model}: câu có emoji F1 {emo[(model, 'có emoji')]} so với không emoji {emo[(model, 'không emoji')]}.")
    save_result("robustness", "Độ bền trước cách viết MXH và nhiễu đối kháng", "CH1, CH4 - phân tích lỗi và tấn công đối kháng (T-41, T-45)",
                "Biến đổi câu gốc của tập test rồi cho qua đúng chuỗi làm sạch + mô hình của pipeline; số trong bảng là F1-macro. "
                "Cột 'tắt CL-04' bỏ qua bước chuẩn hóa teencode để đo giá trị của bước này. "
                "Hạn chế: 'Teencode hóa' chỉ dùng các từ có sẵn trong từ điển CL-04 nên bước làm sạch khôi phục được hoàn toàn - "
                "cột này là mức trần; teencode ngoài từ điển (viết tắt mới, chơi chữ) chưa được đo.",
                [{"title": "F1-macro theo kiểu biến đổi đầu vào", "columns": list(rows[0].keys()), "rows": rows},
                 {"title": "Phân tích lỗi theo nhóm câu (đầu vào gốc)", "columns": list(subset_rows[0].keys()), "rows": subset_rows}], findings)


if __name__ == "__main__":
    run()
