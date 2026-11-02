"""T-40 (CH1): LLM zero-shot / few-shot cho phân loại quan điểm và cảm xúc, so với mô hình đã fine-tune.

LLM chạy cục bộ (Qwen2.5-1.5B-Instruct, Apache-2.0, vừa GPU 4GB ở fp16) -> không gửi dữ liệu ra ngoài.
Đánh giá trên mẫu phân tầng của tập test (tối đa N câu/nhãn) vì sinh văn bản chậm; mô hình được chọn
của pipeline được chấm trên CÙNG mẫu để so sánh công bằng. Few-shot: 1 ví dụ/nhãn lấy từ tập train.
Chạy: python -m experiments.llm
"""
from __future__ import annotations

import gc
import time
import unicodedata

import pandas as pd
import torch

from experiments import r4, save_result
from models.sentiment.predict import load_selected
from models.sentiment.train import evaluate, load_split

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
BATCH = 4  # lô nhỏ: lô lớn + prompt few-shot dài làm kernel GPU vượt giới hạn thời gian của Windows (TDR) -> "CUDA unknown error"
PER_LABEL = {"sentiment": 100, "emotion": 40}
DESC = {
    "sentiment": "quan điểm của câu phản hồi sinh viên",
    "emotion": "cảm xúc chính của bình luận mạng xã hội",
}


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip().lower()


def build_prompt(tok, task: str, labels: list[str], text: str, shots: list[tuple[str, str]]) -> str:
    sys_msg = (f"Bạn là bộ phân loại {DESC[task]}. Chỉ trả lời đúng MỘT nhãn trong danh sách: "
               + ", ".join(labels) + ". Không giải thích.")
    msgs = [{"role": "system", "content": sys_msg}]
    for t, lab in shots:
        msgs += [{"role": "user", "content": f"Câu: {t}\nNhãn:"}, {"role": "assistant", "content": lab}]
    msgs.append({"role": "user", "content": f"Câu: {text}\nNhãn:"})
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def parse(output: str, labels: list[str], fallback: str) -> tuple[str, bool]:
    o = norm(output)
    for lab in sorted(labels, key=len, reverse=True):  # nhãn dài trước để "Trung tính" không bị nuốt bởi nhãn ngắn
        if norm(lab) in o:
            return lab, True
    return fallback, False


def run() -> None:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    tok.padding_side = "left"
    llm = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16 if device == "cuda" else torch.float32).to(device).eval()
    rows, findings, samples = [], [], {}
    for task in ("sentiment", "emotion"):
        test, train = load_split(task, "test"), load_split(task, "train")
        labels = sorted(train["label"].unique())
        # lấy mẫu phân tầng (pandas 3.x: groupby.apply bỏ cột nhóm -> ghép tường minh từng nhãn)
        sample = pd.concat([test[test["label"] == lab].sample(min((test["label"] == lab).sum(), PER_LABEL[task]), random_state=42)
                            for lab in labels], ignore_index=True)
        shots = [(train[train["label"] == lab]["clean_text"].sample(1, random_state=1).iloc[0], lab) for lab in labels]
        truth = sample["label"].tolist()
        task_name = "Quan điểm (VSFC)" if task == "sentiment" else "Cảm xúc (VSMEC)"
        majority = sample["label"].value_counts().idxmax()
        for mode, sh in (("zero-shot", []), ("few-shot (1 ví dụ/nhãn)", shots)):
            preds, parsed_ok, t0 = [], 0, time.time()
            for i in range(0, len(sample), BATCH):
                prompts = [build_prompt(tok, task, labels, t, sh) for t in sample["clean_text"].iloc[i:i + BATCH]]
                enc = tok(prompts, return_tensors="pt", padding=True).to(device)
                with torch.no_grad():
                    gen = llm.generate(**enc, max_new_tokens=8, do_sample=False, pad_token_id=tok.eos_token_id)
                for g in gen[:, enc["input_ids"].shape[1]:]:
                    lab, ok = parse(tok.decode(g, skip_special_tokens=True), labels, majority)
                    preds.append(lab)
                    parsed_ok += ok
            m = evaluate(truth, preds, labels)
            rows.append({"Bài toán": task_name, "Phương pháp": f"Qwen2.5-1.5B {mode}", "Số câu": len(sample),
                         "Accuracy": r4(m["accuracy"]), "F1-macro": r4(m["f1_macro"]), "Trả lời đúng định dạng": f"{parsed_ok / len(sample):.0%}",
                         "Giây/câu": round((time.time() - t0) / len(sample), 3)})
            print(rows[-1])
        samples[task] = (task_name, sample, truth, labels)
    # giải phóng LLM trước khi nạp mô hình fine-tune (16GB RAM không đủ giữ cả hai -> lỗi "paging file is too small")
    del llm
    gc.collect()
    torch.cuda.empty_cache()
    for task, (task_name, sample, truth, labels) in samples.items():
        sel = load_selected(task)
        t0 = time.time()
        p = [lab for lab, _ in sel.predict(sample["clean_text"].tolist())]
        m = evaluate(truth, p, labels)
        rows.append({"Bài toán": task_name, "Phương pháp": f"{sel.model_key} đã fine-tune (đang dùng)", "Số câu": len(sample),
                     "Accuracy": r4(m["accuracy"]), "F1-macro": r4(m["f1_macro"]), "Trả lời đúng định dạng": "100%",
                     "Giây/câu": round((time.time() - t0) / len(sample), 4)})
        print(rows[-1])
        del sel
        gc.collect()
        torch.cuda.empty_cache()
    for task_name in ("Quan điểm (VSFC)", "Cảm xúc (VSMEC)"):
        r = [x for x in rows if x["Bài toán"] == task_name]
        llm_rows = [x for x in r if x["Phương pháp"].startswith("Qwen")]
        ft = next(x for x in r if not x["Phương pháp"].startswith("Qwen"))
        best_llm = max(llm_rows, key=lambda x: x["F1-macro"])
        findings.append(f"{task_name}: LLM tốt nhất ({best_llm['Phương pháp']}) F1-macro {best_llm['F1-macro']} so với mô hình fine-tune {ft['F1-macro']} "
                        f"trên cùng {ft['Số câu']} câu; LLM chậm hơn khoảng {best_llm['Giây/câu'] / max(ft['Giây/câu'], 1e-4):.0f} lần.")
    findings.append("Mẫu được lấy cân bằng theo nhãn nên F1-macro ở đây không so trực tiếp được với R-xx (đo trên toàn bộ tập test lệch lớp).")
    findings.append("Chỉ thử LLM 1.5B (giới hạn GPU 4GB); LLM lớn hơn có thể tốt hơn nhưng cần phần cứng mạnh hơn hoặc gửi dữ liệu ra dịch vụ ngoài (rủi ro quyền riêng tư).")
    save_result("llm", "LLM zero-shot / few-shot so với mô hình fine-tune", "CH1 - so sánh kỹ thuật (T-40)",
                f"{MODEL} chạy cục bộ fp16, sinh tối đa 8 token, giải mã tham lam. Mẫu phân tầng tập test (tối đa {PER_LABEL['sentiment']} câu/nhãn quan điểm, "
                f"{PER_LABEL['emotion']} câu/nhãn cảm xúc). Câu trả lời không khớp nhãn nào được gán nhãn đa số của mẫu.",
                [{"title": "So sánh trên cùng mẫu", "columns": list(rows[0].keys()), "rows": rows}], findings)


if __name__ == "__main__":
    pd.options.mode.chained_assignment = None
    run()
