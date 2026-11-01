"""CLI pipeline.

  python -m pipeline datasets                       # PL-03: tải + làm sạch UIT-VSFC, UIT-VSMEC
  python -m pipeline train --task sentiment --model tfidf-lr   # PL-05/06 (model: tfidf-lr | tfidf-svm | bilstm | visobert | phobert)
  python -m pipeline collect | clean | predict | trends | monitor
  python -m pipeline run                            # collect -> clean -> predict -> trends -> monitor
  python -m pipeline select --task sentiment --run-code <mã lần huấn luyện>
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("collect", "clean", "predict", "trends", "monitor", "run"):
        p = sub.add_parser(name)
        p.add_argument("--by", default="cli", help="người/tiến trình kích hoạt (ghi vào pipeline_runs)")
    p = sub.add_parser("datasets")
    p.add_argument("--by", default="cli")
    p = sub.add_parser("train")
    p.add_argument("--task", choices=["sentiment", "emotion"], required=True)
    p.add_argument("--model", choices=["tfidf-lr", "tfidf-svm", "bilstm", "visobert", "phobert"], required=True)
    p.add_argument("--epochs", type=int, default=4)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--by", default="cli")
    p = sub.add_parser("select")
    p.add_argument("--task", choices=["sentiment", "emotion"], required=True)
    p.add_argument("--run-code", required=True)
    args = ap.parse_args()

    from pipeline import steps
    from pipeline.runlog import pipeline_run

    if args.cmd == "datasets":
        from pipeline.datasets import SOURCES, prepare
        with pipeline_run("datasets", args.by) as run:
            for name in SOURCES:
                meta = prepare(name)
                run.records_out += sum(v["rows"] for v in meta["splits"].values())
                run.info[name] = {"version": meta["version"], "splits": {k: v["rows"] for k, v in meta["splits"].items()}}
                print(json.dumps(meta, ensure_ascii=False, indent=2))
    elif args.cmd == "train":
        from models.sentiment import train as tr
        with pipeline_run(f"train:{args.task}", args.by) as run:
            if args.model.startswith("tfidf"):
                meta = tr.train_baseline(args.task, args.model)
            elif args.model == "bilstm":
                meta = tr.train_bilstm(args.task)
            else:
                meta = tr.train_transformer(args.task, args.model, epochs=args.epochs, batch_size=args.batch_size)
            run.records_in = meta["params"].get("train_size", 0)
            run.info = {k: meta[k] for k in ("run_code", "model_name", "accuracy", "f1_macro", "train_seconds")}
    elif args.cmd == "select":
        from sqlalchemy import select as sql_select

        from models.sentiment.train import select_run
        from storage.database import SessionLocal
        from storage.models import ModelRun
        with SessionLocal() as s:
            row = s.scalars(sql_select(ModelRun).where(ModelRun.run_code == args.run_code, ModelRun.task == args.task)).first()
            if not row:
                sys.exit(f"Không thấy lần huấn luyện {args.run_code} cho task {args.task}")
            select_run(row.id, s, by="cli")
        print(f"Đã chọn {args.run_code} cho {args.task}")
    elif args.cmd == "run":
        for fn in (steps.step_collect, steps.step_clean, steps.step_predict, steps.step_trends, steps.step_monitor):
            fn(args.by)
    else:
        getattr(steps, f"step_{args.cmd}")(args.by)


if __name__ == "__main__":
    main()
