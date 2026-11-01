"""T-44 (CH4, QD-06): đánh đổi riêng tư – độ chính xác bằng DP-SGD (Opacus).

Thiết kế:
- Bộ trích đặc trưng: ViSoBERT gốc (huấn luyện công khai, không dùng dữ liệu đề tài), đóng băng, trung bình token.
- Phần học trên dữ liệu đề tài: lớp phân loại tuyến tính. Huấn luyện thường (ε = ∞) và DP-SGD với ε ∈ {0.5, 1, 2, 4, 8},
  δ = 1/N. Bảo đảm (ε, δ)-DP áp cho dữ liệu huấn luyện của lớp phân loại này.
- Chuẩn hóa L2 từng mẫu (không dùng thống kê của tập huấn luyện để khỏi rò rỉ ngoài phạm vi DP).
- 3 seed cho mỗi mức, báo trung bình ± độ lệch chuẩn F1-macro trên tập test.
Chạy: python -m experiments.dp
"""
from __future__ import annotations

import warnings

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from experiments import r4, save_result
from experiments.embed import embed
from models.sentiment.train import evaluate, load_split

EPSILONS = (0.5, 1.0, 2.0, 4.0, 8.0, None)  # None = không riêng tư
SEEDS = (0, 1, 2)
EPOCHS, BATCH, LR, CLIP = 30, 256, 5e-3, 1.0
warnings.filterwarnings("ignore")


def features(task: str, split: str):
    df = load_split(task, split)
    x = embed(df["clean_text"].tolist())
    x = x / np.linalg.norm(x, axis=1, keepdims=True)
    return torch.tensor(x), df["label"].tolist()


def train_head(x, y, n_classes: int, eps: float | None, seed: int, device: str):
    from opacus import PrivacyEngine

    torch.manual_seed(seed)
    model = nn.Linear(x.shape[1], n_classes).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loader = DataLoader(TensorDataset(x, y), batch_size=BATCH, shuffle=True)
    noise = 0.0
    if eps is not None:
        engine = PrivacyEngine(accountant="rdp")
        model, opt, loader = engine.make_private_with_epsilon(
            module=model, optimizer=opt, data_loader=loader, target_epsilon=eps, target_delta=1 / len(x),
            epochs=EPOCHS, max_grad_norm=CLIP)
        noise = opt.noise_multiplier
    loss_fn = nn.CrossEntropyLoss()
    for _ in range(EPOCHS):
        for xb, yb in loader:
            if len(xb) == 0:
                continue
            opt.zero_grad()
            loss_fn(model(xb.to(device)), yb.to(device)).backward()
            opt.step()
    real_eps = engine.get_epsilon(1 / len(x)) if eps is not None else None
    return model, noise, real_eps


def run() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows, findings = [], []
    for task in ("sentiment", "emotion"):
        x_tr, y_tr = features(task, "train")
        x_te, y_te = features(task, "test")
        labels = sorted(set(y_tr))
        lab2id = {l: i for i, l in enumerate(labels)}
        y = torch.tensor([lab2id[l] for l in y_tr])
        task_name = "Quan điểm (VSFC)" if task == "sentiment" else "Cảm xúc (VSMEC)"
        for eps in EPSILONS:
            f1s, noise, real = [], 0.0, None
            for seed in SEEDS:
                model, noise, real = train_head(x_tr, y, len(labels), eps, seed, device)
                with torch.no_grad():
                    pred = model(x_te.to(device)).argmax(-1).cpu().tolist()
                f1s.append(evaluate(y_te, [labels[i] for i in pred], labels)["f1_macro"])
            rows.append({"Bài toán": task_name, "ε (mục tiêu)": "∞ (không riêng tư)" if eps is None else eps,
                         "ε đạt được": r4(real) if real is not None else None, "δ": f"1/{len(x_tr)}",
                         "Hệ số nhiễu": r4(noise), "F1-macro (TB)": r4(np.mean(f1s)), "Độ lệch chuẩn": r4(np.std(f1s))})
            print(rows[-1])
    for task_name in ("Quan điểm (VSFC)", "Cảm xúc (VSMEC)"):
        r = {str(x["ε (mục tiêu)"]): x["F1-macro (TB)"] for x in rows if x["Bài toán"] == task_name}
        inf = r["∞ (không riêng tư)"]
        findings.append(f"{task_name}: không riêng tư {inf}; ε=8: {r['8.0']} (−{inf - r['8.0']:.3f}); ε=1: {r['1.0']} (−{inf - r['1.0']:.3f}); ε=0.5: {r['0.5']}.")
    findings.append("So với fine-tune toàn bộ ViSoBERT không riêng tư (R-05: 0.809, R-06: 0.665), phần lớn chênh lệch đến từ việc đóng băng bộ trích đặc trưng, "
                    "không phải từ DP - cần tách hai yếu tố này khi viết báo cáo.")
    findings.append("DP-SGD cho toàn bộ ViSoBERT (thay vì chỉ lớp cuối) cần nhiều bộ nhớ hơn GPU 4GB hiện có - để ở hướng phát triển.")
    save_result("dp", "Đánh đổi riêng tư – độ chính xác (DP-SGD)", "CH4 - học máy bảo toàn quyền riêng tư (T-44, QD-06)",
                f"Đặc trưng: ViSoBERT gốc đóng băng (trung bình token, chuẩn hóa L2 từng mẫu). Lớp phân loại tuyến tính huấn luyện bằng Adam, "
                f"{EPOCHS} epoch, batch {BATCH}, lr {LR}; DP-SGD qua Opacus (RDP accountant, cắt gradient từng mẫu ở {CLIP}), δ = 1/N. "
                f"Mỗi mức chạy {len(SEEDS)} seed. Bảo đảm riêng tư áp cho dữ liệu huấn luyện của lớp phân loại.",
                [{"title": "F1-macro theo mức riêng tư ε (nhỏ hơn = riêng tư hơn)", "columns": list(rows[0].keys()), "rows": rows}], findings)


if __name__ == "__main__":
    run()
