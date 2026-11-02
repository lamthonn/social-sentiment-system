"""T-33 (CH3, CH5): hiệu năng các thành phần của hệ thống trên máy chạy thử.

Đo: tốc độ làm sạch (câu/giây); với từng mô hình: thông lượng theo lô (câu/giây), độ trễ 1 câu (trung vị, ms),
bộ nhớ GPU đỉnh; độ trễ API (trung vị) cho các endpoint đọc chính, gọi trong tiến trình qua TestClient.
Chạy: python -m experiments.perf
"""
from __future__ import annotations

import statistics
import time

import torch
from sqlalchemy import select

from experiments import r4, save_result
from models.sentiment.predict import load_run
from models.sentiment.train import load_split
from preprocessing.text import clean_text
from storage.database import SessionLocal
from storage.models import ModelRun


def timeit(fn, repeat: int) -> list[float]:
    out = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t0)
    return out


def run() -> None:
    texts_raw = load_split("emotion", "test")["text"].tolist() + load_split("sentiment", "test")["text"].tolist()
    rows, findings = [], []

    t = timeit(lambda: [clean_text(s) for s in texts_raw], 3)
    clean_rate = len(texts_raw) / statistics.median(t)
    rows.append({"Thành phần": "Làm sạch (preprocessing/text.py)", "Thiết bị": "CPU", "Thông lượng (câu/giây)": round(clean_rate),
                 "Độ trễ 1 câu (ms)": r4(1000 / clean_rate), "Bộ nhớ GPU đỉnh (MB)": None})
    batch = [clean_text(s).text for s in texts_raw[:1000]]

    with SessionLocal() as s:
        runs = s.scalars(select(ModelRun).where(ModelRun.task == "sentiment").order_by(ModelRun.created_at.desc())).all()
    seen = set()
    for run_ in runs:
        if run_.model_key in seen:
            continue
        seen.add(run_.model_key)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        p = load_run(run_.run_code)
        p.predict(batch[:32])  # khởi động (nạp CUDA kernel, cache)
        thr = len(batch) / statistics.median(timeit(lambda: p.predict(batch), 3))
        lat = statistics.median(timeit(lambda: p.predict([batch[7]]), 30)) * 1000
        gpu = run_.model_key not in ("tfidf-lr", "tfidf-svm") and torch.cuda.is_available()
        rows.append({"Thành phần": f"Dự đoán – {run_.model_name}", "Thiết bị": torch.cuda.get_device_name(0) if gpu else "CPU",
                     "Thông lượng (câu/giây)": round(thr), "Độ trễ 1 câu (ms)": r4(lat),
                     "Bộ nhớ GPU đỉnh (MB)": round(torch.cuda.max_memory_allocated() / 2**20) if gpu else None})
        print(rows[-1])
        del p

    api_rows = []
    try:
        from fastapi.testclient import TestClient

        from api.main import app
        from security.auth import create_token
        client = TestClient(app)
        # token hợp lệ chỉ cần user tồn tại trong DB -> dùng tài khoản tạm rồi xóa
        from security.auth import hash_password
        from storage.models import User
        with SessionLocal() as s:
            s.add(User(username="zz_perf", password_hash=hash_password("Perf-only-123"), role="admin"))
            s.commit()
        try:
            h = {"Authorization": f"Bearer {create_token('zz_perf', 'admin')}"}
            for path in ("/health", "/dashboard/summary?days=30", "/analysis/posts?page_size=20", "/topics/latest", "/models/runs", "/pipeline/runs"):
                client.get(path, headers=h)
                ms = statistics.median(timeit(lambda: client.get(path, headers=h), 20)) * 1000
                api_rows.append({"Endpoint": path, "Trung vị (ms)": r4(ms)})
                print(api_rows[-1])
        finally:
            with SessionLocal() as s:
                s.query(User).filter(User.username == "zz_perf").delete()
                s.commit()
    except Exception as exc:  # noqa: BLE001
        findings.append(f"Không đo được độ trễ API: {exc}")

    fastest = max(rows[1:], key=lambda r: r["Thông lượng (câu/giây)"])
    findings.append(f"Làm sạch đạt khoảng {round(clean_rate):,} câu/giây trên CPU - không phải nút cổ chai.".replace(",", "."))
    findings.append(f"Mô hình nhanh nhất: {fastest['Thành phần'].replace('Dự đoán – ', '')} ({fastest['Thông lượng (câu/giây)']} câu/giây). "
                    "Transformer chậm hơn nhưng vẫn đủ cho quy mô thu thập của đề tài (quota YouTube ~10.000 đơn vị/ngày tương đương tối đa vài trăm nghìn bình luận/ngày).")
    findings.append("Độ trễ API đo với CSDL gần như trống (chưa có dữ liệu thu thập thật) - cần đo lại khi có dữ liệu.")
    tables = [{"title": "Thông lượng và độ trễ", "columns": list(rows[0].keys()), "rows": rows}]
    if api_rows:
        tables.append({"title": "Độ trễ API (CSDL hiện tại)", "columns": list(api_rows[0].keys()), "rows": api_rows})
    save_result("perf", "Hiệu năng hệ thống", "CH3, CH5 - hiệu năng (T-33)",
                f"Đo trên máy chạy thử. Thông lượng: dự đoán 1.000 câu (trung vị 3 lần); độ trễ 1 câu: trung vị 30 lần; làm sạch {len(texts_raw)} câu. "
                "Bước PhoBERT gồm cả tách từ bằng underthesea.", tables, findings)


if __name__ == "__main__":
    run()
