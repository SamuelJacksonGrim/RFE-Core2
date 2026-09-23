"""
training/legibility.py

Cone-bounded legibility — grow the frozen 5-rhythm encoder so a thought is
recoverable *inside* its rhythm cone.

The rhythm objective (training/rhythm_pretraining.py, supervised contrastive)
and the live contrastive aligner (training/contrastive_alignment.py) both
train one thing: same-rhythm cosine high, cross-rhythm cosine low. That is
why within-rhythm cosine sits at 0.94–0.97. The collapse is the objective,
not a broken pool. This module ADDS the objective those passes never had:
within a cone, cosine should track token-set overlap. It does not rerun the
rhythm losses, and it does not touch the field, the loop, or resonance memory.

Four terms, one representation (the existing mean-pooled, L2-normalized vector):

  margin     cos(z, own frozen centroid) - max_{other} cos(z, other)  >= δ
             A wall, not a pull. Inactive while the cone still has room.
             This is what keeps attractor routing and nearest-centroid
             rhythm membership intact. It is NOT a field-lock lever — the
             lock is the reflective loop (STATE.md) and is not in this graph.

  centroid   Batch mean of a rhythm stays aligned with the FROZEN centroid.
             The gradient is identical for every point in the rhythm, so it
             translates the cloud and does not shrink it. Basins stay where
             RM / attractors were calibrated; points may move inside them.

  jaccard    Within-rhythm pairs only. Disjoint bags are pushed down toward
             tau_pair; near-duplicate bags stay up at tau_same. Cross-rhythm
             pairs are not in this term — separation across cones is the
             margin's job, and re-pulling same-rhythm pairs together is how
             the old objective erased words.

  rank       Auxiliary linear head, sampled softmax over the true tokens.
             Discarded after the fit. It pins WHICH tangent direction means
             which word; jaccard alone only preserves distances. The mouth
             that gets reported is a fresh TokenDecoder trained the Phase 0
             way, so this head cannot inflate the yardstick.

Orphan rows (corpus tokens with no ecology entry, still at init) get no
special parameter. Sequences that contain one are upweighted on the rank
term, and the embedding row receives gradient through the ordinary forward.
Trained rows are not reinitialized.

Dropout stays off for the whole fit (generator.eval()). The deployed encoder
is the eval-mode function — dropout noise was measured as fake diversity
(2026-06-08) and eval-mode is the graduated lever. Gradients still flow.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from training.corpus import RHYTHMS
from training.encode import encode_grad


RUPTURE_ID = RHYTHMS.index("rupture")


@dataclass
class LegibilityConfig:
    """Weights and thresholds for one growth fit. See the module docstring."""

    margin: float = 0.20
    tau_pair: float = 0.70
    tau_same: float = 0.98
    pull_jaccard: float = 0.80
    pull_weight: float = 0.25
    rupture_weight: float = 3.0
    orphan_weight: float = 2.0
    w_margin: float = 4.0
    w_centroid: float = 2.0
    w_jaccard: float = 2.0
    w_rank: float = 1.0
    rank_negatives: int = 48
    lr: float = 3e-4
    head_lr: float = 1e-3
    weight_decay: float = 0.0
    epochs: int = 8
    per_rhythm: int = 32
    grad_clip: float = 1.0
    rupture_id: int = RUPTURE_ID


def legibility_losses(
    z: torch.Tensor,
    rhythm_ids: torch.Tensor,
    pos_idx: torch.Tensor,
    pos_mask: torch.Tensor,
    multi_hot: torch.Tensor,
    centroids: torch.Tensor,
    head: nn.Module,
    row_weight: torch.Tensor,
    cfg: LegibilityConfig,
) -> Dict[str, torch.Tensor]:
    """
    Component losses on one batch.

    z is (n, dim), already L2-normalized, and must stay in the graph.
    centroids is (n_rhythms, dim), frozen, unit, detached.
    pos_idx / pos_mask describe the true tokens (n, P).
    multi_hot is (n, vocab) float, used only for the jaccard term.
    row_weight is (n,) — rupture and orphan upweight, already combined.
    """
    n = z.shape[0]
    device = z.device
    zero = z.new_zeros(())

    # --- margin wall (per point, against frozen centroids) ---
    sim_c = z @ centroids.T
    own = sim_c[torch.arange(n, device=device), rhythm_ids]
    others = sim_c.clone()
    others[torch.arange(n, device=device), rhythm_ids] = -2.0
    gap = own - others.max(dim=1).values
    margin = F.relu(cfg.margin - gap).mean() if cfg.w_margin else zero

    # --- centroid anchor (same gradient for every point in a rhythm) ---
    if cfg.w_centroid:
        anchor = zero
        seen = 0
        for r in rhythm_ids.unique().tolist():
            m = rhythm_ids == int(r)
            if int(m.sum()) < 1:
                continue
            c = F.normalize(z[m].mean(dim=0), dim=0)
            anchor = anchor + (1.0 - torch.dot(c, centroids[int(r)]))
            seen += 1
        anchor = anchor / max(seen, 1)
    else:
        anchor = zero

    # --- within-rhythm jaccard spread ---
    if cfg.w_jaccard and n >= 2:
        jaccard = _jaccard_spread(z, rhythm_ids, multi_hot, cfg)
    else:
        jaccard = zero

    # --- auxiliary token rank (linear head; not the reported mouth) ---
    if cfg.w_rank:
        logits = head(z)
        rank = _sampled_rank(logits, pos_idx, pos_mask, row_weight, cfg.rank_negatives)
        rank = rank / math.log(cfg.rank_negatives + 1)
    else:
        rank = zero

    total = (
        cfg.w_margin * margin
        + cfg.w_centroid * anchor
        + cfg.w_jaccard * jaccard
        + cfg.w_rank * rank
    )
    return {
        "total": total,
        "margin": margin,
        "centroid": anchor,
        "jaccard": jaccard,
        "rank": rank,
        "gap": gap.detach(),
    }


def _jaccard_spread(
    z: torch.Tensor,
    rhythm_ids: torch.Tensor,
    multi_hot: torch.Tensor,
    cfg: LegibilityConfig,
) -> torch.Tensor:
    """Push disjoint same-rhythm bags apart; keep near-copies together.

    Cross-rhythm pairs are excluded. Computed per rhythm so a batch that is
    only a few dozen per cone stays cheap, and so rupture can be reweighted
    without touching the other cones' pair counts.
    """
    loss = z.new_zeros(())
    weight = z.new_zeros(())
    for r in rhythm_ids.unique().tolist():
        m = rhythm_ids == int(r)
        if int(m.sum()) < 2:
            continue
        zr = z[m]
        yr = multi_hot[m]
        sim = zr @ zr.T
        inter = yr @ yr.T
        sizes = yr.sum(dim=1, keepdim=True)
        union = (sizes + sizes.T - inter).clamp(min=1.0)
        jac = inter / union
        target = cfg.tau_pair + (cfg.tau_same - cfg.tau_pair) * jac
        gap = sim - target
        push = F.relu(gap)
        pull = F.relu(-gap) * (jac >= cfg.pull_jaccard).to(z.dtype)
        per = push + cfg.pull_weight * pull
        tri = torch.triu(
            torch.ones(per.shape[0], per.shape[0], device=z.device, dtype=z.dtype),
            diagonal=1,
        )
        w = cfg.rupture_weight if int(r) == cfg.rupture_id else 1.0
        loss = loss + (per * tri).sum() * w
        weight = weight + tri.sum() * w
    if float(weight.detach()) <= 0.0:
        return z.new_zeros(())
    return loss / weight


def _sampled_rank(
    logits: torch.Tensor,
    pos_idx: torch.Tensor,
    pos_mask: torch.Tensor,
    row_weight: torch.Tensor,
    n_neg: int,
) -> torch.Tensor:
    """Mean log-prob of each true token against K random negatives.

    One shared negative draw per row. Collisions with a true token are masked
    out of the softmax. At most P vectorized passes, P = sequence length (<=4
    on this corpus), so a full-epoch batch stays on CPU without a Python loop
    over tokens.
    """
    n, vocab = logits.shape
    if pos_mask.sum() == 0:
        return logits.new_zeros(())
    neg = torch.randint(0, vocab, (n, n_neg), device=logits.device)
    neg_logits = logits.gather(1, neg)
    for p in range(pos_idx.shape[1]):
        clash = neg.eq(pos_idx[:, p:p + 1]) & pos_mask[:, p:p + 1]
        neg_logits = neg_logits.masked_fill(clash, -1e9)

    total = logits.new_zeros(())
    denom = logits.new_zeros(())
    for p in range(pos_idx.shape[1]):
        m = pos_mask[:, p]
        if not bool(m.any()):
            continue
        pos_logit = logits[m, pos_idx[m, p]].unsqueeze(1)
        row = torch.cat([pos_logit, neg_logits[m]], dim=1)
        nll = -F.log_softmax(row, dim=1)[:, 0]
        w = row_weight[m]
        total = total + (nll * w).sum()
        denom = denom + w.sum()
    return total / denom.clamp(min=1.0)


def pack_positives(
    token_lists: Sequence[Sequence[str]],
    token_index: Dict[str, int],
    max_p: int,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """(pos_idx, pos_mask, multi_hot) for a batch. Unknown tokens are skipped."""
    n = len(token_lists)
    v = len(token_index)
    pos_idx = torch.zeros(n, max_p, dtype=torch.long)
    pos_mask = torch.zeros(n, max_p, dtype=torch.bool)
    multi_hot = torch.zeros(n, v, dtype=torch.float32)
    for i, toks in enumerate(token_lists):
        p = 0
        seen = set()
        for t in toks:
            j = token_index.get(t)
            if j is None or j in seen:
                continue
            multi_hot[i, j] = 1.0
            seen.add(j)
            if p < max_p:
                pos_idx[i, p] = j
                pos_mask[i, p] = True
                p += 1
    return pos_idx, pos_mask, multi_hot


def row_weights(
    rhythm_ids: torch.Tensor,
    orphan: torch.Tensor,
    cfg: LegibilityConfig,
) -> torch.Tensor:
    """Per-sequence rank weight. Margin and centroid are NOT scaled by this."""
    w = torch.ones(rhythm_ids.shape[0], dtype=torch.float32)
    w = torch.where(rhythm_ids == cfg.rupture_id, w * cfg.rupture_weight, w)
    w = torch.where(orphan, w * cfg.orphan_weight, w)
    return w


def iter_stratified(
    records: Sequence[dict],
    per_rhythm: int,
    rng: np.random.Generator,
) -> Iterable[List[int]]:
    """Yield index batches with up to `per_rhythm` sequences from each rhythm.

    Smaller rhythms wrap across batches (rupture is the small one; seeing it
    more often is intentional). A window never duplicates inside one batch.
    """
    by: Dict[str, List[int]] = {r: [] for r in RHYTHMS}
    for i, rec in enumerate(records):
        by[rec["rhythm"]].append(i)
    for r in RHYTHMS:
        rng.shuffle(by[r])
    usable = [len(v) for v in by.values() if v]
    if not usable:
        return
    longest = max(usable)
    n_batches = max(1, math.ceil(longest / max(per_rhythm, 1)))
    for b in range(n_batches):
        chosen: List[int] = []
        for r in RHYTHMS:
            idxs = by[r]
            n = len(idxs)
            if n == 0:
                continue
            if per_rhythm >= n:
                chosen.extend(idxs)
                continue
            start = (b * per_rhythm) % n
            chosen.extend(idxs[(start + k) % n] for k in range(per_rhythm))
        if len(chosen) >= 2:
            yield chosen


def fit_encoder(
    generator,
    records: Sequence[dict],
    centroids: torch.Tensor,
    token_index: Dict[str, int],
    cfg: Optional[LegibilityConfig] = None,
    log=print,
) -> dict:
    """
    Grow `generator` in place from its current weights.

    records: {tokens, rhythm, orphan}. orphan is a bool.
    centroids: (5, dim) frozen unit centroids on the same device as generator.
    The linear head created here is a scaffold. Callers that report a mouth
    must train a fresh TokenDecoder afterwards.
    """
    cfg = cfg or LegibilityConfig()
    device = generator.device
    centroids = centroids.detach().to(device)
    was_training = generator.training
    # Eval-mode fit: dropout off, matching the function the field actually reads.
    generator.eval()

    vocab = len(token_index)
    max_p = max((len(set(r["tokens"])) for r in records), default=1)
    max_p = max(max_p, 1)
    head = nn.Linear(generator.dim, vocab).to(device)
    opt = torch.optim.AdamW(
        [
            {"params": list(generator.parameters()), "lr": cfg.lr},
            {"params": list(head.parameters()), "lr": cfg.head_lr},
        ],
        weight_decay=cfg.weight_decay,
    )
    rng = np.random.default_rng(42)
    history = []

    for epoch in range(cfg.epochs):
        totals = {k: 0.0 for k in ("total", "margin", "centroid", "jaccard", "rank")}
        gaps = []
        steps = 0
        for chosen in iter_stratified(records, cfg.per_rhythm, rng):
            batch = [records[i] for i in chosen]
            tokens = [r["tokens"] for r in batch]
            rhythm_ids = torch.tensor(
                [RHYTHMS.index(r["rhythm"]) for r in batch],
                dtype=torch.long, device=device,
            )
            orphan = torch.tensor(
                [bool(r.get("orphan", False)) for r in batch],
                dtype=torch.bool, device=device,
            )
            pos_idx, pos_mask, multi_hot = pack_positives(tokens, token_index, max_p)
            pos_idx = pos_idx.to(device)
            pos_mask = pos_mask.to(device)
            multi_hot = multi_hot.to(device)
            weights = row_weights(rhythm_ids.cpu(), orphan.cpu(), cfg).to(device)

            z = encode_grad(generator, tokens)
            z = F.normalize(z, dim=-1)
            parts = legibility_losses(
                z, rhythm_ids, pos_idx, pos_mask, multi_hot,
                centroids, head, weights, cfg,
            )
            if not torch.isfinite(parts["total"]):
                raise RuntimeError(f"non-finite legibility loss at epoch {epoch}")

            opt.zero_grad(set_to_none=True)
            parts["total"].backward()
            torch.nn.utils.clip_grad_norm_(
                list(generator.parameters()) + list(head.parameters()),
                cfg.grad_clip,
            )
            opt.step()

            steps += 1
            for k in totals:
                totals[k] += float(parts[k].detach())
            gaps.append(parts["gap"])

        row = {k: (totals[k] / max(steps, 1)) for k in totals}
        if gaps:
            g = torch.cat(gaps)
            row["gap_mean"] = float(g.mean())
            row["gap_p10"] = float(torch.quantile(g, 0.10))
        row["steps"] = steps
        row["epoch"] = epoch + 1
        history.append(row)
        log(
            f"  epoch {epoch + 1}/{cfg.epochs}  "
            f"total={row['total']:.4f}  margin={row['margin']:.4f}  "
            f"centroid={row['centroid']:.4f}  jaccard={row['jaccard']:.4f}  "
            f"rank={row['rank']:.4f}  gap_mean={row.get('gap_mean', float('nan')):.3f}  "
            f"gap_p10={row.get('gap_p10', float('nan')):.3f}"
        )

    generator.train(was_training)
    return {"history": history, "head": head, "max_p": max_p}


def fit_points(
    z_init: torch.Tensor,
    rhythm_ids: torch.Tensor,
    pos_idx: torch.Tensor,
    pos_mask: torch.Tensor,
    multi_hot: torch.Tensor,
    centroids: torch.Tensor,
    orphan: torch.Tensor,
    cfg: LegibilityConfig,
    steps: int = 300,
    lr: float = 0.05,
    pair_per_rhythm: int = 48,
    log=print,
) -> dict:
    """
    Ceiling probe: move the vectors themselves, not the encoder.

    Same losses, same frozen centroids. If these points cannot become readable
    under the margin, the cone wall — not mean-pool — is the ceiling. The
    returned head is a scaffold; the caller retrains a TokenDecoder to read
    the points.
    """
    device = z_init.device
    raw = nn.Parameter(z_init.detach().clone())
    head = nn.Linear(z_init.shape[1], multi_hot.shape[1]).to(device)
    opt = torch.optim.Adam(
        [
            {"params": [raw], "lr": lr},
            {"params": list(head.parameters()), "lr": cfg.head_lr},
        ]
    )
    n = z_init.shape[0]
    history = []
    rng = np.random.default_rng(0)
    weights_all = row_weights(rhythm_ids.cpu(), orphan.cpu(), cfg).to(device)

    for t in range(steps):
        z = F.normalize(raw, dim=-1)
        # Margin, centroid, and rank see every point. Jaccard is on a rotating
        # per-rhythm subsample — a full 8k gram is the expensive part, and the
        # wall must not be estimated on that subsample.
        choose = _subsample_per_rhythm(rhythm_ids, pair_per_rhythm, rng)
        parts_j = (
            _jaccard_spread(
                z.index_select(0, choose),
                rhythm_ids.index_select(0, choose),
                multi_hot.index_select(0, choose),
                cfg,
            )
            if cfg.w_jaccard else z.new_zeros(())
        )
        walled = LegibilityConfig(**{**cfg.__dict__, "w_jaccard": 0.0})
        parts_full = legibility_losses(
            z, rhythm_ids, pos_idx, pos_mask, multi_hot,
            centroids, head, weights_all, walled,
        )
        total = parts_full["total"] + cfg.w_jaccard * parts_j
        if not torch.isfinite(total):
            raise RuntimeError(f"non-finite point loss at step {t}")
        opt.zero_grad(set_to_none=True)
        total.backward()
        opt.step()
        # Stay on the sphere. Otherwise Adam grows ||raw|| and the normalize
        # in the forward shrinks the effective step until the cloud stalls.
        with torch.no_grad():
            raw.copy_(F.normalize(raw, dim=-1))
        if t % 50 == 0 or t == steps - 1:
            row = {
                "step": t,
                "total": float(total.detach()),
                "margin": float(parts_full["margin"].detach()),
                "centroid": float(parts_full["centroid"].detach()),
                "jaccard": float(parts_j.detach()),
                "rank": float(parts_full["rank"].detach()),
                "gap_mean": float(parts_full["gap"].mean()),
            }
            history.append(row)
            log(
                f"  points step {t:3d}/{steps}  total={row['total']:.4f}  "
                f"margin={row['margin']:.4f}  jaccard={row['jaccard']:.4f}  "
                f"rank={row['rank']:.4f}  gap={row['gap_mean']:.3f}"
            )

    return {
        "z": F.normalize(raw.detach(), dim=-1),
        "head": head,
        "history": history,
        "n": n,
    }


def _subsample_per_rhythm(
    rhythm_ids: torch.Tensor,
    per: int,
    rng: np.random.Generator,
) -> torch.Tensor:
    picks = []
    for r in rhythm_ids.unique().tolist():
        idx = (rhythm_ids == int(r)).nonzero(as_tuple=False).squeeze(1).cpu().numpy()
        if len(idx) <= per:
            picks.append(idx)
        else:
            picks.append(rng.choice(idx, size=per, replace=False))
    return torch.tensor(np.concatenate(picks), dtype=torch.long, device=rhythm_ids.device)


def geometry_report(
    z: np.ndarray,
    rhythm_ids: np.ndarray,
    centroids: np.ndarray,
    sample_cap: int = 40,
    seed: int = 42,
) -> dict:
    """
    Within / across cosine the Phase 0 way (40-cap mean pairwise), plus the
    routing reads the wall is there to protect: nearest-centroid accuracy and
    the own-minus-other margin.
    """
    rng = np.random.default_rng(seed)
    z = z.astype(np.float64)
    z = z / np.clip(np.linalg.norm(z, axis=1, keepdims=True), 1e-8, None)
    centroids = centroids.astype(np.float64)
    centroids = centroids / np.clip(np.linalg.norm(centroids, axis=1, keepdims=True), 1e-8, None)

    within = {}
    samples = {}
    for r, name in enumerate(RHYTHMS):
        idx = np.flatnonzero(rhythm_ids == r)
        if len(idx) == 0:
            continue
        if len(idx) > sample_cap:
            idx = rng.choice(idx, size=sample_cap, replace=False)
        samples[r] = idx
        block = z[idx]
        sim = block @ block.T
        if len(idx) < 2:
            within[name] = None
            continue
        iu = np.triu_indices(len(idx), k=1)
        within[name] = float(sim[iu].mean())

    across_vals = []
    rhythms_present = sorted(samples)
    for i, r in enumerate(rhythms_present):
        for s in rhythms_present[i + 1:]:
            a = z[samples[r]]
            b = z[samples[s]]
            across_vals.append(float((a @ b.T).mean()))

    sim_c = z @ centroids.T
    own = sim_c[np.arange(len(z)), rhythm_ids]
    sim_c[np.arange(len(z)), rhythm_ids] = -2.0
    max_other = sim_c.max(axis=1)
    gap = own - max_other
    nn = (z @ centroids.T).argmax(axis=1)
    nn_acc = float((nn == rhythm_ids).mean()) if len(z) else None

    present = [v for v in within.values() if v is not None]
    return {
        "within": {k: (round(v, 4) if v is not None else None) for k, v in within.items()},
        "within_mean": round(float(np.mean(present)), 4) if present else None,
        "across_mean": round(float(np.mean(across_vals)), 4) if across_vals else None,
        "nn_centroid_acc": round(nn_acc, 4) if nn_acc is not None else None,
        "margin_mean": round(float(gap.mean()), 4) if len(gap) else None,
        "margin_p10": round(float(np.quantile(gap, 0.10)), 4) if len(gap) else None,
        "own_centroid_cos_mean": round(float(own.mean()), 4) if len(own) else None,
    }


def neighbor_jaccard(
    z: np.ndarray,
    multi_hot: np.ndarray,
    rhythm_ids: np.ndarray,
) -> dict:
    """
    Self-legibility, decoder-free: the nearest other vector inside the same
    rhythm should share tokens. A recall gain that does not move this number
    is a head performing coherence the geometry does not have.
    """
    z = z.astype(np.float64)
    z = z / np.clip(np.linalg.norm(z, axis=1, keepdims=True), 1e-8, None)
    y = multi_hot.astype(np.float64)
    sizes = y.sum(axis=1, keepdims=True)

    def _mean_nn() -> Optional[float]:
        acc = []
        for r in range(len(RHYTHMS)):
            idx = np.flatnonzero(rhythm_ids == r)
            if len(idx) < 2:
                continue
            block = z[idx]
            sim = block @ block.T
            np.fill_diagonal(sim, -2.0)
            nn = sim.argmax(axis=1)
            yb = y[idx]
            inter = (yb * yb[nn]).sum(axis=1)
            union = sizes[idx, 0] + sizes[idx][nn, 0] - inter
            jac = inter / np.clip(union, 1e-8, None)
            acc.append(jac)
        if not acc:
            return None
        return float(np.concatenate(acc).mean())

    # Chance: mean jaccard of random within-rhythm pairs, not nearest neighbors.
    rng = np.random.default_rng(42)
    chance_vals = []
    for r in range(len(RHYTHMS)):
        idx = np.flatnonzero(rhythm_ids == r)
        if len(idx) < 2:
            continue
        a = rng.integers(0, len(idx), size=min(400, len(idx)))
        b = rng.integers(0, len(idx), size=len(a))
        # avoid the trivial self pair
        same = a == b
        b[same] = (b[same] + 1) % len(idx)
        ya = y[idx][a]
        yb = y[idx][b]
        inter = (ya * yb).sum(axis=1)
        union = sizes[idx][a, 0] + sizes[idx][b, 0] - inter
        chance_vals.append(inter / np.clip(union, 1e-8, None))
    nn_j = _mean_nn()
    chance = float(np.concatenate(chance_vals).mean()) if chance_vals else None
    return {
        "within_cone_nn_jaccard": round(nn_j, 4) if nn_j is not None else None,
        "random_pair_jaccard": round(chance, 4) if chance is not None else None,
    }


def _self_check() -> None:
    """The wall is inactive on a collapsed-but-separated cloud and active when a point crosses."""
    torch.manual_seed(0)
    dim = 16
    centroids = F.normalize(torch.eye(5, dim), dim=-1)
    ids = []
    rows = []
    for r in range(5):
        for _ in range(4):
            rows.append(centroids[r])
            ids.append(r)
    z = torch.stack(rows).requires_grad_(True)
    rhythm_ids = torch.tensor(ids)
    vocab = 8
    pos_idx = torch.zeros(z.shape[0], 1, dtype=torch.long)
    pos_mask = torch.ones(z.shape[0], 1, dtype=torch.bool)
    multi_hot = torch.zeros(z.shape[0], vocab)
    for i, r in enumerate(ids):
        pos_idx[i, 0] = r
        multi_hot[i, r] = 1.0
    head = nn.Linear(dim, vocab)
    orphan = torch.zeros(z.shape[0], dtype=torch.bool)
    w = row_weights(rhythm_ids, orphan, LegibilityConfig())
    cfg = LegibilityConfig()
    ok = legibility_losses(
        z, rhythm_ids, pos_idx, pos_mask, multi_hot, centroids, head, w, cfg,
    )
    if float(ok["margin"].detach()) != 0.0:
        raise AssertionError(f"margin should be inactive on the centroids, got {float(ok['margin'].detach())}")
    if float(ok["centroid"].detach()) > 1e-5:
        raise AssertionError(
            f"anchor should be ~0 when every point is its centroid, got {float(ok['centroid'].detach())}"
        )

    z_bad = z.detach().clone().requires_grad_(True)
    with torch.no_grad():
        z_bad[0] = centroids[1]
    bad = legibility_losses(
        z_bad, rhythm_ids, pos_idx, pos_mask, multi_hot, centroids, head, w, cfg,
    )
    if float(bad["margin"].detach()) <= 0.0:
        raise AssertionError("margin should fire when a point sits on another centroid")
    bad["total"].backward()
    if z_bad.grad is None or not torch.isfinite(z_bad.grad).all():
        raise AssertionError("legibility loss did not backpropagate")
    print("legibility self-check ok", flush=True)


if __name__ == "__main__":
    _self_check()
