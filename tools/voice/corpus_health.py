"""
tools/voice/corpus_health.py — the yardstick corpus growth has to clear.

Samuel's rule on this encoder: the representation stays level. No redundant
phrasings, no deep basins, no hub token, spread preserved. This script
measures that on the current corpus and scores a candidate batch against
the same numbers. The thresholds at the bottom of the report are a proposal
for the architect, not a law.

Two stages.

  A. Corpus only, no encoder. Exact and near-duplicate bags (Jaccard),
     repeated pairs, context-count hub cap, within-rhythm token share.
     This is what an addition is not allowed to add more of.

  B. The encoded landscape, frozen 5-rhythm checkpoint, optionally the
     legible one. Participation ratio and effective rank (is the spread
     using the space, or one direction), entropy of the nearest-neighbor
     cosine distribution, depth gap inside each cone, sequence-hub and
     token-hub indegree, and the split between a tight neighbor that
     shares its bag and a tight neighbor that does not.

Stage B does not step the field and does not write either checkpoint.
The field lock is not a lever here. A batch that passes A can still fail
B, because piling new sequences into one existing hole is a basin even
when none of the bags are near-duplicates of each other.

Run:
    python tools/voice/corpus_health.py
    python tools/voice/corpus_health.py --batch data/corpus/candidate.jsonl
    python tools/voice/corpus_health.py --self-check
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")

from training.corpus import (
    HOLDOUT_PATH,
    RHYTHMS,
    TRAIN_PATH,
    corpus_version,
    load_corpus,
)
from training.rhythm_pretraining import DEFAULT_RHYTHM_SEEDS

FROZEN_W = Path("data/checkpoints/generator_weights_5rhythm.pt")
FROZEN_E = Path("data/checkpoints/generator_ecology_5rhythm.json")
LEGIBLE_W = Path("data/checkpoints/generator_weights_5rhythm_legible.pt")
LEGIBLE_E = Path("data/checkpoints/generator_ecology_5rhythm_legible.json")
METRICS = Path("docs/findings/2026-09-22-corpus-health-metrics.json")

NEAR_J = 0.80          # legibility objective's pull_jaccard: a near-duplicate bag
CROSS_FORBID_J = 0.80  # same phrasing in two rhythms
CONTEXT_FLOOR = 8      # data_curation.md, corpus integrity check
KNN_K = 8
TIGHT_COS = 0.95       # neighbor close enough to call a local hole
LOW_J = 0.50           # not enough shared tokens to justify that hole
DIM = 128

# Proposal, relative to the measured baseline of THIS corpus on the FROZEN
# encoder. Samuel rules on these. They are not silently the law.
PROPOSAL_RULES = {
    "exact_sequence_overlap_with_train": 0,
    "exact_bag_overlap_with_train": 0,
    "exact_bag_cross_rhythm": 0,
    "batch_within_near_dup_rate_max": 0.0,
    "why_not_the_measured_rate": "the measured rate is order-swapped bags; it is a debt, not a budget",
    "batch_cross_rhythm_jaccard_ge_0.80": 0,
    "context_floor": CONTEXT_FLOOR,
    "context_count_cap": "baseline max distinct-sequence count of any token",
    "rhythm_share_cap": "baseline max fraction of one rhythm containing one token",
    "unordered_pair_count_cap": "baseline max times any unordered pair co-occurs",
    "participation_ratio_min": "0.98 * baseline cone (clean sequences)",
    "effective_rank_min": "0.98 * baseline cone",
    "depth_gap_p95_minus_p50_max_rise": 0.02,
    "sequence_hub_indegree_max": "ceil(1.10 * baseline)",
    "token_hub_indegree_max": "baseline (a token may not become a stronger magnet)",
    "knn_cosine_and_density_entropy": "reported, not binding, while the frozen neighborhood is a spike at cosine 1",
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def _round(x, n=4):
    if x is None:
        return None
    return round(float(x), n)


def _file_id(path: Path) -> dict:
    data = path.read_bytes()
    st = path.stat()
    return {
        "path": str(path).replace("\\", "/"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "mtime_ns": st.st_mtime_ns,
    }


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
    if isinstance(o, Path):
        return str(o)
    return o


def _bags(records):
    return [frozenset(r["tokens"]) for r in records]


def _rhythm_ids(records) -> np.ndarray:
    return np.array([RHYTHMS.index(r["rhythm"]) for r in records], dtype=np.int64)


def _multi_hot(records, index) -> np.ndarray:
    y = np.zeros((len(records), len(index)), dtype=np.float32)
    for i, rec in enumerate(records):
        for t in rec["tokens"]:
            j = index.get(t)
            if j is not None:
                y[i, j] = 1.0
    return y


def _nn_jaccard(y: np.ndarray, rhythm_ids: np.ndarray, batch=512):
    """Per-row max bag-Jaccard inside the rhythm and across rhythms."""
    n = y.shape[0]
    sizes = y.sum(axis=1)
    within_j = np.full(n, -1.0, dtype=np.float64)
    within_i = np.full(n, -1, dtype=np.int64)
    cross_j = np.full(n, -1.0, dtype=np.float64)
    cross_i = np.full(n, -1, dtype=np.int64)
    for s in range(0, n, batch):
        e = min(s + batch, n)
        inter = y[s:e] @ y.T
        union = sizes[s:e, None] + sizes[None, :] - inter
        jac = inter / np.maximum(union, 1.0)
        rows = np.arange(e - s)
        cols = np.arange(s, e)
        jac[rows, cols] = -1.0
        same = rhythm_ids[s:e, None] == rhythm_ids[None, :]
        same[rows, cols] = False
        within = np.where(same, jac, -1.0)
        cross = np.where(~same, jac, -1.0)
        w_arg = within.argmax(axis=1)
        c_arg = cross.argmax(axis=1)
        within_j[s:e] = within[rows, w_arg]
        within_i[s:e] = w_arg
        cross_j[s:e] = cross[rows, c_arg]
        cross_i[s:e] = c_arg
    return within_j, within_i, cross_j, cross_i


def _dist_summary(values: np.ndarray) -> dict:
    v = values[values >= 0]
    if len(v) == 0:
        return {"n": 0}
    return {
        "n": int(len(v)),
        "mean": _round(v.mean()),
        "p50": _round(np.quantile(v, 0.50)),
        "p90": _round(np.quantile(v, 0.90)),
        "p99": _round(np.quantile(v, 0.99)),
        "max": _round(v.max()),
        "frac_ge_0.80": _round(float((v >= NEAR_J).mean())),
        "frac_ge_0.50": _round(float((v >= 0.50).mean())),
        "frac_eq_1": _round(float(np.isclose(v, 1.0).mean())),
        "n_ge_0.80": int((v >= NEAR_J).sum()),
        "n_eq_1": int(np.isclose(v, 1.0).sum()),
    }


def _pair_examples(records, scores, indices, k, cross_only=False):
    """Highest unique neighbor pairs. scores[i] is Jaccard to indices[i]."""
    seen = set()
    ranked = np.argsort(-scores)
    out = []
    for i in ranked:
        i = int(i)
        j = int(indices[i])
        if j < 0 or scores[i] < 0:
            continue
        key = (min(i, j), max(i, j))
        if key in seen:
            continue
        seen.add(key)
        a, b = records[i], records[j]
        if cross_only and a["rhythm"] == b["rhythm"]:
            continue
        if not cross_only and a["rhythm"] != b["rhythm"]:
            continue
        out.append({
            "jaccard": _round(scores[i]),
            "a_rhythm": a["rhythm"],
            "b_rhythm": b["rhythm"],
            "a_tokens": list(a["tokens"]),
            "b_tokens": list(b["tokens"]),
        })
        if len(out) >= k:
            break
    return out


def redundancy_report(train, holdout=None) -> dict:
    index = {}
    for rec in train:
        for t in rec["tokens"]:
            index.setdefault(t, len(index))
    y = _multi_hot(train, index)
    rids = _rhythm_ids(train)
    within_j, within_i, cross_j, cross_i = _nn_jaccard(y, rids)

    ordered = [tuple(r["tokens"]) for r in train]
    ordered_dups = len(ordered) - len(set(ordered))
    bags = _bags(train)
    by_bag = collections.defaultdict(list)
    for i, bag in enumerate(bags):
        by_bag[bag].append(i)
    bag_dup_groups = [v for v in by_bag.values() if len(v) > 1]
    conflicts = []
    for group in bag_dup_groups:
        rhythms = {train[i]["rhythm"] for i in group}
        if len(rhythms) > 1:
            conflicts.append({
                "n": len(group),
                "rhythms": sorted(rhythms),
                "tokens": sorted(bags[group[0]]),
            })

    pair_count = collections.Counter()
    pair_rhythms = collections.defaultdict(collections.Counter)
    bigram_count = collections.Counter()
    for rec in train:
        toks = rec["tokens"]
        for i in range(len(toks)):
            for j in range(i + 1, len(toks)):
                key = tuple(sorted((toks[i], toks[j])))
                pair_count[key] += 1
                pair_rhythms[key][rec["rhythm"]] += 1
        for a, b in zip(toks, toks[1:]):
            bigram_count[(a, b, rec["rhythm"])] += 1

    repeated_pairs = []
    for (a, b), n in pair_count.most_common(15):
        repeated_pairs.append({
            "tokens": [a, b],
            "count": int(n),
            "rhythms": dict(pair_rhythms[(a, b)]),
            "n_rhythms": len(pair_rhythms[(a, b)]),
        })
    cross_pairs = [
        row for row in (
            {
                "tokens": [a, b],
                "count": int(n),
                "rhythms": dict(pair_rhythms[(a, b)]),
            }
            for (a, b), n in pair_count.items()
            if len(pair_rhythms[(a, b)]) >= 2
        )
    ]
    cross_pairs.sort(key=lambda r: -r["count"])

    per_rhythm = {}
    for r, name in enumerate(RHYTHMS):
        m = rids == r
        per_rhythm[name] = {
            "n": int(m.sum()),
            "within_nn": _dist_summary(within_j[m]),
        }

    holdout_vs_train = None
    if holdout:
        hold_index_rows = []
        # Jaccard of each holdout bag against train, same rhythm and any.
        h_y = np.zeros((len(holdout), len(index)), dtype=np.float32)
        unknown = 0
        for i, rec in enumerate(holdout):
            for t in rec["tokens"]:
                j = index.get(t)
                if j is None:
                    unknown += 1
                else:
                    h_y[i, j] = 1.0
        h_sizes = h_y.sum(axis=1)
        t_sizes = y.sum(axis=1)
        # chunked
        best = np.full(len(holdout), -1.0)
        best_same = np.full(len(holdout), -1.0)
        h_rids = _rhythm_ids(holdout)
        bs = 256
        for s in range(0, len(holdout), bs):
            e = min(s + bs, len(holdout))
            inter = h_y[s:e] @ y.T
            union = h_sizes[s:e, None] + t_sizes[None, :] - inter
            jac = inter / np.maximum(union, 1.0)
            best[s:e] = jac.max(axis=1)
            same = h_rids[s:e, None] == rids[None, :]
            masked = np.where(same, jac, -1.0)
            best_same[s:e] = masked.max(axis=1)
        holdout_vs_train = {
            "n": len(holdout),
            "unknown_token_hits": int(unknown),
            "nearest_train_any_rhythm": _dist_summary(best),
            "nearest_train_same_rhythm": _dist_summary(best_same),
        }

    return {
        "n": len(train),
        "exact_ordered_duplicate_sequences": int(ordered_dups),
        "exact_bag_duplicate_groups": len(bag_dup_groups),
        "exact_bag_duplicate_sequences": int(sum(len(g) for g in bag_dup_groups)),
        "exact_bag_cross_rhythm_conflicts": conflicts,
        "within_rhythm_nn": _dist_summary(within_j),
        "cross_rhythm_nn": _dist_summary(cross_j),
        "per_rhythm": per_rhythm,
        "worst_within_pairs": _pair_examples(train, within_j, within_i, 12, cross_only=False),
        "worst_cross_pairs": _pair_examples(train, cross_j, cross_i, 12, cross_only=True),
        "repeated_unordered_pairs": repeated_pairs,
        "repeated_cross_rhythm_pairs": cross_pairs[:12],
        "max_unordered_pair_count": int(pair_count.most_common(1)[0][1]) if pair_count else 0,
        "repeated_bigrams": [
            {"tokens": [a, b], "rhythm": rhythm, "count": int(n)}
            for (a, b, rhythm), n in bigram_count.most_common(12)
        ],
        "holdout_vs_train": holdout_vs_train,
    }


def hub_cap_report(train) -> dict:
    """Context counts and within-rhythm share. The low-context floor is 8.
    The hub cap is the other side: one token sitting in too many sequences
    of one rhythm, which is how a cone collapses onto a word.
    """
    contexts = collections.defaultdict(set)
    rhythm_hits = collections.defaultdict(collections.Counter)
    rhythm_n = collections.Counter(r["rhythm"] for r in train)
    for rec in train:
        key = tuple(rec["tokens"])
        for t in set(rec["tokens"]):
            contexts[t].add(key)
            rhythm_hits[t][rec["rhythm"]] += 1
    counts = {t: len(v) for t, v in contexts.items()}
    vals = np.array(list(counts.values()), dtype=np.float64)
    busiest = sorted(counts.items(), key=lambda kv: -kv[1])[:12]
    shares = []
    for t, by_r in rhythm_hits.items():
        for rhythm, n in by_r.items():
            shares.append((n / rhythm_n[rhythm], t, rhythm, n, rhythm_n[rhythm]))
    shares.sort(key=lambda row: -row[0])
    return {
        "n_tokens": len(counts),
        "context_min": int(vals.min()) if len(vals) else None,
        "context_p10": _round(np.quantile(vals, 0.10), 2) if len(vals) else None,
        "context_median": _round(np.median(vals), 2) if len(vals) else None,
        "context_p90": _round(np.quantile(vals, 0.90), 2) if len(vals) else None,
        "context_max": int(vals.max()) if len(vals) else None,
        "max_over_median": _round(float(vals.max() / np.median(vals)), 3) if len(vals) else None,
        "below_floor": int((vals < CONTEXT_FLOOR).sum()) if len(vals) else None,
        "busiest_tokens": [{"token": t, "contexts": int(n)} for t, n in busiest],
        "rhythm_share_max": _round(shares[0][0]) if shares else None,
        "rhythm_share_top": [
            {
                "token": t,
                "rhythm": rhythm,
                "share": _round(share),
                "count": int(n),
                "rhythm_n": int(rn),
            }
            for share, t, rhythm, n, rn in shares[:12]
        ],
        "per_rhythm_n": {name: int(rhythm_n[name]) for name in RHYTHMS},
    }


def seed_report(train) -> dict:
    keys = {(tuple(r["tokens"]), r["rhythm"]) for r in train}
    rows = []
    present = 0
    for rhythm, seqs in DEFAULT_RHYTHM_SEEDS.items():
        for seq in seqs:
            ok = (tuple(seq), rhythm) in keys
            present += int(ok)
            rows.append({"rhythm": rhythm, "tokens": list(seq), "in_train": ok})
    return {
        "n_seeds": len(rows),
        "in_train_same_rhythm": present,
        "missing": [r for r in rows if not r["in_train"]],
    }


def _unit(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=np.float64)
    n = np.linalg.norm(z, axis=1, keepdims=True)
    return z / np.clip(n, 1e-8, None)


def _spectrum(z: np.ndarray) -> dict:
    """Participation ratio and effective rank of the centered cloud.

    PR = (sum λ)^2 / sum λ^2. A single direction scores 1. A flat spectrum
    across d dimensions scores d. Effective rank is exp(entropy of the
    normalized eigenvalues), same idea, more sensitive to a long tail.
    """
    z = _unit(z)
    if len(z) < 2:
        return {"participation_ratio": None, "effective_rank": None, "n": int(len(z))}
    x = z - z.mean(axis=0, keepdims=True)
    singular = np.linalg.svd(x, compute_uv=False)
    lam = np.square(singular.astype(np.float64))
    total = float(lam.sum())
    if total <= 0:
        return {
            "participation_ratio": 0.0,
            "effective_rank": 0.0,
            "variance": 0.0,
            "n": int(len(z)),
        }
    lam = lam[lam > total * 1e-12]
    pr = float((lam.sum() ** 2) / np.square(lam).sum())
    p = lam / lam.sum()
    entropy = float(-(p * np.log(p)).sum())
    return {
        "participation_ratio": _round(pr),
        "effective_rank": _round(float(np.exp(entropy))),
        "spectrum_entropy": _round(entropy),
        "variance": _round(float(np.square(x).sum() / len(z))),
        "n": int(len(z)),
        "rank_used": int(len(lam)),
    }


def _density_entropy(values: np.ndarray, lo=-0.25, hi=1.0, bins=25) -> dict:
    v = np.asarray(values, dtype=np.float64)
    hist, edges = np.histogram(v, bins=np.linspace(lo, hi, bins + 1))
    total = int(hist.sum())
    if total == 0:
        return {"entropy": None, "normalized": None}
    p = hist[hist > 0] / total
    entropy = float(-(p * np.log(p)).sum())
    return {
        "entropy": _round(entropy),
        "normalized": _round(entropy / np.log(bins)),
        "bins": bins,
    }


def _indegree(nn: np.ndarray, n: int) -> dict:
    indeg = np.bincount(nn[nn >= 0], minlength=n)
    if n == 0:
        return {"max": 0}
    order = np.argsort(-indeg)
    top1 = max(1, n // 100)
    return {
        "max": int(indeg.max()),
        "p99": _round(np.quantile(indeg, 0.99), 2),
        "mean": _round(indeg.mean(), 3),
        "top_1pct_share": _round(float(indeg[order[:top1]].sum()) / n),
        "argmax": int(order[0]),
    }


def levelness_report(z: np.ndarray, records, token_rows=None, token_names=None) -> dict:
    """Landscape of one encoded corpus. z is (n, dim), already the encoder's
    unit output. token_rows, when given, is the corpus vocabulary's embedding
    rows in token_names order — hub-ness of the table, separate from the
    sequences.
    """
    z = _unit(z)
    rids = _rhythm_ids(records)
    index = {}
    for rec in records:
        for t in rec["tokens"]:
            index.setdefault(t, len(index))
    y = _multi_hot(records, index)
    sizes = y.sum(axis=1)

    global_spec = _spectrum(z)
    nn_cos = np.full(len(z), np.nan)
    knn_mean = np.full(len(z), np.nan)
    nn_local = np.full(len(z), -1, dtype=np.int64)
    own = np.full(len(z), np.nan)
    per = {}
    centroids = np.zeros((len(RHYTHMS), z.shape[1]), dtype=np.float64)
    for r, name in enumerate(RHYTHMS):
        idx = np.flatnonzero(rids == r)
        block = z[idx]
        if len(idx) == 0:
            continue
        c = block.mean(axis=0)
        c = c / (np.linalg.norm(c) + 1e-8)
        centroids[r] = c
        own[idx] = block @ c
        spec = _spectrum(block)
        if len(idx) >= 2:
            sim = block @ block.T
            np.fill_diagonal(sim, -2.0)
            k = min(KNN_K, len(idx) - 1)
            part = np.partition(sim, -k, axis=1)[:, -k:]
            knn_mean[idx] = part.mean(axis=1)
            nn_cos[idx] = sim.max(axis=1)
            nn_local[idx] = idx[sim.argmax(axis=1)]
            within_mean = float((sim.sum() - (-2.0) * len(idx)) / (len(idx) * (len(idx) - 1)))
        else:
            within_mean = None
        per[name] = {
            "n": int(len(idx)),
            "within_mean": _round(within_mean),
            "centroid_cos_mean": _round(own[idx].mean()),
            "centroid_cos_p50": _round(np.quantile(own[idx], 0.50)),
            "centroid_cos_p95": _round(np.quantile(own[idx], 0.95)),
            "centroid_cos_std": _round(own[idx].std()),
            "depth_gap_p95_p50": _round(
                float(np.quantile(own[idx], 0.95) - np.quantile(own[idx], 0.50))
            ),
            "knn_cos_p50": _round(np.quantile(knn_mean[idx], 0.50)) if len(idx) >= 2 else None,
            "knn_cos_p95": _round(np.quantile(knn_mean[idx], 0.95)) if len(idx) >= 2 else None,
            "nn_cos_p50": _round(np.quantile(nn_cos[idx], 0.50)) if len(idx) >= 2 else None,
            "nn_cos_p95": _round(np.quantile(nn_cos[idx], 0.95)) if len(idx) >= 2 else None,
            **{f"spectrum_{k}": v for k, v in spec.items() if k != "n"},
        }

    # Across: mean of per-rhythm-centroid cosines, off-diagonal, plus the
    # sequence-level across mean on a 40-cap is NOT used. Full centroid
    # cosine is the basin-separation number; sequence across is the cloud.
    cent = _unit(centroids)
    cent_sim = cent @ cent.T
    iu = np.triu_indices(len(RHYTHMS), k=1)
    across_centroids = float(cent_sim[iu].mean())

    hub = _indegree(nn_local, len(z))
    # Jaccard of the geometric nearest neighbor, so a tight hole can be
    # blamed on the text or not.
    nn_j = np.full(len(z), np.nan)
    valid = nn_local >= 0
    inter = (y[valid] * y[nn_local[valid]]).sum(axis=1)
    union = sizes[valid] + sizes[nn_local[valid]] - inter
    nn_j[valid] = inter / np.clip(union, 1e-8, None)
    tight = nn_cos >= TIGHT_COS
    unjust = tight & (nn_j < LOW_J)
    justified = tight & (nn_j >= NEAR_J)
    n = max(len(z), 1)

    token_hub = None
    if token_rows is not None and token_names is not None and len(token_names) >= 2:
        rows = _unit(np.asarray(token_rows, dtype=np.float64))
        sim = rows @ rows.T
        np.fill_diagonal(sim, -2.0)
        nn = sim.argmax(axis=1)
        indeg = np.bincount(nn, minlength=len(rows))
        order = np.argsort(-indeg)
        token_hub = {
            "n_tokens": len(token_names),
            "max_indegree": int(indeg.max()),
            "median_indegree": _round(np.median(indeg), 2),
            "p99_indegree": _round(np.quantile(indeg, 0.99), 2),
            "top": [
                {
                    "token": token_names[int(i)],
                    "indegree": int(indeg[int(i)]),
                    "share": _round(float(indeg[int(i)]) / len(rows)),
                    "mean_cos_of_those_neighbors": _round(
                        float(sim[nn == int(i), int(i)].mean()) if indeg[int(i)] else None
                    ),
                }
                for i in order[:8]
                if indeg[int(i)] > 0
            ],
        }

    finite_own = own[np.isfinite(own)]
    finite_nn = nn_cos[np.isfinite(nn_cos)]
    finite_k = knn_mean[np.isfinite(knn_mean)]
    return {
        "n": int(len(z)),
        "spectrum": global_spec,
        "centroid_cosine_offdiag_mean": _round(across_centroids),
        "centroid_cos_mean": _round(finite_own.mean()) if len(finite_own) else None,
        "centroid_cos_p50": _round(np.quantile(finite_own, 0.50)) if len(finite_own) else None,
        "centroid_cos_p95": _round(np.quantile(finite_own, 0.95)) if len(finite_own) else None,
        "depth_gap_p95_p50": _round(
            float(np.quantile(finite_own, 0.95) - np.quantile(finite_own, 0.50))
        ) if len(finite_own) else None,
        "nn_cos_p50": _round(np.quantile(finite_nn, 0.50)) if len(finite_nn) else None,
        "nn_cos_p95": _round(np.quantile(finite_nn, 0.95)) if len(finite_nn) else None,
        "knn8_cos_p50": _round(np.quantile(finite_k, 0.50)) if len(finite_k) else None,
        "knn8_cos_p95": _round(np.quantile(finite_k, 0.95)) if len(finite_k) else None,
        "density_entropy_nn_cos": _density_entropy(finite_nn),
        "sequence_hub": {k: v for k, v in hub.items() if k != "argmax"},
        "sequence_hub_token_hint": (
            list(records[hub["argmax"]]["tokens"]) if hub.get("argmax", -1) >= 0 else None
        ),
        "sequence_hub_rhythm": (
            records[hub["argmax"]]["rhythm"] if hub.get("argmax", -1) >= 0 else None
        ),
        "unjustified_collapse_rate": _round(float(unjust.sum()) / n),
        "unjustified_collapse_n": int(unjust.sum()),
        "justified_tight_rate": _round(float(justified.sum()) / n),
        "justified_tight_n": int(justified.sum()),
        "tight_neighbor_rate": _round(float(tight.sum()) / n),
        "per_rhythm": per,
        "token_hub": token_hub,
    }


def _headline(level: dict) -> dict:
    """The small set the gate actually compares. Everything else is context."""
    spec = level["spectrum"]
    return {
        "participation_ratio": spec.get("participation_ratio"),
        "effective_rank": spec.get("effective_rank"),
        "density_entropy": (level.get("density_entropy_nn_cos") or {}).get("normalized"),
        "knn8_cos_p50": level.get("knn8_cos_p50"),
        "knn8_cos_p95": level.get("knn8_cos_p95"),
        "depth_gap_p95_p50": level.get("depth_gap_p95_p50"),
        "centroid_cos_mean": level.get("centroid_cos_mean"),
        "sequence_hub_max_indegree": (level.get("sequence_hub") or {}).get("max"),
        "token_hub_max_indegree": (level.get("token_hub") or {}).get("max_indegree"),
        "unjustified_collapse_rate": level.get("unjustified_collapse_rate"),
        "justified_tight_rate": level.get("justified_tight_rate"),
    }


def _pair_count_max(records) -> int:
    pair_count = collections.Counter()
    for rec in records:
        toks = rec["tokens"]
        for i in range(len(toks)):
            for j in range(i + 1, len(toks)):
                pair_count[tuple(sorted((toks[i], toks[j])))] += 1
    if not pair_count:
        return 0
    return int(pair_count.most_common(1)[0][1])


def _post_fit_watch(level: dict | None) -> dict | None:
    """Same shape as the frozen cone gate, against the legible clean cloud.
    This one can see a neighborhood retighten. It is still a proposal.
    """
    if not level:
        return None
    cone = level.get("clean") or level
    h = _headline(cone)
    return {
        "against": "legible encoder, clean sequences, after a growth fit — not the admission gate",
        "participation_ratio_min": _round(0.98 * h["participation_ratio"]) if h["participation_ratio"] else None,
        "effective_rank_min": _round(0.98 * h["effective_rank"]) if h["effective_rank"] else None,
        "depth_gap_p95_p50_max": _round((h["depth_gap_p95_p50"] or 0) + 0.02),
        "knn8_cos_p50_max": _round((h["knn8_cos_p50"] or 0) + 0.01),
        "sequence_hub_indegree_max": int(np.ceil(1.10 * h["sequence_hub_max_indegree"])) if h["sequence_hub_max_indegree"] else None,
        "token_hub_indegree_max": h["token_hub_max_indegree"],
        "unjustified_collapse_rate_max": h["unjustified_collapse_rate"],
        "baseline": h,
    }


def propose_thresholds(redundancy: dict, hubs: dict, level: dict, legible: dict | None = None) -> dict:
    """Absolute numbers for the proposal. Samuel rules on them.

    The near-duplicate rate on this corpus is a debt (order-swapped bags),
    not a budget. A new batch does not get to match it.

    knn-cosine and density entropy on the frozen encoder are saturated:
    the typical neighbor is already cosine 1, so 'do not get tighter' cannot
    fail and is not a gate. They are reported, and they become a gate only
    on a post-fit encoder whose neighborhoods have actually opened.
    """
    cone = level.get("clean") or level
    h = _headline(cone)
    return {
        "status": "proposal — not ratified",
        "rules": PROPOSAL_RULES,
        "baseline_headline_cone": h,
        "baseline_near_dup_rate_not_a_budget": redundancy["within_rhythm_nn"]["frac_ge_0.80"],
        "absolute": {
            "exact_sequence_overlap_with_train": 0,
            "exact_bag_overlap_with_train": 0,
            "batch_within_near_dup_rate_max": 0.0,
            "batch_cross_rhythm_ge_0.80": 0,
            "context_floor": CONTEXT_FLOOR,
            "context_count_cap": hubs["context_max"],
            "rhythm_share_cap": hubs["rhythm_share_max"],
            "unordered_pair_count_cap": redundancy["max_unordered_pair_count"],
            "participation_ratio_min": _round(0.98 * h["participation_ratio"]) if h["participation_ratio"] else None,
            "effective_rank_min": _round(0.98 * h["effective_rank"]) if h["effective_rank"] else None,
            "depth_gap_p95_p50_max": _round((h["depth_gap_p95_p50"] or 0) + 0.02),
            "sequence_hub_indegree_max": int(np.ceil(1.10 * h["sequence_hub_max_indegree"])) if h["sequence_hub_max_indegree"] else None,
            "token_hub_indegree_max": h["token_hub_max_indegree"],
        },
        "not_binding_on_frozen_encoder": {
            "why": (
                "Frozen nearest-neighbor cosine is already ~1 and the density "
                "entropy of that spike is ~0. A cap at baseline+epsilon cannot "
                "fail. Do not gate admission on these until the encoder being "
                "measured has local room (the legible column does, barely)."
            ),
            "knn8_cos_p50": h["knn8_cos_p50"],
            "density_entropy": h["density_entropy"],
            "unjustified_collapse_rate": h["unjustified_collapse_rate"],
        },
        "post_fit_watch": _post_fit_watch(legible),
    }


def score_batch(train, batch, thresholds: dict, level_combined: dict | None = None) -> dict:
    """Stage A always. Stage B if level_combined is the landscape of train+batch
    encoded by the frozen checkpoint."""
    failures = []
    train_ordered = {tuple(r["tokens"]) for r in train}
    train_bags = {frozenset(r["tokens"]) for r in train}
    exact_seq = 0
    exact_bag = 0
    for rec in batch:
        if tuple(rec["tokens"]) in train_ordered:
            exact_seq += 1
        if frozenset(rec["tokens"]) in train_bags:
            exact_bag += 1
    if exact_seq:
        failures.append(f"{exact_seq} batch sequences already in train")
    if exact_bag:
        failures.append(f"{exact_bag} batch bags already in train")

    combined = list(train) + list(batch)
    index = {}
    for rec in combined:
        for t in rec["tokens"]:
            index.setdefault(t, len(index))
    y = _multi_hot(combined, index)
    rids = _rhythm_ids(combined)
    within_j, _, cross_j, _ = _nn_jaccard(y, rids)
    b0 = len(train)
    b_within = within_j[b0:]
    b_cross = cross_j[b0:]
    near_rate = float((b_within >= NEAR_J).mean()) if len(batch) else 0.0
    cross_n = int((b_cross >= CROSS_FORBID_J).sum()) if len(batch) else 0
    cap_near = thresholds["batch_within_near_dup_rate_max"]
    if cap_near is not None and near_rate > float(cap_near) + 1e-12:
        failures.append(
            f"batch within-rhythm near-dup rate {near_rate:.4f} > cap {cap_near}"
        )
    if cross_n:
        failures.append(f"{cross_n} batch sequences have cross-rhythm Jaccard >= {CROSS_FORBID_J}")

    # Context counts and rhythm share on the combined corpus.
    hubs = hub_cap_report(combined)
    # New tokens must clear the floor. Existing tokens must not exceed the cap.
    train_tokens = {t for r in train for t in r["tokens"]}
    contexts = collections.defaultdict(set)
    for rec in combined:
        key = tuple(rec["tokens"])
        for t in set(rec["tokens"]):
            contexts[t].add(key)
    under = sorted(t for t, v in contexts.items() if t not in train_tokens and len(v) < CONTEXT_FLOOR)
    if under:
        failures.append(
            f"{len(under)} new tokens below the context floor {CONTEXT_FLOOR}: {under[:8]}"
        )
    if hubs["context_max"] is not None and hubs["context_max"] > thresholds["context_count_cap"]:
        failures.append(
            f"context count {hubs['context_max']} exceeds cap {thresholds['context_count_cap']}"
        )
    if hubs["rhythm_share_max"] is not None and hubs["rhythm_share_max"] > thresholds["rhythm_share_cap"] + 1e-9:
        failures.append(
            f"rhythm share {hubs['rhythm_share_max']} exceeds cap {thresholds['rhythm_share_cap']}"
        )
    pair_cap = thresholds.get("unordered_pair_count_cap")
    if pair_cap is not None:
        hottest = _pair_count_max(combined)
        if hottest > pair_cap:
            failures.append(f"unordered pair count {hottest} exceeds cap {pair_cap}")

    observed_level = None
    if level_combined is not None:
        observed_level = _headline(level_combined)
        base = thresholds
        # Cone metrics, not the saturated nearest-neighbor cosine.
        cone = level_combined.get("clean") or level_combined
        observed_level = _headline(cone)
        checks = [
            ("participation_ratio", observed_level["participation_ratio"], base["participation_ratio_min"], "min"),
            ("effective_rank", observed_level["effective_rank"], base["effective_rank_min"], "min"),
            ("depth_gap_p95_p50", observed_level["depth_gap_p95_p50"], base["depth_gap_p95_p50_max"], "max"),
            ("sequence_hub_max_indegree", observed_level["sequence_hub_max_indegree"], base["sequence_hub_indegree_max"], "max"),
            ("token_hub_max_indegree", observed_level["token_hub_max_indegree"], base["token_hub_indegree_max"], "max"),
        ]
        for name, got, bound, direction in checks:
            if got is None or bound is None:
                failures.append(f"{name} missing (got {got}, bound {bound})")
                continue
            if direction == "min" and got < bound - 1e-9:
                failures.append(f"{name} {got} < {bound}")
            if direction == "max" and got > bound + 1e-9:
                failures.append(f"{name} {got} > {bound}")

    return {
        "admitted": len(failures) == 0,
        "failures": failures,
        "batch_n": len(batch),
        "exact_sequence_overlap": exact_seq,
        "exact_bag_overlap": exact_bag,
        "within_near_dup_rate": _round(near_rate),
        "cross_rhythm_ge_0.80": cross_n,
        "combined_context_max": hubs["context_max"],
        "combined_rhythm_share_max": hubs["rhythm_share_max"],
        "level_headline": observed_level,
        "note": "proposal thresholds, not a ratified law",
    }


def _encode(gen, token_lists, batch=256) -> np.ndarray:
    gen.eval()
    out = []
    for i in range(0, len(token_lists), batch):
        out.append(gen.encode_batch(token_lists[i:i + batch]))
    return np.concatenate(out, axis=0).astype(np.float32)


def _token_table(gen, vocab):
    """Corpus-token rows only, after the pipeline's canonical name."""
    pipe = gen.registry.pipeline
    names = []
    rows = []
    missing = []
    weight = gen.embedding.weight.detach().cpu().float()
    for t in vocab:
        canon = pipe.process(t).token
        st = gen.registry.symbols.get(canon)
        if st is None:
            missing.append(t)
            continue
        names.append(t)
        rows.append(weight[st.address].numpy())
    if not rows:
        return None, [], missing
    return np.stack(rows), names, missing


def _load_generator(weights: Path, ecology: Path):
    import torch
    from agents.generator import Generator
    gen = Generator(vocab_size=8192, dim=DIM, depth=4, heads=4, device="cpu")
    gen.load_checkpoint(str(weights), str(ecology))
    gen.eval()
    return gen


def _orphan_count(gen, vocab) -> int:
    pipe = gen.registry.pipeline
    ecology = set(gen.registry.symbols)
    return sum(1 for t in vocab if pipe.process(t).token not in ecology)


def frozen_trained_mask(records) -> list:
    """True when every token in the sequence already has a row in the frozen
    ecology. Orphan sequences sit outside the cones and pull a full-set mean
    off the number Phase 0 published. The mask is the frozen ecology either way,
    so the legible column is sliced on the same sequences.
    """
    gen = _load_generator(FROZEN_W, FROZEN_E)
    pipe = gen.registry.pipeline
    ecology = set(gen.registry.symbols)
    return [
        not any(pipe.process(t).token not in ecology for t in rec["tokens"])
        for rec in records
    ]


def encode_level(records, weights: Path, ecology: Path, register_missing: bool, clean_mask=None) -> dict:
    before = _file_id(weights), _file_id(ecology)
    gen = _load_generator(weights, ecology)
    vocab = sorted({t for r in records for t in r["tokens"]})
    orphans = _orphan_count(gen, vocab)
    if register_missing:
        pipe = gen.registry.pipeline
        ecology_names = set(gen.registry.symbols)
        for t in vocab:
            if pipe.process(t).token not in ecology_names:
                gen.registry.register(t)
        gen._ensure_embedding_capacity()
    z = _encode(gen, [r["tokens"] for r in records])
    rows, names, missing = _token_table(gen, vocab)
    level = levelness_report(z, records, token_rows=rows, token_names=names)
    level["orphan_tokens_before_register"] = int(orphans)
    level["token_rows_missing"] = missing
    if clean_mask is not None:
        idx = [i for i, c in enumerate(clean_mask) if c]
        level["clean_n"] = len(idx)
        if idx and len(idx) != len(records):
            level["clean"] = levelness_report(
                z[idx], [records[i] for i in idx], token_rows=rows, token_names=names,
            )
    after = _file_id(weights), _file_id(ecology)
    if after != before:
        raise RuntimeError(f"checkpoint changed while measuring {weights}")
    level["checkpoint_untouched"] = True
    level["weights"] = str(weights).replace("\\", "/")
    return level


def _self_check() -> None:
    records = [
        {"tokens": ["a", "b"], "rhythm": "stabilize"},
        {"tokens": ["b", "a"], "rhythm": "stabilize"},  # exact bag, different order
        {"tokens": ["a", "b", "c"], "rhythm": "stabilize"},  # near
        {"tokens": ["a", "b"], "rhythm": "dream"},  # cross-rhythm clone
        {"tokens": ["q", "z"], "rhythm": "explore"},
        {"tokens": ["q", "z", "y"], "rhythm": "explore"},
    ]
    rep = redundancy_report(records)
    # ["a","b"] is in stabilize and in dream: one ordered collision, and the
    # bag group also swallows the order-swapped stabilize row.
    if rep["exact_ordered_duplicate_sequences"] != 1:
        raise AssertionError(f"ordered dups {rep['exact_ordered_duplicate_sequences']}")
    if rep["exact_bag_duplicate_groups"] != 1:
        raise AssertionError(f"bag groups {rep['exact_bag_duplicate_groups']}")
    if not rep["exact_bag_cross_rhythm_conflicts"]:
        raise AssertionError("expected a cross-rhythm bag conflict")
    if rep["within_rhythm_nn"]["max"] is None or rep["within_rhythm_nn"]["max"] < 0.99:
        raise AssertionError(f"within nn max {rep['within_rhythm_nn']}")

    # One point repeated: participation ratio ~ 0. Orthogonal axes: higher.
    eye = np.eye(8, dtype=np.float64)
    piled = np.repeat(eye[:1], 16, axis=0)
    pr_pile = _spectrum(piled)["participation_ratio"]
    pr_eye = _spectrum(eye)["participation_ratio"]
    if pr_pile is None or pr_pile > 1.05:
        raise AssertionError(f"piled PR {pr_pile}")
    if pr_eye is None or pr_eye < 5:
        raise AssertionError(f"eye PR {pr_eye}")

    # A magnet: 10 copies of e0's neighbor sitting on e0.
    rows = np.vstack([eye[0], np.repeat(eye[0][None, :] + eye[1] * 0.01, 10, axis=0)])
    # sequence hub via levelness: everyone near the first of the copies
    recs = [{"tokens": ["t"], "rhythm": "stabilize"} for _ in range(len(rows))]
    # give them distinct tokens so multi-hot isn't identical... not required
    level = levelness_report(rows, recs)
    if level["sequence_hub"]["max"] < 2:
        raise AssertionError(f"expected a hub, got {level['sequence_hub']}")
    _log("corpus_health self-check ok")


def main() -> int:
    ap = argparse.ArgumentParser(description="Corpus redundancy and levelness yardstick")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--batch", type=Path, default=None, help="candidate JSONL to score against the proposal")
    ap.add_argument("--no-encoder", action="store_true", help="stage A only")
    ap.add_argument("--legible", type=Path, default=LEGIBLE_W)
    ap.add_argument("--legible-ecology", type=Path, default=LEGIBLE_E)
    ap.add_argument("--out", type=Path, default=METRICS)
    args = ap.parse_args()

    if args.self_check:
        _self_check()
        return 0

    train = load_corpus(TRAIN_PATH)
    holdout = load_corpus(HOLDOUT_PATH)
    _log(f"corpus v{corpus_version()}  train={len(train)} holdout={len(holdout)}")
    _log("redundancy ...")
    red = redundancy_report(train, holdout)
    hubs = hub_cap_report(train)
    seeds = seed_report(train)
    _log(
        f"  within NN Jaccard p50={red['within_rhythm_nn']['p50']} "
        f"frac>=0.80={red['within_rhythm_nn']['frac_ge_0.80']} "
        f"exact bag groups={red['exact_bag_duplicate_groups']} "
        f"cross frac>=0.80={red['cross_rhythm_nn']['frac_ge_0.80']}"
    )
    _log(
        f"  contexts min={hubs['context_min']} median={hubs['context_median']} "
        f"max={hubs['context_max']}  rhythm-share max={hubs['rhythm_share_max']}"
    )
    _log(f"  seeds in train {seeds['in_train_same_rhythm']}/{seeds['n_seeds']}")

    level_frozen = None
    level_legible = None
    if not args.no_encoder:
        if not FROZEN_W.exists():
            raise RuntimeError(f"missing {FROZEN_W}")
        _log("levelness, frozen encoder ...")
        clean_mask = frozen_trained_mask(train)
        _log(f"  clean sequences (no orphan token): {sum(clean_mask)}/{len(train)}")
        level_frozen = encode_level(
            train, FROZEN_W, FROZEN_E, register_missing=True, clean_mask=clean_mask,
        )
        h = _headline(level_frozen)
        _log(
            f"  frozen PR={h['participation_ratio']} erank={h['effective_rank']} "
            f"knn_p50={h['knn8_cos_p50']} depth_gap={h['depth_gap_p95_p50']} "
            f"seq_hub={h['sequence_hub_max_indegree']} tok_hub={h['token_hub_max_indegree']} "
            f"unjustified={h['unjustified_collapse_rate']}"
        )
        if args.legible.exists() and args.legible_ecology.exists():
            _log("levelness, legible encoder ...")
            level_legible = encode_level(
                train, args.legible, args.legible_ecology,
                register_missing=False, clean_mask=clean_mask,
            )
            h2 = _headline(level_legible)
            _log(
                f"  legible PR={h2['participation_ratio']} erank={h2['effective_rank']} "
                f"knn_p50={h2['knn8_cos_p50']} depth_gap={h2['depth_gap_p95_p50']} "
                f"seq_hub={h2['sequence_hub_max_indegree']} tok_hub={h2['token_hub_max_indegree']} "
                f"unjustified={h2['unjustified_collapse_rate']}"
            )
        else:
            _log("  legible checkpoint not present; frozen column only")

    proposal = None
    if level_frozen is not None:
        proposal = propose_thresholds(red, hubs, level_frozen, level_legible)

    batch_score = None
    if args.batch is not None:
        if proposal is None:
            raise RuntimeError("batch scoring needs the frozen encoder (drop --no-encoder)")
        batch = load_corpus(args.batch)
        _log(f"scoring batch {args.batch} n={len(batch)}")
        combined_records = list(train) + list(batch)
        level_combined = encode_level(
            combined_records, FROZEN_W, FROZEN_E, register_missing=True,
            clean_mask=frozen_trained_mask(combined_records),
        )
        batch_score = score_batch(train, batch, proposal["absolute"], level_combined)
        _log(f"  admitted={batch_score['admitted']} failures={batch_score['failures']}")

    report = {
        "corpus": corpus_version(),
        "train_n": len(train),
        "holdout_n": len(holdout),
        "redundancy": red,
        "hub_cap": hubs,
        "seeds": seeds,
        "levelness_frozen": level_frozen,
        "levelness_legible": level_legible,
        "proposal": proposal,
        "batch_score": batch_score,
        "gate_reference_encoder": "frozen 5-rhythm checkpoint, not the legible one",
        "field": "not stepped",
    }
    if args.batch is None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(_jsonable(report), indent=2), encoding="utf-8")
        _log(f"WROTE {args.out}")
    else:
        _log(json.dumps(_jsonable(batch_score), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
