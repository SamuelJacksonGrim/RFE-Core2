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

The collator feeds the encoder the context only. One label slot, after the
stem, holds the mode filler's content-vocab index; every stem position and
every pad is IGNORE_INDEX. The training loss is still the soft distribution
on that row, not a hard label and not one example per raw count.
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
# Stem positions and pad. One post-stem slot holds the mode filler.
IGNORE_INDEX = -100


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


def mode_filler(row: dict) -> str:
    """Highest-count target. Ties break lexicographically, not by expanding counts."""
    counts = row.get("targets")
    if counts:
        best = max(counts.values())
        words = [w for w, c in counts.items() if c == best and c > 0]
    else:
        dist = row["target_dist"]
        best = max(dist.values())
        words = [w for w, p in dist.items() if p == best and p > 0]
    if not words:
        raise ValueError("empty target distribution")
    return sorted(words)[0]


def support_ids(row: dict, index: Dict[str, int]) -> List[int]:
    counts = row.get("targets")
    if counts:
        words = [w for w, c in counts.items() if c > 0]
    else:
        words = [w for w, p in row["target_dist"].items() if p > 0]
    ids: List[int] = []
    for word in words:
        j = index.get(word)
        if j is None:
            raise KeyError(f"target {word!r} is not in the completion vocabulary")
        ids.append(int(j))
    if not ids:
        raise ValueError("empty target support")
    return ids


@dataclass
class CompletionBatch:
    """One collated step. `contexts` is the encoder input; the filler is absent."""

    contexts: List[List[str]]
    labels: torch.Tensor
    stem_lengths: torch.Tensor
    target_p: torch.Tensor
    rhythm_ids: torch.Tensor
    support_ids: List[List[int]]


class CompletionCollator:
    """Context-only batches. Labels supervise one mode-filler slot, not the stem."""

    def __init__(self, index: Dict[str, int], rhythm_index: Dict[str, int], device: str):
        self.index = index
        self.rhythm_index = rhythm_index
        self.device = device

    def __call__(self, rows: Sequence[dict]) -> CompletionBatch:
        if not rows:
            raise ValueError("empty completion batch")
        contexts = [list(row["context"]) for row in rows]
        if any(not ctx for ctx in contexts):
            raise ValueError("empty completion context")
        lengths = [len(ctx) for ctx in contexts]
        # The extra column is the supervised slot. It is not an encoder input.
        width = max(lengths) + 1
        labels = torch.full(
            (len(rows), width), IGNORE_INDEX, dtype=torch.long, device=self.device,
        )
        supports: List[List[int]] = []
        for i, row in enumerate(rows):
            word = mode_filler(row)
            if word in contexts[i]:
                raise ValueError(f"filler {word!r} is in the context")
            j = self.index.get(word)
            if j is None:
                raise KeyError(f"target {word!r} is not in the completion vocabulary")
            labels[i, lengths[i]] = int(j)
            supports.append(support_ids(row, self.index))
        target_p = pack_targets(
            [row["target_dist"] for row in rows], self.index, self.device,
        )
        rhythm_ids = torch.tensor(
            [self.rhythm_index[row["rhythm"]] for row in rows],
            dtype=torch.long,
            device=self.device,
        )
        return CompletionBatch(
            contexts=contexts,
            labels=labels,
            stem_lengths=torch.tensor(lengths, dtype=torch.long, device=self.device),
            target_p=target_p,
            rhythm_ids=rhythm_ids,
            support_ids=supports,
        )


def filler_ids_from_labels(labels: torch.Tensor) -> torch.Tensor:
    """Class id at the only non-ignored position. Refuses any other pattern."""
    if labels.ndim != 2:
        raise ValueError(f"labels must be (N, L), got {tuple(labels.shape)}")
    supervised = labels != IGNORE_INDEX
    counts = supervised.sum(dim=1)
    expected = torch.ones(labels.shape[0], dtype=counts.dtype, device=counts.device)
    if not torch.equal(counts, expected):
        bad = (counts != 1).nonzero(as_tuple=False).flatten().tolist()
        raise ValueError(
            "each completion row must have exactly one supervised position, "
            f"got counts {counts[bad[:8]].tolist()} at rows {bad[:8]}"
        )
    position = supervised.to(torch.int64).argmax(dim=1)
    return labels.gather(1, position.unsqueeze(1)).squeeze(1)


def assert_completion_mask(
    labels: torch.Tensor,
    stem_lengths: torch.Tensor,
    support: Sequence[Sequence[int]],
    filler_ids: torch.Tensor,
) -> None:
    """Refuse a stem label, a pad label, or a filler outside that row's support.

    The supervised slot is the position just after the stem. Pad and stem stay
    IGNORE_INDEX. `filler_ids` is the gather from `filler_ids_from_labels`.
    """
    if labels.ndim != 2:
        raise ValueError(f"labels must be (N, L), got {tuple(labels.shape)}")
    n, length = labels.shape
    if stem_lengths.shape != (n,) or filler_ids.shape != (n,):
        raise ValueError("completion batch fields disagree on the row count")
    if len(support) != n:
        raise ValueError("completion batch fields disagree on the row count")
    device = labels.device
    stem_lengths = stem_lengths.to(device=device, dtype=torch.long)
    filler_ids = filler_ids.to(device=device)
    if bool((stem_lengths < 0).any()) or bool((stem_lengths >= length).any()):
        raise ValueError("stem length does not leave exactly one supervised slot")
    pos = torch.arange(length, device=device).unsqueeze(0)
    stem = pos < stem_lengths.unsqueeze(1)
    pad = pos > stem_lengths.unsqueeze(1)
    if bool((stem & (labels != IGNORE_INDEX)).any()):
        raise ValueError("stem position was given a supervised id")
    if bool((pad & (labels != IGNORE_INDEX)).any()):
        raise ValueError("pad position was given a supervised id")
    at_slot = labels.gather(1, stem_lengths.unsqueeze(1)).squeeze(1)
    if bool((at_slot == IGNORE_INDEX).any()):
        raise ValueError("a row has no supervised position")
    if not torch.equal(at_slot, filler_ids):
        raise ValueError("gathered filler id is not the post-stem label")
    for i in range(n):
        fid = int(filler_ids[i])
        if fid not in support[i]:
            raise ValueError(
                f"gathered filler id {fid} is not in row {i} target support"
            )


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

        collator = CompletionCollator(self.head.index, rhythm_index, device)

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
                packed = collator([rows[i] for i in batch_ix])
                # Load-bearing mask. A stem label, a bad slot count, or a
                # filler outside the support refuses the batch before the step.
                filler_ids = filler_ids_from_labels(packed.labels)
                assert_completion_mask(
                    packed.labels, packed.stem_lengths, packed.support_ids, filler_ids,
                )
                token_lists = packed.contexts
                rhythm_ids = packed.rhythm_ids
                target_p = packed.target_p

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

                n = len(token_lists)
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
