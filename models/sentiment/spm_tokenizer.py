"""Tokenizer cho ViSoBERT (uitnlp/visobert) đọc thẳng file sentencepiece.

Lý do: kho uitnlp/visobert không có tokenizer_config.json, và transformers 5.x dựng
XLMRobertaTokenizer từ file này thành toàn <unk> (đã kiểm tra) -> mô hình học trên rác mà
không báo lỗi. Quy ước id theo XLM-RoBERTa/fairseq: <s>=0, <pad>=1, </s>=2, <unk>=3,
mảnh từ = id sentencepiece + 1 (id sentencepiece 0 là <unk> -> 3).
"""
from __future__ import annotations

import shutil
from pathlib import Path

SPM_FILE = "sentencepiece.bpe.model"
BOS, PAD, EOS, UNK, OFFSET = 0, 1, 2, 3, 1


class SpmXlmrTokenizer:
    def __init__(self, spm_path: str | Path):
        import sentencepiece as spm

        self.spm_path = Path(spm_path)
        self.sp = spm.SentencePieceProcessor(model_file=str(self.spm_path))

    @classmethod
    def from_pretrained(cls, name_or_dir: str | Path) -> "SpmXlmrTokenizer":
        local = Path(name_or_dir) / SPM_FILE
        if local.exists():
            return cls(local)
        from huggingface_hub import hf_hub_download
        return cls(hf_hub_download(str(name_or_dir), SPM_FILE))

    def save_pretrained(self, out_dir: str | Path) -> None:
        shutil.copy(self.spm_path, Path(out_dir) / SPM_FILE)

    def encode(self, text: str, max_length: int = 128) -> list[int]:
        ids = [i + OFFSET if i != 0 else UNK for i in self.sp.encode(text)]
        return [BOS] + ids[: max_length - 2] + [EOS]

    def tokens(self, text: str) -> list[str]:
        return self.sp.encode(text, out_type=str)

    def __call__(self, texts: list[str], truncation: bool = True, max_length: int = 128, padding: bool = True, return_tensors: str = "pt"):
        import torch

        seqs = [self.encode(t, max_length) for t in texts]
        width = max(len(s) for s in seqs)
        ids = torch.full((len(seqs), width), PAD, dtype=torch.long)
        mask = torch.zeros((len(seqs), width), dtype=torch.long)
        for i, s in enumerate(seqs):
            ids[i, : len(s)] = torch.tensor(s)
            mask[i, : len(s)] = 1
        return _Batch(input_ids=ids, attention_mask=mask)


class _Batch(dict):
    def to(self, device):
        return _Batch({k: v.to(device) for k, v in self.items()})
