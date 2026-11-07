"""T-48 (CH4, QD-06, M-20): mô phỏng học liên kết (federated learning) trên một máy.

Bối cảnh: nhiều đơn vị (VD các khoa/trường) cùng huấn luyện bộ phân loại mà không gửi dữ liệu thô về một chỗ -
chỉ gửi tham số mô hình. Mô phỏng K bên bằng cách chia tập train:
- IID: chia ngẫu nhiên đều;
- Non-IID: phân phối nhãn mỗi bên lệch theo Dirichlet(α) - giống thực tế mỗi đơn vị có "khẩu vị" dữ liệu riêng.
Thuật toán: FedAvg (trung bình tham số có trọng số theo số mẫu), mỗi vòng mỗi bên học E epoch cục bộ.
So với: huấn luyện tập trung (gom hết dữ liệu) và huấn luyện riêng lẻ (mỗi bên chỉ dùng dữ liệu của mình).
Mô hình: lớp tuyến tính trên đặc trưng ViSoBERT gốc đóng băng (như experiments/dp.py), vừa GPU 4GB.
Chạy: python -m experiments.federated
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from experiments import r4, save_result
from experiments.dp import features
from models.sentiment.train import evaluate

CLIENTS = 5
ROUNDS, LOCAL_EPOCHS, BATCH, LR = 40, 1, 64, 5e-3
ALPHAS = (None, 1.0, 0.3, 0.1)  # None = IID; α nhỏ = càng lệch
SEEDS = (0, 1, 2)


def split(y: np.ndarray, alpha: float | None, rng: np.random.Generator) -> list[np.ndarray]:
    idx = rng.permutation(len(y))
    if alpha is None:
        return np.array_split(idx, CLIENTS)
    parts: list[list[int]] = [[] for _ in range(CLIENTS)]
    for c in np.unique(y):
        ids = idx[y[idx] == c]
        props = rng.dirichlet([alpha] * CLIENTS)
        for k, chunk in enumerate(np.split(ids, (np.cumsum(props)[:-1] * len(ids)).astype(int))):
            parts[k] += chunk.tolist()
    return [np.array(p, dtype=int) for p in parts]


def local_train(model: nn.Module, x: torch.Tensor, y: torch.Tensor, epochs: int, gen: torch.Generator) -> None:
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()
    for _ in range(epochs):
        perm = torch.randperm(len(x), generator=gen)
        for i in range(0, len(x), BATCH):
            b = perm[i:i + BATCH]
            opt.zero_grad()
            loss_fn(model(x[b]), y[b]).backward()
            opt.step()


def f1(model: nn.Module, x: torch.Tensor, y_true: list[str], labels: list[str]) -> float:
    with torch.no_grad():
        pred = model(x).argmax(-1).cpu().tolist()
    return evaluate(y_true, [labels[i] for i in pred], labels)["f1_macro"]


def fedavg(parts, x, y, n_classes, x_te, y_te, labels, seed, device) -> tuple[float, list[float]]:
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed)
    glob = nn.Linear(x.shape[1], n_classes).to(device)
    curve = []
    sizes = np.array([len(p) for p in parts], dtype=float)
    for _ in range(ROUNDS):
        states = []
        for p in parts:
            if len(p) == 0:
                states.append(None)
                continue
            local = nn.Linear(x.shape[1], n_classes).to(device)
            local.load_state_dict(glob.state_dict())
            local_train(local, x[p], y[p], LOCAL_EPOCHS, gen)
            states.append(local.state_dict())
        w = sizes / sizes[[s is not None for s in states]].sum()
        glob.load_state_dict({k: sum(wi * s[k] for wi, s in zip(w, states) if s is not None) for k in glob.state_dict()})
        curve.append(f1(glob, x_te, y_te, labels))
    return curve[-1], curve


def run() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows, curves, findings = [], [], []
    for task in ("sentiment", "emotion"):
        x_tr, y_tr = features(task, "train")
        x_te, y_te = features(task, "test")
        labels = sorted(set(y_tr))
        lab2id = {l: i for i, l in enumerate(labels)}
        y_np = np.array([lab2id[l] for l in y_tr])
        x, y, xt = x_tr.to(device), torch.tensor(y_np, device=device), x_te.to(device)
        task_name = "Quan điểm (VSFC)" if task == "sentiment" else "Cảm xúc (VSMEC)"
        # tập trung: cùng số lượt cập nhật dữ liệu (ROUNDS × LOCAL_EPOCHS epoch trên toàn bộ dữ liệu)
        central = []
        for seed in SEEDS:
            torch.manual_seed(seed)
            m = nn.Linear(x.shape[1], len(labels)).to(device)
            local_train(m, x, y, ROUNDS * LOCAL_EPOCHS, torch.Generator().manual_seed(seed))
            central.append(f1(m, xt, y_te, labels))
        rows.append({"Bài toán": task_name, "Cách chia dữ liệu": "-", "Phương pháp": "Tập trung (gom hết dữ liệu)",
                     "F1-macro (TB)": r4(np.mean(central)), "Độ lệch chuẩn": r4(np.std(central)), "Lệch nhãn giữa các bên": None})
        print(rows[-1])
        for alpha in ALPHAS:
            fed, solo, skew = [], [], []
            for seed in SEEDS:
                rng = np.random.default_rng(seed)
                parts = split(y_np, alpha, rng)
                # độ lệch nhãn: trung bình khoảng cách tổng biến phân giữa phân phối nhãn của từng bên và toàn bộ
                glob_dist = np.bincount(y_np, minlength=len(labels)) / len(y_np)
                skew.append(np.mean([0.5 * np.abs(np.bincount(y_np[p], minlength=len(labels)) / max(len(p), 1) - glob_dist).sum()
                                     for p in parts if len(p)]))
                score, curve = fedavg(parts, x, y, len(labels), xt, y_te, labels, seed, device)
                fed.append(score)
                if seed == SEEDS[0]:
                    curves.append((task_name, "IID" if alpha is None else f"α={alpha}", curve))
                for k, p in enumerate(parts):  # riêng lẻ: mỗi bên tự học, chấm trên tập test chung
                    if len(p) < 10:
                        continue
                    torch.manual_seed(seed)
                    m = nn.Linear(x.shape[1], len(labels)).to(device)
                    local_train(m, x[p], y[p], ROUNDS * LOCAL_EPOCHS, torch.Generator().manual_seed(seed + k))
                    solo.append(f1(m, xt, y_te, labels))
            name = "IID (chia đều)" if alpha is None else f"Non-IID Dirichlet α={alpha}"
            for method, vals in ((f"FedAvg {CLIENTS} bên", fed), ("Riêng lẻ (TB các bên)", solo)):
                rows.append({"Bài toán": task_name, "Cách chia dữ liệu": name, "Phương pháp": method,
                             "F1-macro (TB)": r4(np.mean(vals)), "Độ lệch chuẩn": r4(np.std(vals)), "Lệch nhãn giữa các bên": r4(np.mean(skew))})
                print(rows[-1])
    for task_name in ("Quan điểm (VSFC)", "Cảm xúc (VSMEC)"):
        r = [x for x in rows if x["Bài toán"] == task_name]
        c = r[0]["F1-macro (TB)"]
        fed = {x["Cách chia dữ liệu"]: x["F1-macro (TB)"] for x in r if x["Phương pháp"].startswith("FedAvg")}
        solo = {x["Cách chia dữ liệu"]: x["F1-macro (TB)"] for x in r if x["Phương pháp"].startswith("Riêng")}
        iid, skewed = fed["IID (chia đều)"], f"Non-IID Dirichlet α={ALPHAS[-1]}"
        findings.append(f"{task_name}: tập trung {c}; FedAvg IID {iid} ({iid - c:+.3f}); lệch nhãn mạnh nhất ({skewed}) {fed[skewed]} "
                        f"({fed[skewed] - c:+.3f}). Ở mức lệch đó, mỗi bên tự học riêng chỉ đạt {solo[skewed]} - học liên kết hơn "
                        f"{fed[skewed] - solo[skewed]:+.3f}. Khi dữ liệu lệch, độ lệch chuẩn giữa các seed tăng mạnh nên thứ tự giữa các mức α "
                        "không ổn định.")
    late = [cv[-1] - cv[19] for _, s, cv in curves if s != "IID"]
    findings.append(f"Sau 40 vòng mô hình chung vẫn đang tăng (vòng 20 -> 40: +{min(late):.3f} đến +{max(late):.3f} F1 với dữ liệu lệch) - "
                    "chưa hội tụ hẳn; chênh lệch với tập trung ở trên là cận trên khi giới hạn số vòng truyền tham số.")
    findings.append("Học liên kết chỉ chia sẻ tham số, không chia sẻ dữ liệu thô - nhưng tham số vẫn có thể rò rỉ thông tin; "
                    "kết hợp với DP (experiments/dp.py) hoặc tổng hợp an toàn (secure aggregation) để bảo vệ đầy đủ.")
    findings.append("Mô phỏng trên một máy, lớp tuyến tính trên đặc trưng đóng băng; học liên kết toàn bộ Transformer cần nhiều GPU hơn và "
                    "chi phí truyền tham số lớn (~400MB/bên/vòng với ViSoBERT so với vài chục KB ở đây).")
    curve_rows = [{"Bài toán": t, "Cách chia": s, **{f"Vòng {i + 1}": r4(v) for i, v in enumerate(cv) if (i + 1) in (1, 5, 10, 20, ROUNDS)}}
                  for t, s, cv in curves]
    save_result("federated", "Mô phỏng học liên kết (FedAvg)", "CH4 - học máy bảo toàn quyền riêng tư (T-48, QD-06, M-20)",
                f"{CLIENTS} bên mô phỏng trên một máy; FedAvg {ROUNDS} vòng, mỗi vòng {LOCAL_EPOCHS} epoch cục bộ, Adam lr {LR}, batch {BATCH}. "
                "Mô hình: lớp tuyến tính trên đặc trưng ViSoBERT gốc đóng băng. Non-IID: tỉ lệ mỗi nhãn chia cho các bên theo Dirichlet(α). "
                "'Lệch nhãn' = trung bình khoảng cách tổng biến phân giữa phân phối nhãn của từng bên và toàn bộ (0 = giống hệt). "
                f"Mỗi cấu hình {len(SEEDS)} seed; 'Riêng lẻ' = mỗi bên tự học trên dữ liệu của mình, chấm trên tập test chung.",
                [{"title": "F1-macro: tập trung, học liên kết, học riêng lẻ", "columns": list(rows[0].keys()), "rows": rows},
                 {"title": "F1-macro của mô hình chung qua các vòng (seed 0)", "columns": list(curve_rows[0].keys()), "rows": curve_rows}],
                findings)


if __name__ == "__main__":
    run()
