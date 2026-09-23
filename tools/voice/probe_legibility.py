"""
tools/voice/probe_legibility.py — cheap CPU probe for cone-bounded legibility.

Not a training run. The 5-rhythm checkpoint on disk is read and never written.
Nothing here steps the field, opens resonance memory, or binds a port.

Arms, pre-declared before the numbers are read:

  frozen     Phase 0 yardstick on this same checkout. Should land near
             holdout recall@8 = 0.1106. If it does not, the later arms are
             not comparable and the probe says so.
  walled     The proposal: margin + frozen-centroid anchor + within-rhythm
             jaccard spread + auxiliary token rank. Rupture and orphan
             sequences upweighted on the rank term only.
  naive      Same budget, rank loss only. The reconstruction objective with
             the wall taken off. This is the arm that is allowed to flatten
             the cones; it exists to show the wall is doing something.
  points     Free vectors on the sphere, same walled loss, in-sample. The
             ceiling of fork (i) under the routing margin, with mean-pool
             removed from the question.
  points0    Same, margin set to 0. Sensitivity: how much the wall costs.
             Not a candidate to ship.
  bag        Mean of learned token embeddings, rank loss, no rhythm wall.
             If this cannot be read back, 128-d mean-pool cannot hold these
             bags and fork (ii) is required. If it can, the pool is not the
             ceiling.

The mouth on every arm that has a function (frozen, walled, naive, bag) is a
fresh TokenDecoder, BCE, hidden 256, 20 epochs, seed 42 — the Phase 0
protocol. The linear head used inside the fit is reported separately and is
not that mouth.

Self-legibility gate (decoder-free): within-cone nearest-neighbor token
Jaccard. A recall gain that does not move this is the head performing
coherence the substrate does not have, and does not count.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, ".")

from agents.decoder import TokenDecoder
from agents.generator import Generator
from training.corpus import RHYTHMS, TRAIN_PATH, HOLDOUT_PATH, corpus_version, load_corpus
from training.decoder_training import _vocab_from, evaluate, train_decoder
from training.legibility import (
    LegibilityConfig,
    _self_check,
    fit_encoder,
    fit_points,
    geometry_report,
    neighbor_jaccard,
    pack_positives,
)

W = "data/checkpoints/generator_weights_5rhythm.pt"
E = "data/checkpoints/generator_ecology_5rhythm.json"
METRICS = Path("docs/findings/2026-09-22-encoder-legibility-metrics.json")
DIM = 128
DECODER_EPOCHS = 20
TOPK = 8
PHASE0_HOLDOUT_RECALL = 0.1106
PHASE0_WITHIN = (0.94, 0.97)
PHASE0_ACROSS = 0.34


def _log(msg: str) -> None:
    print(msg, flush=True)


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def _encode(gen, token_lists, batch=128) -> np.ndarray:
    gen.eval()
    out = []
    n = len(token_lists)
    t0 = time.perf_counter()
    for i in range(0, n, batch):
        out.append(gen.encode_batch(token_lists[i:i + batch]))
        done = min(i + batch, n)
        if done == n or done % (batch * 8) == 0:
            _log(f"    encode {done}/{n}  {time.perf_counter() - t0:.1f}s")
    return np.concatenate(out, axis=0).astype(np.float32)


def _snapshot(gen) -> dict:
    return {k: v.detach().cpu().clone() for k, v in gen.state_dict().items()}


def _restore(gen, snap) -> None:
    gen.load_state_dict({k: v.to(gen.device) for k, v in snap.items()})
    gen.eval()


def _centroids(z: np.ndarray, rhythm_ids: np.ndarray) -> np.ndarray:
    cs = []
    for r in range(len(RHYTHMS)):
        block = z[rhythm_ids == r]
        if len(block) == 0:
            cs.append(np.zeros(z.shape[1], dtype=np.float64))
            continue
        c = block.mean(axis=0)
        cs.append(c / (np.linalg.norm(c) + 1e-8))
    return np.stack(cs).astype(np.float32)


def _rank_table(logits: torch.Tensor, token_lists, vocab) -> dict:
    """Median true-token rank (1 = best) and recall@8, matching evaluate's mean-over-sequences."""
    index = {t: i for i, t in enumerate(vocab)}
    V = logits.shape[1]
    order = logits.argsort(dim=-1, descending=True)
    rank_of = torch.empty_like(order)
    rank_of.scatter_(
        1, order,
        torch.arange(1, V + 1, device=logits.device).view(1, -1).expand_as(order),
    )
    recalls = []
    ranks = []
    for i, toks in enumerate(token_lists):
        true = [index[t] for t in toks if t in index]
        if not true:
            continue
        r = rank_of[i, true]
        ranks.extend(int(x) for x in r.tolist())
        recalls.append(float((r <= TOPK).float().mean()))
    if not ranks:
        return {"n": 0, "recall@8": None, "median_rank": None}
    return {
        "n": len(recalls),
        "recall@8": round(float(np.mean(recalls)), 4),
        "median_rank": int(np.median(ranks)),
        "mean_rank": round(float(np.mean(ranks)), 1),
    }


def _subset_table(logits, token_lists, vocab, rhythm_names, mask, ecology_tokens) -> dict:
    """Per-rhythm and orphan-vs-trained splits on one readout."""
    index = {t: i for i, t in enumerate(vocab)}
    V = logits.shape[1]
    order = logits.argsort(dim=-1, descending=True)
    rank_of = torch.empty_like(order)
    rank_of.scatter_(
        1, order,
        torch.arange(1, V + 1, device=logits.device).view(1, -1).expand_as(order),
    )
    by = {name: [] for name in RHYTHMS}
    by_rank = {name: [] for name in RHYTHMS}
    orphan_hit = orphan_n = trained_hit = trained_n = 0
    orphan_ranks = []
    trained_ranks = []
    for i, toks in enumerate(token_lists):
        if mask is not None and not mask[i]:
            continue
        true = []
        for t in toks:
            j = index.get(t)
            if j is None:
                continue
            true.append(j)
            rk = int(rank_of[i, j])
            if t in ecology_tokens:
                trained_n += 1
                trained_hit += int(rk <= TOPK)
                trained_ranks.append(rk)
            else:
                orphan_n += 1
                orphan_hit += int(rk <= TOPK)
                orphan_ranks.append(rk)
        if not true:
            continue
        r = rank_of[i, true]
        rec = float((r <= TOPK).float().mean())
        name = rhythm_names[i]
        by[name].append(rec)
        by_rank[name].extend(int(x) for x in r.tolist())

    def _rate(h, n):
        return round(h / n, 4) if n else None

    per = {}
    for name in RHYTHMS:
        per[name] = {
            "n": len(by[name]),
            "recall@8": round(float(np.mean(by[name])), 4) if by[name] else None,
            "median_rank": int(np.median(by_rank[name])) if by_rank[name] else None,
        }
    return {
        "per_rhythm": per,
        "orphan_token_recall@8": _rate(orphan_hit, orphan_n),
        "orphan_token_n": orphan_n,
        "orphan_median_rank": int(np.median(orphan_ranks)) if orphan_ranks else None,
        "trained_token_recall@8": _rate(trained_hit, trained_n),
        "trained_token_n": trained_n,
        "trained_median_rank": int(np.median(trained_ranks)) if trained_ranks else None,
    }


def _head_logits(head, z: np.ndarray) -> torch.Tensor:
    head.eval()
    with torch.no_grad():
        t = torch.tensor(z, dtype=torch.float32)
        return head(t)


def _nn_jaccard(z, token_lists, vocab, rhythm_ids) -> dict:
    index = {t: i for i, t in enumerate(vocab)}
    y = np.zeros((len(token_lists), len(vocab)), dtype=np.float32)
    for i, toks in enumerate(token_lists):
        for t in toks:
            j = index.get(t)
            if j is not None:
                y[i, j] = 1.0
    # Cap the pair work: neighbor_jaccard is O(n^2) per rhythm. 400/rhythm is enough.
    return neighbor_jaccard(z, y, rhythm_ids)


def _row_report(weight_now, weight_then, addrs) -> dict:
    if not addrs:
        return {"n": 0}
    a = torch.tensor(addrs, dtype=torch.long)
    now = weight_now.index_select(0, a).float()
    then = weight_then.index_select(0, a).float()
    cos = F.cosine_similarity(now, then, dim=-1)
    return {
        "n": len(addrs),
        "row_cosine_mean": round(float(cos.mean()), 4),
        "row_cosine_p10": round(float(torch.quantile(cos, 0.10)), 4),
        "l2_before": round(float(then.norm(dim=-1).mean()), 4),
        "l2_after": round(float(now.norm(dim=-1).mean()), 4),
    }


def _pick_subset(rhythm_ids: np.ndarray, per: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    picks = []
    for r in range(len(RHYTHMS)):
        idx = np.flatnonzero(rhythm_ids == r)
        if len(idx) <= per:
            picks.append(idx)
        else:
            picks.append(rng.choice(idx, size=per, replace=False))
    return np.sort(np.concatenate(picks))


def _arm_report(
    name, z_tr, toks_tr, rid_tr, z_ho, toks_ho, rid_ho, rhythms_ho,
    vocab, ecology_tokens, clean_ho, centroids, frozen_centroids,
    frozen_z_ho=None, head=None, z_for_jaccard_train=None,
) -> dict:
    _log(f"  Phase 0 mouth on {name} ...")
    torch.manual_seed(42)
    dec = TokenDecoder(vocab, dim=DIM, hidden=256, device="cpu")
    Xtr_t = torch.tensor(np.asarray(z_tr), dtype=torch.float32)
    Xho_t = torch.tensor(np.asarray(z_ho), dtype=torch.float32)
    train_decoder(None, dec, Xtr_t, toks_tr, epochs=DECODER_EPOCHS)
    tr = evaluate(dec, Xtr_t, toks_tr, top_k=TOPK)
    ho = evaluate(dec, Xho_t, toks_ho, top_k=TOPK)
    with torch.no_grad():
        logits_ho = dec(Xho_t)
    # Cross-check the rank table's recall against evaluate().
    ranks = _rank_table(logits_ho, toks_ho, vocab)
    if ho["recall@k"] is not None and ranks["recall@8"] is not None:
        if abs(ho["recall@k"] - ranks["recall@8"]) > 5e-4:
            raise AssertionError(
                f"{name} recall mismatch evaluate={ho['recall@k']} ranks={ranks['recall@8']}"
            )
    splits = _subset_table(logits_ho, toks_ho, vocab, rhythms_ho, None, ecology_tokens)
    clean_idx = [i for i, c in enumerate(clean_ho) if c]
    dirty_idx = [i for i, c in enumerate(clean_ho) if not c]
    clean_logits = logits_ho[clean_idx] if clean_idx else logits_ho[:0]
    clean_toks = [toks_ho[i] for i in clean_idx]
    clean_rhythms = [rhythms_ho[i] for i in clean_idx]
    clean_splits = _subset_table(
        clean_logits, clean_toks, vocab, clean_rhythms, None, ecology_tokens,
    ) if clean_idx else {}
    new_c = _centroids(z_ho, rid_ho)
    drift_c = [
        round(float(np.dot(new_c[r], frozen_centroids[r])), 4) for r in range(len(RHYTHMS))
    ]
    geo = geometry_report(z_ho, rid_ho, frozen_centroids)
    clean_arr = np.array(clean_ho, dtype=bool)
    geo_clean = (
        geometry_report(z_ho[clean_arr], rid_ho[clean_arr], frozen_centroids)
        if clean_arr.any() else None
    )
    cap = _pick_subset(rid_ho, 80, seed=1)
    nn = _nn_jaccard(z_ho[cap], [toks_ho[i] for i in cap], vocab, rid_ho[cap])
    out = {
        "mouth_train": tr,
        "mouth_holdout": ho,
        "holdout_rank": ranks,
        "holdout_splits_all": splits,
        "holdout_splits_clean": clean_splits,
        "dirty_holdout_n": len(dirty_idx),
        "clean_holdout_n": len(clean_idx),
        "geometry_vs_frozen_centroids": geo,
        "geometry_clean_holdout": geo_clean,
        "centroid_cos_to_frozen": {RHYTHMS[r]: drift_c[r] for r in range(len(RHYTHMS))},
        "nn_jaccard_holdout": nn,
    }
    if frozen_z_ho is not None:
        # Both sides are unit (encoder normalize_output). Clip for safety.
        a = z_ho / np.clip(np.linalg.norm(z_ho, axis=1, keepdims=True), 1e-8, None)
        b = frozen_z_ho / np.clip(np.linalg.norm(frozen_z_ho, axis=1, keepdims=True), 1e-8, None)
        drift = np.sum(a * b, axis=1)
        clean = np.array(clean_ho, dtype=bool)
        out["encode_cos_to_frozen_mean"] = round(float(drift.mean()), 4)
        out["encode_cos_to_frozen_clean_mean"] = (
            round(float(drift[clean].mean()), 4) if clean.any() else None
        )
    if head is not None:
        out["scaffold_head_holdout"] = _rank_table(_head_logits(head, z_ho), toks_ho, vocab)
    _log(
        f"  {name}: holdout recall@8={ho['recall@k']}  "
        f"median_rank={ranks['median_rank']}  "
        f"within={geo['within_mean']}  across={geo['across_mean']}  "
        f"nn_acc={geo['nn_centroid_acc']}  "
        f"nn_jaccard={nn['within_cone_nn_jaccard']}"
    )
    return out


def _fit_bag(token_lists_tr, token_lists_ho, token_index, rhythm_ids_unused, epochs=12):
    """Unconstrained mean-pool of a fresh embedding table. Capacity, not a cone."""
    vocab = len(token_index)
    max_p = max(len(set(t)) for t in token_lists_tr)
    pos_tr, mask_tr, _ = pack_positives(token_lists_tr, token_index, max_p)
    pos_ho, mask_ho, _ = pack_positives(token_lists_ho, token_index, max_p)
    emb = torch.nn.Embedding(vocab, DIM)
    torch.nn.init.normal_(emb.weight, 0.0, 0.05)
    head = torch.nn.Linear(DIM, vocab)
    opt = torch.optim.Adam(list(emb.parameters()) + list(head.parameters()), lr=1e-3)
    n = pos_tr.shape[0]
    cfg = LegibilityConfig(w_margin=0, w_centroid=0, w_jaccard=0, w_rank=1)
    ones = torch.ones(n)
    bs = 256
    for ep in range(epochs):
        perm = torch.randperm(n)
        total = 0.0
        steps = 0
        for s in range(0, n, bs):
            idx = perm[s:s + bs]
            e = emb(pos_tr[idx].clamp(min=0))
            m = mask_tr[idx].unsqueeze(-1).float()
            z = F.normalize((e * m).sum(dim=1) / m.sum(dim=1).clamp(min=1), dim=-1)
            from training.legibility import _sampled_rank
            import math
            raw = _sampled_rank(head(z), pos_tr[idx], mask_tr[idx], ones[idx], cfg.rank_negatives)
            loss = raw / math.log(cfg.rank_negatives + 1)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            total += float(loss.detach())
            steps += 1
        if ep == 0 or (ep + 1) % 4 == 0 or ep == epochs - 1:
            _log(f"  bag epoch {ep + 1}/{epochs}  rank={total / max(steps, 1):.4f}")

    def _z(pos, mask):
        with torch.no_grad():
            e = emb(pos.clamp(min=0))
            m = mask.unsqueeze(-1).float()
            return F.normalize((e * m).sum(1) / m.sum(1).clamp(min=1), dim=-1).cpu().numpy()

    return _z(pos_tr, mask_tr), _z(pos_ho, mask_ho), head


def _verdict(frozen, walled, naive, points, points0, bag) -> dict:
    """Rules fixed before the run. A miss is a miss; do not retune the bar."""
    f_rec = frozen["mouth_holdout"]["recall@k"]
    w_rec = walled["mouth_holdout"]["recall@k"]
    f_rank = frozen["holdout_rank"]["median_rank"]
    w_rank = walled["holdout_rank"]["median_rank"]
    f_jac = frozen["nn_jaccard_holdout"]["within_cone_nn_jaccard"]
    w_jac = walled["nn_jaccard_holdout"]["within_cone_nn_jaccard"]
    w_nn = walled["geometry_vs_frozen_centroids"]["nn_centroid_acc"]
    w_across = walled["geometry_vs_frozen_centroids"]["across_mean"]
    f_across = frozen["geometry_vs_frozen_centroids"]["across_mean"]
    centroid_cos = walled["centroid_cos_to_frozen"]
    centroid_min = min(centroid_cos.values())
    # Phase 0's rupture number (0.055, median rank 102) is the clean holdout.
    rupture_f = frozen["holdout_splits_clean"]["per_rhythm"]["rupture"]["recall@8"]
    rupture_w = walled["holdout_splits_clean"]["per_rhythm"]["rupture"]["recall@8"]
    bag_rec = bag["mouth_holdout"]["recall@k"]
    pts_rec = points["in_sample_recall@8"]
    pts0_rec = points0["in_sample_recall@8"]
    naive_nn = naive["geometry_vs_frozen_centroids"]["nn_centroid_acc"]
    naive_across = naive["geometry_vs_frozen_centroids"]["across_mean"]

    self_legible = (
        w_rec is not None and f_rec is not None and (w_rec - f_rec) >= 0.05
        and w_jac is not None and f_jac is not None and (w_jac - f_jac) >= 0.02
        and w_nn is not None and w_nn >= 0.98
        and w_across is not None and f_across is not None and w_across <= f_across + 0.08
        and centroid_min >= 0.95
    )
    meaningful_mouth = (
        w_rec is not None and (w_rec >= 0.20 or (w_rec >= 0.15 and w_rank is not None and w_rank <= 25))
    )
    cones_held = (
        w_nn is not None and w_nn >= 0.98
        and centroid_min >= 0.95
        and w_across is not None and f_across is not None and w_across <= max(0.50, f_across + 0.08)
    )
    rupture_up = (
        rupture_w is not None and rupture_f is not None and (rupture_w - rupture_f) >= 0.02
    )
    # Fork read.
    bag_can_hold = bag_rec is not None and bag_rec >= 0.40
    wall_blocks = (
        pts_rec is not None and pts0_rec is not None and (pts0_rec - pts_rec) >= 0.10
        and pts_rec < 0.25
    )
    if not bag_can_hold:
        fork = "ii"
        fork_why = (
            "Unconstrained mean-pool bag recall stayed below 0.40. "
            "128-d mean of these bags does not carry token identity. Fork (ii)."
        )
    elif self_legible and meaningful_mouth and cones_held:
        fork = "i"
        fork_why = (
            "Walled encoder moved holdout recall and within-cone neighbor Jaccard "
            "with routing and frozen centroids intact, and the bag arm shows the "
            "dim can hold a bag. Fork (i) is enough for a bag mouth. Fork (ii) "
            "waits until word order is the goal."
        )
    elif (not self_legible) and wall_blocks and cones_held:
        fork = "wall"
        fork_why = (
            "Free points under the routing margin stay near the frozen recall, "
            "and dropping the margin raises the ceiling. The pool is not the "
            "ceiling; the wall is. Do not silently lower it — that is an "
            "attractor-routing change and needs an architect call."
        )
    elif cones_held and w_rec is not None and f_rec is not None and (w_rec - f_rec) >= 0.03:
        fork = "i-budget"
        fork_why = (
            "Cones held and recall moved, but not past the pre-declared mouth bar. "
            "A full-data GPU run is a longer fit of fork (i), not a reason to drop mean-pool."
        )
    else:
        fork = "inconclusive"
        fork_why = (
            "The cheap fit did not clear the pre-declared bar and the ceiling "
            "arms do not pin the blame on mean-pool. Read the component losses "
            "before spending a GPU run."
        )
    return {
        "frozen_recall_near_phase0": abs((f_rec or 0) - PHASE0_HOLDOUT_RECALL) <= 0.02,
        "self_legible": self_legible,
        "meaningful_mouth": meaningful_mouth,
        "cones_held": cones_held,
        "rupture_improved": rupture_up,
        "fork": fork,
        "fork_why": fork_why,
        "naive_kept_cones": naive_nn is not None and naive_nn >= 0.98,
        "naive_across": naive_across,
        "numbers": {
            "frozen_recall": f_rec,
            "walled_recall": w_rec,
            "frozen_median_rank": f_rank,
            "walled_median_rank": w_rank,
            "frozen_nn_jaccard": f_jac,
            "walled_nn_jaccard": w_jac,
            "walled_nn_acc": w_nn,
            "walled_across": w_across,
            "frozen_across": f_across,
            "centroid_cos_min": centroid_min,
            "rupture_frozen": rupture_f,
            "rupture_walled": rupture_w,
            "bag_recall": bag_rec,
            "points_recall": pts_rec,
            "points0_recall": pts0_rec,
        },
    }


def _points_arm(name, z, rhythm_ids, token_lists, token_index, centroids, orphan, cfg, steps):
    _log(f"  free points: {name}  n={len(z)}  margin={cfg.margin}  steps={steps}")
    pos_idx, pos_mask, multi_hot = pack_positives(token_lists, token_index, max(len(set(t)) for t in token_lists))
    rid = torch.tensor(rhythm_ids, dtype=torch.long)
    orph = torch.tensor(orphan, dtype=torch.bool)
    cents = torch.tensor(centroids, dtype=torch.float32)
    out = fit_points(
        torch.tensor(z, dtype=torch.float32),
        rid, pos_idx, pos_mask, multi_hot, cents, orph, cfg,
        steps=steps, lr=0.05, pair_per_rhythm=min(48, max(4, len(z) // 5)),
        log=_log,
    )
    z_out = out["z"].cpu().numpy()
    # In-sample mouth. Small n, same protocol otherwise.
    torch.manual_seed(42)
    vocab = [None] * len(token_index)
    for t, i in token_index.items():
        vocab[i] = t
    dec = TokenDecoder(vocab, dim=DIM, hidden=256, device="cpu")
    X = torch.tensor(z_out, dtype=torch.float32)
    train_decoder(None, dec, X, token_lists, epochs=DECODER_EPOCHS)
    ev = evaluate(dec, X, token_lists, top_k=TOPK)
    with torch.no_grad():
        logits = dec(X)
    ranks = _rank_table(logits, token_lists, vocab)
    geo = geometry_report(z_out, rhythm_ids, centroids)
    nn = _nn_jaccard(z_out, token_lists, vocab, rhythm_ids)
    _log(
        f"  {name}: IN-SAMPLE recall@8={ev['recall@k']}  "
        f"median_rank={ranks['median_rank']}  "
        f"within={geo['within_mean']}  across={geo['across_mean']}  "
        f"nn_acc={geo['nn_centroid_acc']}  nn_jaccard={nn['within_cone_nn_jaccard']}"
    )
    return {
        "in_sample_recall@8": ev["recall@k"],
        "in_sample_exact_bag@8": ev["exact_bag@k"],
        "in_sample_rank": ranks,
        "geometry": geo,
        "nn_jaccard": nn,
        "history_tail": out["history"][-3:],
        "n": int(len(z)),
    }


def main() -> int:
    t_all = time.perf_counter()
    _self_check()
    if torch.cuda.is_available():
        _log("cuda is visible; probe forces CPU anyway")

    train = load_corpus(TRAIN_PATH)
    holdout = load_corpus(HOLDOUT_PATH)
    vocab = _vocab_from(train)
    token_index = {t: i for i, t in enumerate(vocab)}
    _log(f"corpus v{corpus_version()}  train={len(train)} holdout={len(holdout)} vocab={len(vocab)}")

    gen = Generator(vocab_size=8192, dim=DIM, depth=4, heads=4, device="cpu")
    gen.load_checkpoint(W, E)
    gen.eval()
    pipe = gen.registry.pipeline
    ecology = set(gen.registry.symbols)
    _log(f"ecology symbols before orphan registration: {len(ecology)}")

    def canon(tok: str) -> str:
        return pipe.process(tok).token

    ecology_tokens = set()
    orphan_tokens = []
    for t in vocab:
        c = canon(t)
        if c in ecology:
            ecology_tokens.add(t)
        else:
            orphan_tokens.append(t)
    _log(f"vocab tokens with a trained row: {len(ecology_tokens)}  orphan: {len(orphan_tokens)}")

    def mark(records):
        out = []
        for rec in records:
            orph = any(t not in ecology_tokens for t in rec["tokens"])
            out.append({
                "tokens": list(rec["tokens"]),
                "rhythm": rec["rhythm"],
                "orphan": orph,
            })
        return out

    train_m = mark(train)
    hold_m = mark(holdout)
    rid_tr = np.array([RHYTHMS.index(r["rhythm"]) for r in train_m], dtype=np.int64)
    rid_ho = np.array([RHYTHMS.index(r["rhythm"]) for r in hold_m], dtype=np.int64)
    rhythms_ho = [r["rhythm"] for r in hold_m]
    toks_tr = [r["tokens"] for r in train_m]
    toks_ho = [r["tokens"] for r in hold_m]
    clean_tr = [not r["orphan"] for r in train_m]
    clean_ho = [not r["orphan"] for r in hold_m]
    _log(
        "clean sequences  train "
        + " ".join(f"{name}={sum(1 for r, c in zip(train_m, clean_tr) if c and r['rhythm']==name)}" for name in RHYTHMS)
    )

    _log("frozen centroids from clean train encodes ...")
    clean_lists = [r["tokens"] for r, c in zip(train_m, clean_tr) if c]
    clean_rids = np.array(
        [RHYTHMS.index(r["rhythm"]) for r, c in zip(train_m, clean_tr) if c],
        dtype=np.int64,
    )
    z_clean = _encode(gen, clean_lists)
    centroids_np = _centroids(z_clean, clean_rids)
    cent_sim = centroids_np @ centroids_np.T
    _log("frozen centroid cosine:")
    for i, a in enumerate(RHYTHMS):
        row = " ".join(f"{cent_sim[i, j]:+.3f}" for j in range(len(RHYTHMS)))
        _log(f"  {a:10s} {row}")

    # Register orphan rows at init, then snapshot. This is the Phase 0 state:
    # virgin rows exist, weights otherwise the checkpoint.
    trained_addrs = [gen.registry.symbols[canon(t)].address for t in ecology_tokens]
    for t in orphan_tokens:
        gen.registry.register(t)
    gen._ensure_embedding_capacity()
    orphan_addrs = []
    for t in orphan_tokens:
        st = gen.registry.symbols.get(canon(t))
        if st is not None:
            orphan_addrs.append(st.address)
    snap = _snapshot(gen)
    weight0 = snap["embedding.weight"].float()

    _log("frozen encode of full train + holdout ...")
    z_tr = _encode(gen, toks_tr)
    z_ho = _encode(gen, toks_ho)

    report = {
        "corpus": corpus_version(),
        "checkpoint": W,
        "device": "cpu",
        "orphan_tokens": len(orphan_tokens),
        "trained_tokens": len(ecology_tokens),
        "phase0_reference": {
            "holdout_recall@8": PHASE0_HOLDOUT_RECALL,
            "within": list(PHASE0_WITHIN),
            "across": PHASE0_ACROSS,
            "median_rank": 40,
            "rupture_recall@8": 0.055,
            "rupture_median_rank": 102,
        },
        "frozen_centroid_cosine": {
            RHYTHMS[i]: {RHYTHMS[j]: round(float(cent_sim[i, j]), 4) for j in range(len(RHYTHMS))}
            for i in range(len(RHYTHMS))
        },
    }

    _log("ARM frozen")
    report["frozen"] = _arm_report(
        "frozen", z_tr, toks_tr, rid_tr, z_ho, toks_ho, rid_ho, rhythms_ho,
        vocab, ecology_tokens, clean_ho, centroids_np, centroids_np,
    )
    f_rec = report["frozen"]["mouth_holdout"]["recall@k"]
    if f_rec is None or abs(f_rec - PHASE0_HOLDOUT_RECALL) > 0.02:
        _log(f"  WARNING: frozen recall {f_rec} is not within 0.02 of Phase 0 {PHASE0_HOLDOUT_RECALL}")

    cfg = LegibilityConfig()
    cents = torch.tensor(centroids_np, dtype=torch.float32)
    _log("ARM walled (the proposal)")
    walled_fit = fit_encoder(gen, train_m, cents, token_index, cfg, log=_log)
    z_tr_w = _encode(gen, toks_tr)
    z_ho_w = _encode(gen, toks_ho)
    report["walled"] = _arm_report(
        "walled", z_tr_w, toks_tr, rid_tr, z_ho_w, toks_ho, rid_ho, rhythms_ho,
        vocab, ecology_tokens, clean_ho, centroids_np, centroids_np,
        frozen_z_ho=z_ho, head=walled_fit["head"],
    )
    report["walled"]["fit_history"] = walled_fit["history"]
    report["walled"]["rows_trained"] = _row_report(gen.embedding.weight.detach().cpu().float(), weight0, trained_addrs)
    report["walled"]["rows_orphan"] = _row_report(gen.embedding.weight.detach().cpu().float(), weight0, orphan_addrs)
    _log(f"  trained-row drift: {report['walled']['rows_trained']}")
    _log(f"  orphan-row drift:  {report['walled']['rows_orphan']}")

    _log("ARM naive (rank only, wall off)")
    _restore(gen, snap)
    naive_cfg = LegibilityConfig(w_margin=0.0, w_centroid=0.0, w_jaccard=0.0, w_rank=1.0, epochs=cfg.epochs)
    naive_fit = fit_encoder(gen, train_m, cents, token_index, naive_cfg, log=_log)
    z_tr_n = _encode(gen, toks_tr)
    z_ho_n = _encode(gen, toks_ho)
    report["naive"] = _arm_report(
        "naive", z_tr_n, toks_tr, rid_tr, z_ho_n, toks_ho, rid_ho, rhythms_ho,
        vocab, ecology_tokens, clean_ho, centroids_np, centroids_np,
        frozen_z_ho=z_ho, head=naive_fit["head"],
    )
    report["naive"]["fit_history"] = naive_fit["history"]
    _restore(gen, snap)

    sub = _pick_subset(rid_tr, 64, seed=7)
    _log(f"ARM free points on {len(sub)} train vectors")
    sub_toks = [toks_tr[i] for i in sub]
    sub_orph = [train_m[i]["orphan"] for i in sub]
    report["points"] = _points_arm(
        "points-margin-0.20", z_tr[sub], rid_tr[sub], sub_toks, token_index,
        centroids_np, sub_orph, cfg, steps=200,
    )
    loose = LegibilityConfig(**{**cfg.__dict__, "margin": 0.0, "w_margin": 0.0})
    report["points_wall_off"] = _points_arm(
        "points-wall-off", z_tr[sub], rid_tr[sub], sub_toks, token_index,
        centroids_np, sub_orph, loose, steps=200,
    )

    _log("ARM bag (unconstrained mean-pool capacity)")
    z_tr_b, z_ho_b, bag_head = _fit_bag(toks_tr, toks_ho, token_index, rid_tr, epochs=12)
    # Bag vectors are not in the frozen cone space. Geometry vs frozen centroids
    # is reported so the flatten is visible, and is not a routing success criterion.
    report["bag"] = _arm_report(
        "bag", z_tr_b, toks_tr, rid_tr, z_ho_b, toks_ho, rid_ho, rhythms_ho,
        vocab, ecology_tokens, clean_ho, centroids_np, centroids_np, head=bag_head,
    )

    report["verdict"] = _verdict(
        report["frozen"], report["walled"], report["naive"],
        report["points"], report["points_wall_off"], report["bag"],
    )
    report["seconds"] = round(time.perf_counter() - t_all, 1)
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(_jsonable(report), indent=2), encoding="utf-8")
    _log(f"WROTE {METRICS}")
    _log(f"VERDICT fork={report['verdict']['fork']}")
    _log(report["verdict"]["fork_why"])
    _log(json.dumps(report["verdict"]["numbers"], indent=2))
    _log(f"done in {report['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
