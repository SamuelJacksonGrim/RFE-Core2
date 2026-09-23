"""
training/completion.py

Context -> completion pretraining for the rhythm encoder.

The rhythm-contrastive loss is minimized by one centroid per rhythm. That is
why the holdout cloud sits at participation ~4 at both 128 and 256: four
directions realize five cones, and extra ambient axes stay unused.

This objective is CBOW. The encoder mean-pools a context; a linear head
reads that vector and places a distribution over the held-out word. A
full-vocabulary softmax can realize only as many distinct distributions as
the context vectors can separate, and the completion corpus has thousands
of distinct context -> word distributions. Five centroids cannot fit it.

Rhythm is a condition, not the target. A learned rhythm code is added at a
fixed small scale (0.25) after the pool, so it can reweight a completion
but cannot replace the context. A second, lighter term reads the rhythm
back off the context vector itself (before the code is added), so routing
is still in the field vector. Its weight is 0.15: at chance the word loss
is ln(|V|) ~ 6.5 nats and the rhythm loss is ln(5) ~ 1.6, so the word term
leads by more than an order of magnitude.

Mean-pool is unchanged. Order is not a feature of this objective.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from training.encode import encode_grad

logger = logging.getLogger(__name__)

# Fixed. A learned scale can grow until the rhythm code solves every
# shared stem and the context vector is free to collapse.
COND_SCALE = 0.25
RHYTHM_LOSS_WEIGHT = 0.15


@dataclass
class CompletionConfig:
    n_epochs: int = 20
    batch_size: int = 128
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    rhythm_weight: float = RHYTHM_LOSS_WEIGHT
    cond_scale: float = COND_SCALE
    grad_clip: float = 1.0
    log_interval: int = 1


@dataclass
class CompletionReport:
    epochs: int
    final_loss: float
    final_word_ce: float
    final_rhythm_acc: float
    loss_history: List[float] = field(default_factory=list)
    word_ce_history: List[float] = field(default_factory=list)
    rhythm_acc_history: List[float] = field(default_factory=list)


class CompletionHead(nn.Module):
    """Linear CBOW head + rhythm code + rhythm probe. Not part of the field."""

    def __init__(self, vocab: Sequence[str], dim: int, n_rhythms: int, device: str):
        super().__init__()
        self.vocab: List[str] = list(vocab)
        self.index: Dict[str, int] = {t: i for i, t in enumerate(self.vocab)}
        self.head = nn.Linear(dim, len(self.vocab))
        self.rhythm_embed = nn.Embedding(n_rhythms, dim)
        self.rhythm_probe = nn.Linear(dim, n_rhythms)
        nn.init.xavier_uniform_(self.head.weight)
        nn.init.zeros_(self.head.bias)
        nn.init.normal_(self.rhythm_embed.weight, std=0.02)
        nn.init.xavier_uniform_(self.rhythm_probe.weight)
        nn.init.zeros_(self.rhythm_probe.bias)
        self.to(device)

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)


def pack_targets(
    dists: Sequence[Dict[str, float]],
    index: Dict[str, int],
    device: str,
) -> torch.Tensor:
    """Dense rows that sum to 1. Unknown target words are a builder bug."""
    rows = torch.zeros(len(dists), len(index), device=device)
    for i, dist in enumerate(dists):
        for word, prob in dist.items():
            j = index.get(word)
            if j is None:
                raise KeyError(f"target {word!r} is not in the completion vocabulary")
            rows[i, j] = float(prob)
        total = rows[i].sum()
        if total <= 0:
            raise ValueError("empty target distribution")
        rows[i] /= total
    return rows


def completion_loss(
    logits: torch.Tensor,
    target_p: torch.Tensor,
    rhythm_logits: torch.Tensor,
    rhythm_ids: torch.Tensor,
    rhythm_weight: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Soft cross-entropy on the completion, plus a light rhythm CE on h.

    Returns (total, per-example word CE, per-example rhythm CE). The word
    term is -sum_w p(w|context, rhythm) log q(w). One-hot rows are ordinary
    CBOW; multi-word rows are the rhythm-weighted filler distribution.
    """
    log_q = F.log_softmax(logits, dim=-1)
    word = -(target_p * log_q).sum(dim=-1)
    rhythm = F.cross_entropy(rhythm_logits, rhythm_ids, reduction="none")
    total = word.mean() + rhythm_weight * rhythm.mean()
    return total, word, rhythm


class CompletionTrainer:
    """Train generator + head. The generator checkpoint stays a plain encoder."""

    def __init__(self, generator, head: CompletionHead, config: CompletionConfig | None = None):
        self.generator = generator
        self.head = head
        self.config = config or CompletionConfig()
        params = [
            p for p in list(generator.parameters()) + list(head.parameters())
            if p.requires_grad
        ]
        self.optimizer = torch.optim.AdamW(
            params,
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

    def _forward(self, token_lists: List[List[str]], rhythm_ids: torch.Tensor):
        h = encode_grad(self.generator, token_lists)
        code = F.normalize(self.head.rhythm_embed(rhythm_ids), dim=-1)
        conditioned = F.normalize(h + self.config.cond_scale * code, dim=-1)
        return h, self.head.head(conditioned), self.head.rhythm_probe(h)

    def pretrain(
        self,
        rows: List[dict],
        rhythm_index: Dict[str, int],
        on_epoch_end=None,
    ) -> CompletionReport:
        cfg = self.config
        device = self.generator.device
        loss_history: List[float] = []
        word_history: List[float] = []
        acc_history: List[float] = []

        logger.info(
            "completion pretrain: %d rows, %d epochs, batch %d, |V|=%d",
            len(rows), cfg.n_epochs, cfg.batch_size, self.head.vocab_size,
        )

        for epoch in range(cfg.n_epochs):
            self.generator.train()
            self.head.train()
            order = torch.randperm(len(rows)).tolist()
            total_loss = 0.0
            total_word = 0.0
            correct = 0
            seen = 0

            for start in range(0, len(rows), cfg.batch_size):
                batch_ix = order[start:start + cfg.batch_size]
                batch = [rows[i] for i in batch_ix]
                token_lists = [r["context"] for r in batch]
                rhythm_ids = torch.tensor(
                    [rhythm_index[r["rhythm"]] for r in batch],
                    dtype=torch.long,
                    device=device,
                )
                dists = [r["target_dist"] for r in batch]
                target_p = pack_targets(dists, self.head.index, device)

                _h, logits, rhythm_logits = self._forward(token_lists, rhythm_ids)
                loss, word, rhythm = completion_loss(
                    logits, target_p, rhythm_logits, rhythm_ids, cfg.rhythm_weight,
                )
                if not torch.isfinite(loss):
                    raise RuntimeError(f"non-finite completion loss at epoch {epoch}")

                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    list(self.generator.parameters()) + list(self.head.parameters()),
                    cfg.grad_clip,
                )
                self.optimizer.step()

                n = len(batch)
                total_loss += float(loss.detach()) * n
                total_word += float(word.detach().mean()) * n
                correct += int((rhythm_logits.argmax(-1) == rhythm_ids).sum().detach())
                seen += n

            mean_loss = total_loss / max(seen, 1)
            mean_word = total_word / max(seen, 1)
            acc = correct / max(seen, 1)
            loss_history.append(mean_loss)
            word_history.append(mean_word)
            acc_history.append(acc)
            if (epoch + 1) % cfg.log_interval == 0:
                logger.info(
                    "epoch %d/%d  loss=%.4f  word_ce=%.4f  rhythm_acc=%.3f",
                    epoch + 1, cfg.n_epochs, mean_loss, mean_word, acc,
                )
            if on_epoch_end is not None and (
                epoch + 1 == cfg.n_epochs or (epoch + 1) % 5 == 0
            ):
                on_epoch_end(epoch + 1)

        self.generator.eval()
        self.head.eval()
        return CompletionReport(
            epochs=cfg.n_epochs,
            final_loss=round(loss_history[-1] if loss_history else 0.0, 6),
            final_word_ce=round(word_history[-1] if word_history else 0.0, 6),
            final_rhythm_acc=round(acc_history[-1] if acc_history else 0.0, 4),
            loss_history=[round(x, 6) for x in loss_history],
            word_ce_history=[round(x, 6) for x in word_history],
            rhythm_acc_history=[round(x, 4) for x in acc_history],
        )
