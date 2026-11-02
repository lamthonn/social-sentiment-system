"""BiLSTM phân loại văn bản (M-06, nhóm học sâu theo thuyết minh mục 6.5).

Đơn vị là âm tiết/emoji/dấu câu sau làm sạch; embedding học từ đầu (không dùng word2vec ngoài)."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import torch
from torch import nn

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
PAD, UNK = 0, 1


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


class Vocab:
    def __init__(self, itos: list[str]):
        self.itos = itos
        self.stoi = {w: i for i, w in enumerate(itos)}

    @classmethod
    def build(cls, texts, min_freq: int = 2, max_size: int = 30000) -> "Vocab":
        c = Counter(tok for t in texts for tok in tokenize(t))
        words = [w for w, n in c.most_common(max_size) if n >= min_freq]
        return cls(["<pad>", "<unk>", *words])

    def encode(self, text: str, max_len: int) -> list[int]:
        return [self.stoi.get(t, UNK) for t in tokenize(text)][:max_len] or [UNK]


class BiLSTMClassifier(nn.Module):
    def __init__(self, vocab_size: int, num_labels: int, emb: int = 200, hidden: int = 128, dropout: float = 0.3):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, emb, padding_idx=PAD)
        self.lstm = nn.LSTM(emb, hidden, batch_first=True, bidirectional=True)
        self.drop = nn.Dropout(dropout)
        self.out = nn.Linear(hidden * 2, num_labels)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        mask = (ids != PAD).unsqueeze(-1)
        h, _ = self.lstm(self.drop(self.emb(ids)))
        h = h.masked_fill(~mask, -1e4).max(dim=1).values  # max-pooling theo thời gian
        return self.out(self.drop(h))


def pad_batch(seqs: list[list[int]]) -> torch.Tensor:
    width = max(len(s) for s in seqs)
    out = torch.full((len(seqs), width), PAD, dtype=torch.long)
    for i, s in enumerate(seqs):
        out[i, : len(s)] = torch.tensor(s)
    return out


def save(model: BiLSTMClassifier, vocab: Vocab, labels: list[str], cfg: dict, out: Path) -> None:
    torch.save(model.state_dict(), out / "bilstm.pt")
    (out / "bilstm.json").write_text(json.dumps({"itos": vocab.itos, "labels": labels, **cfg}, ensure_ascii=False), encoding="utf-8")


def load(path: Path, device: str) -> tuple[BiLSTMClassifier, Vocab, list[str], dict]:
    meta = json.loads((path / "bilstm.json").read_text(encoding="utf-8"))
    vocab = Vocab(meta["itos"])
    model = BiLSTMClassifier(len(vocab.itos), len(meta["labels"]), meta["emb"], meta["hidden"], meta["dropout"])
    model.load_state_dict(torch.load(path / "bilstm.pt", map_location=device))
    return model.to(device).eval(), vocab, meta["labels"], meta
