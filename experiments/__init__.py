"""Thực nghiệm bổ sung cho báo cáo (CH1, CH2, CH4). Chạy: python -m experiments.<tên>
Mỗi thực nghiệm ghi data/experiments/<tên>.json: {title, question, description, tables: [{title, columns, rows}], findings}
- webapp hiển thị ở mục Mô hình > Thực nghiệm bổ sung."""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime

from pipeline import DATA_DIR

EXP_DIR = DATA_DIR / "experiments"


def save_result(name: str, title: str, question: str, description: str, tables: list[dict], findings: list[str], extra: dict | None = None) -> dict:
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    env = {"python": sys.version.split()[0], "platform": platform.platform()}
    try:
        import torch
        env["torch"] = torch.__version__
        env["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "không"
    except ImportError:
        pass
    data = {"name": name, "title": title, "question": question, "description": description, "tables": tables,
            "findings": findings, "created_at": datetime.now().isoformat(timespec="seconds"), "env": env, **(extra or {})}
    (EXP_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"tables": tables, "findings": findings}, ensure_ascii=False, indent=1, default=str))
    return data


def r4(x: float) -> float:
    return round(float(x), 4)
