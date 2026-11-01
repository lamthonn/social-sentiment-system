"""Ghi mỗi lượt chạy một bước pipeline vào bảng pipeline_runs (dùng cho giám sát PL-08 và webapp)."""
from __future__ import annotations

import json
import logging
import traceback
from contextlib import contextmanager
from datetime import datetime

from storage.database import SessionLocal
from storage.models import PipelineRun

logger = logging.getLogger(__name__)


class Run:
    def __init__(self, row_id: int):
        self.id = row_id
        self.records_in = 0
        self.records_out = 0
        self.info: dict = {}
        self.status = "success"


@contextmanager
def pipeline_run(step: str, triggered_by: str = "cli"):
    """with pipeline_run("clean") as run: run.records_in = …; run.info[...] = …
    Lỗi trong khối -> lượt chạy được ghi 'failed' kèm traceback rồi ném lại lỗi."""
    with SessionLocal() as s:
        row = PipelineRun(step=step, status="running", triggered_by=triggered_by)
        s.add(row)
        s.commit()
        run = Run(row.id)
    logger.info("[%s] bắt đầu (lượt #%d)", step, run.id)
    error = None
    try:
        yield run
    except Exception as exc:  # noqa: BLE001 - ghi lại rồi ném tiếp
        run.status = "failed"
        run.info["error"] = f"{type(exc).__name__}: {exc}"
        run.info["traceback"] = traceback.format_exc()[-4000:]
        error = exc
    finally:
        with SessionLocal() as s:
            row = s.get(PipelineRun, run.id)
            row.status = run.status
            row.finished_at = datetime.utcnow()
            row.records_in = run.records_in
            row.records_out = run.records_out
            row.message = json.dumps(run.info, ensure_ascii=False, default=str)
            s.commit()
        logger.info("[%s] %s: vào %d, ra %d", step, run.status, run.records_in, run.records_out)
    if error is not None:
        raise error
