"""Score order-aware checkpoints against the mean-pool completion baseline.

Three questions, same instrument as docs/findings/2026-09-23-completion-objective.md
where the question is the same one:

  (a) held-out completion, fresh linear probe, plus the co-trained head
  (b) order: reverse-cosine (a bag is ~1), a position probe, and a bag-oracle
      that already knows the token set and only lacks order
  (c) participation and the Phase 0 mouth (recall@8, median rank)

The published completion checkpoints are loaded from the main checkout,
read only, and only on full lines. ``<BLANK>`` is never registered into
that ecology.

    python -m tools.order.measure
"""

from __future__ import annotations

import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from agents.decoder import TokenDecoder
from tools.completion.geometry import (
    encode_texts,
    load_generator,
    population,
    separability,
)
from tools.completion.live_guard import sha256
from tools.completion.measure import (
    completion_scores,
    fit_rhythm_probe,
    median_true_rank,
    unigram_baseline,
)
from tools.order.corpus import load_jsonl
from tools.order.encoder import READOUTS, load_checkpoint
from tools.order.guard import MAIN, REPO, SCRATCH, assert_live_intact, assert_safe_output
from training.completion import pack_targets
from training.corpus import load_corpus
from training.decoder_training import _vocab_from, evaluate, train_decoder

LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-order-aware"


def _json_default(obj):
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"not JSON serializable: {type(obj)}")


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _unit_rows(Z: np.ndarray) -> np.ndarray:
    Z = np.asarray(Z, dtype=np.float64)
    n = np.linalg.norm(Z, axis=1, keepdims=True)
    return Z / np.maximum(n, 1e-12)


def _norms(Z: np.ndarray) -> dict:
    n = np.linalg.norm(np.asarray(Z, dtype=np.float64), axis=1)
    return {
        "norm_mean": round(float(n.mean()), 6),
        "norm_min": round(float(n.min()), 6),
        "norm_max": round(float(n.max()), 6),
        "dim": int(Z.shape[1]),
    }


def _reverse_cosine(encode, lines) -> dict:
    kept = [list(tl) for tl in lines if len(tl) >= 2 and list(tl) != list(reversed(tl))]
    if not kept:
        return {"n": 0}
    a = _unit_rows(encode(kept))
    b = _unit_rows(encode([list(reversed(tl)) for tl in kept]))
    cos = np.sum(a * b, axis=1)
    return {
        "n": int(len(kept)),
        "mean_cosine": round(float(cos.mean()), 4),
        "median_cosine": round(float(np.median(cos)), 4),
        "frac_cosine_gt_0.99": round(float(np.mean(cos > 0.99)), 4),
        "p10_cosine": round(float(np.quantile(cos, 0.10)), 4),
    }


def _word_ce(logits: torch.Tensor, rows, index, device: str) -> float:
    target = pack_targets([r["target_dist"] for r in rows], index, device)
    return float((-(target * torch.log_softmax(logits, dim=-1)).sum(-1)).mean())


def _fit_completion(Xtr, rows_tr, Xho, rows_ho, vocab, epochs=40, lr=1e-2, seed=42):
    """Fresh linear softmax. Returns scores and the holdout logits."""
    _seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    index = {t: i for i, t in enumerate(vocab)}
    layer = nn.Linear(Xtr.shape[1], len(vocab)).to(device)
    opt = torch.optim.Adam(layer.parameters(), lr=lr)
    Ptr = pack_targets([r["target_dist"] for r in rows_tr], index, device)
    Xtr_t = torch.tensor(np.asarray(Xtr), dtype=torch.float32, device=device)
    layer.train()
    n = len(rows_tr)
    for _epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        for start in range(0, n, 256):
            ix = perm[start:start + 256]
            opt.zero_grad()
            loss = -(Ptr[ix] * torch.log_softmax(layer(Xtr_t[ix]), dim=-1)).sum(-1).mean()
            loss.backward()
            opt.step()
    layer.eval()
    with torch.no_grad():
        tr_logits = layer(Xtr_t)
        ho_logits = layer(torch.tensor(np.asarray(Xho), dtype=torch.float32, device=device))
    train_scores = completion_scores(tr_logits, rows_tr, vocab)
    hold_scores = completion_scores(ho_logits, rows_ho, vocab)
    train_scores["ce"] = round(_word_ce(tr_logits, rows_tr, index, device), 4)
    hold_scores["ce"] = round(_word_ce(ho_logits, rows_ho, index, device), 4)
    return {"train": train_scores, "holdout": hold_scores}, ho_logits, index, device


def _slice_scores(logits, rows, vocab, index, device, mask) -> dict | None:
    keep = [i for i, flag in enumerate(mask) if flag]
    if not keep:
        return None
    sub_rows = [rows[i] for i in keep]
    sub_logits = logits[keep]
    scores = completion_scores(sub_logits, sub_rows, vocab)
    scores["ce"] = round(_word_ce(sub_logits, sub_rows, index, device), 4)
    return scores


@torch.no_grad()
def _cotrained(enc, head, rows, vocab) -> dict:
    device = enc.device_name
    logits = []
    for start in range(0, len(rows), 256):
        batch = rows[start:start + 256]
        h = torch.tensor(
            enc.encode_token_lists([r["context"] for r in batch]),
            dtype=torch.float32,
            device=device,
        )
        logits.append(head(h))
    stacked = torch.cat(logits, dim=0)
    index = {t: i for i, t in enumerate(vocab)}
    scores = completion_scores(stacked, rows, vocab)
    scores["ce"] = round(_word_ce(stacked, rows, index, device), 4)
    return scores


def _examples(lines, vocab_index):
    """(line_index, position, token) for every occupied slot whose token is known."""
    out = []
    for i, toks in enumerate(lines):
        for pos, tok in enumerate(toks):
            j = vocab_index.get(tok)
            if j is None:
                continue
            out.append((i, pos, j, tok))
    return out


def _fit_classifier(X, y, n_class, hidden, epochs, lr, seed):
    _seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    D = X.shape[1]
    if hidden:
        layer = nn.Sequential(
            nn.Linear(D, hidden),
            nn.GELU(),
            nn.Linear(hidden, n_class),
        ).to(device)
    else:
        layer = nn.Linear(D, n_class).to(device)
    opt = torch.optim.Adam(layer.parameters(), lr=lr)
    Xt = torch.tensor(np.asarray(X), dtype=torch.float32, device=device)
    yt = torch.tensor(y, dtype=torch.long, device=device)
    layer.train()
    n = len(y)
    for _epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        for start in range(0, n, 256):
            ix = perm[start:start + 256]
            opt.zero_grad()
            loss = F.cross_entropy(layer(Xt[ix]), yt[ix])
            loss.backward()
            opt.step()
    layer.eval()
    return layer, device


def _slot_scores(layer, device, Z, lines, examples, index) -> dict:
    """Top-1 over the whole vocab, and top-1 restricted to the line's own tokens."""
    if not examples:
        return {"n": 0}
    xs = np.stack([Z[i] for i, _p, _j, _t in examples], axis=0)
    with torch.no_grad():
        logits = layer(torch.tensor(xs, dtype=torch.float32, device=device)).float().cpu()
    top1 = 0
    inline = 0
    by_pos_hit = Counter()
    by_pos_n = Counter()
    for row, (i, pos, j, _tok) in enumerate(examples):
        pred = int(logits[row].argmax())
        top1 += int(pred == j)
        allow = sorted({index[t] for t in lines[i] if t in index})
        masked = logits[row].clone()
        ban = torch.ones(masked.shape[0], dtype=torch.bool)
        ban[allow] = False
        masked[ban] = -1e30
        inline += int(int(masked.argmax()) == j)
        by_pos_n[pos] += 1
        by_pos_hit[pos] += int(pred == j)
    n = len(examples)
    return {
        "n": n,
        "top1": round(top1 / n, 4),
        "in_line": round(inline / n, 4),
        "by_pos_top1": {
            str(k): round(by_pos_hit[k] / by_pos_n[k], 4) for k in sorted(by_pos_n)
        },
        "by_pos_n": {str(k): by_pos_n[k] for k in sorted(by_pos_n)},
    }


def _positional_unigram(train_lines, hold_lines, index) -> dict:
    counts: dict[int, Counter] = defaultdict(Counter)
    for toks in train_lines:
        for pos, tok in enumerate(toks):
            if tok in index:
                counts[pos][tok] += 1
    hit = 0
    n = 0
    for toks in hold_lines:
        for pos, tok in enumerate(toks):
            if tok not in index or pos not in counts:
                continue
            guess = counts[pos].most_common(1)[0][0]
            hit += int(guess == tok)
            n += 1
    return {"n": n, "top1": round(hit / n, 4) if n else None}


def _bag_oracle(train_lines, hold_lines) -> dict:
    """Best assignment of the true bag onto slots, by train position prior.

    Enumerates permutations (lines are length <= 4). This is what perfect
    knowledge of WHICH tokens, and none of WHERE, can do. A vector probe
    that does not beat it has not shown order beyond the bag.
    """
    prior: dict[str, Counter] = defaultdict(Counter)
    for toks in train_lines:
        for pos, tok in enumerate(toks):
            prior[tok][pos] += 1
    hit = 0
    n = 0
    n_lines = 0
    for toks in hold_lines:
        L = len(toks)
        if L < 2 or L > 7:
            continue
        n_lines += 1
        best = None
        best_score = -1e300
        for perm in itertools.permutations(range(L)):
            score = 0.0
            for pos, src in enumerate(perm):
                score += math.log(prior[toks[src]][pos] + 1.0)
            if score > best_score:
                best_score = score
                best = perm
        for pos in range(L):
            n += 1
            hit += int(toks[best[pos]] == toks[pos])
    return {
        "n_positions": n,
        "n_lines": n_lines,
        "in_line": round(hit / n, 4) if n else None,
    }


def _per_position(Ztr, train_lines, tr_by, Zho, hold_lines, ho_by, n_class, index, hidden, epochs, lr):
    """One classifier per slot. A shared classifier cannot be told which slot is being asked."""
    positions = sorted(set(tr_by) & set(ho_by))
    parts = []
    train_parts = []
    for pos in positions:
        tr = tr_by[pos]
        ho = ho_by[pos]
        X = np.stack([Ztr[i] for i, _p, _j, _t in tr], axis=0)
        y = [j for _i, _p, j, _t in tr]
        layer, device = _fit_classifier(X, y, n_class, hidden=hidden, epochs=epochs, lr=lr, seed=42)
        train_parts.append(_slot_scores(layer, device, Ztr, train_lines, tr, index))
        parts.append(_slot_scores(layer, device, Zho, hold_lines, ho, index))
        print(f"  slot pos {pos}  hold in-line {parts[-1]['in_line']}  n {parts[-1]['n']}", flush=True)

    def _micro(chunks, key):
        num = 0.0
        den = 0
        for chunk in chunks:
            num += chunk[key] * chunk["n"]
            den += chunk["n"]
        return round(num / den, 4) if den else None

    return {
        "holdout_top1_micro": _micro(parts, "top1"),
        "holdout_in_line_micro": _micro(parts, "in_line"),
        "train_top1_micro": _micro(train_parts, "top1"),
        "train_in_line_micro": _micro(train_parts, "in_line"),
        "by_pos_holdout": {str(positions[i]): parts[i] for i in range(len(positions))},
    }


def _order_block(encode, Ztr, train_lines, Zho, hold_lines, surface) -> dict:
    index = {t: i for i, t in enumerate(surface)}
    tr_ex = _examples(train_lines, index)
    ho_ex = _examples(hold_lines, index)
    tr_by = defaultdict(list)
    ho_by = defaultdict(list)
    for ex in tr_ex:
        tr_by[ex[1]].append(ex)
    for ex in ho_ex:
        ho_by[ex[1]].append(ex)
    print("  linear slot probes", flush=True)
    linear = _per_position(
        Ztr, train_lines, tr_by, Zho, hold_lines, ho_by,
        len(surface), index, hidden=0, epochs=40, lr=1e-2,
    )
    print("  mlp slot probes", flush=True)
    mlp = _per_position(
        Ztr, train_lines, tr_by, Zho, hold_lines, ho_by,
        len(surface), index, hidden=256, epochs=20, lr=1e-3,
    )
    return {
        "reverse_cosine_holdout": _reverse_cosine(encode, hold_lines),
        "reverse_cosine_train": _reverse_cosine(encode, train_lines),
        "positional_unigram_holdout": _positional_unigram(train_lines, hold_lines, index),
        "bag_oracle_holdout": _bag_oracle(train_lines, hold_lines),
        "linear": linear,
        "mlp_hidden256": mlp,
    }


def _legibility(encode, train_records, hold_records, dim: int) -> dict:
    _seed(42)
    vocab = _vocab_from(train_records)
    Xtr = torch.tensor(encode([r["tokens"] for r in train_records]), dtype=torch.float32)
    Xho = torch.tensor(encode([r["tokens"] for r in hold_records]), dtype=torch.float32)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    Xtr = Xtr.to(device)
    Xho = Xho.to(device)
    ttr = [r["tokens"] for r in train_records]
    tho = [r["tokens"] for r in hold_records]
    dec = TokenDecoder(vocab, dim=dim, hidden=256, device=device)
    train_decoder(None, dec, Xtr, ttr, epochs=20)
    tr = evaluate(dec, Xtr, ttr, top_k=8)
    ho = evaluate(dec, Xho, tho, top_k=8)
    tr["median_true_rank"] = median_true_rank(dec, Xtr, ttr)
    ho["median_true_rank"] = median_true_rank(dec, Xho, tho)
    return {"train": tr, "holdout": ho}


def _alignment(enc, lines) -> dict | None:
    if not hasattr(enc, "encode_parts"):
        return None
    _field, bag, ordered = enc.encode_parts(lines)
    if bag is None or ordered is None:
        return None
    bag_u = _unit_rows(bag)
    ord_u = _unit_rows(ordered)
    cos = np.sum(bag_u * ord_u, axis=1)
    return {
        "n": int(len(lines)),
        "bag_order_cosine_mean": round(float(cos.mean()), 4),
        "bag_order_cosine_median": round(float(np.median(cos)), 4),
    }


def measure_order(blob_path: Path, live_train, live_hold, comp_train, comp_hold, content) -> dict:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    enc, head, blob = load_checkpoint(str(blob_path), device)
    if head.out_features != len(content) or blob["head_vocab"] != content:
        raise SystemExit(f"head vocab drifted: {blob_path}")
    print(f"=== {blob['readout']} dim {blob['dim']} ===", flush=True)
    train_lines = [r["tokens"] for r in live_train]
    hold_lines = [r["tokens"] for r in live_hold]
    Ztr = enc.encode_token_lists(train_lines)
    Zho = enc.encode_token_lists(hold_lines)
    ytr = [r["rhythm"] for r in live_train]
    yho = [r["rhythm"] for r in live_hold]
    pop = population(Zho)
    sep = separability(Zho, yho)
    rhythm = fit_rhythm_probe(Ztr, ytr, Zho, yho)
    print(
        f"PR {pop['participation_ratio']}  eff {pop['eff_rank_512cap']}  "
        f"rhythm {rhythm['holdout_acc']}  norm {_norms(Zho)['norm_mean']}",
        flush=True,
    )
    Xctx_tr = enc.encode_token_lists([r["context"] for r in comp_train])
    Xctx_ho = enc.encode_token_lists([r["context"] for r in comp_hold])
    print("fitting completion probe ...", flush=True)
    probe, ho_logits, index, probe_device = _fit_completion(
        Xctx_tr, comp_train, Xctx_ho, comp_hold, content,
    )
    conflict = _slice_scores(
        ho_logits, comp_hold, content, index, probe_device,
        [bool(r.get("train_order_conflict")) for r in comp_hold],
    )
    print(
        f"probe hold peaked {probe['holdout']['peaked_top1']}  ce {probe['holdout']['ce']}",
        flush=True,
    )
    cotrained = {
        "train": _cotrained(enc, head, comp_train, content),
        "holdout": _cotrained(enc, head, comp_hold, content),
    }
    print(
        f"cotrained hold peaked {cotrained['holdout']['peaked_top1']}  "
        f"ce {cotrained['holdout']['ce']}",
        flush=True,
    )
    print("order probes ...", flush=True)
    # Surface vocab only. PAD and BLANK are encoder-internal and never line tokens.
    order = _order_block(
        enc.encode_token_lists, Ztr, train_lines, Zho, hold_lines, blob["surface_vocab"],
    )
    print(
        f"reverse cos {order['reverse_cosine_holdout']['mean_cosine']}  "
        f"mlp in-line {order['mlp_hidden256']['holdout_in_line_micro']}  "
        f"oracle {order['bag_oracle_holdout']['in_line']}",
        flush=True,
    )
    print("phase-0 mouth ...", flush=True)
    mouth = _legibility(enc.encode_token_lists, live_train, live_hold, blob["dim"])
    print(f"legibility holdout {mouth['holdout']}", flush=True)
    result = {
        "name": f"{blob['readout']}{blob['dim']}",
        "readout": blob["readout"],
        "dim": blob["dim"],
        "checkpoint": str(blob_path),
        "checkpoint_sha256": sha256(blob_path),
        "field_norm": _norms(Zho),
        "population_live_holdout": pop,
        "separability_live_holdout": sep,
        "rhythm_linear_probe": rhythm,
        "frozen_completion_probe": probe,
        "completion_order_conflict_slice": conflict,
        "cotrained_completion": cotrained,
        "order": order,
        "term_alignment_holdout": _alignment(enc, hold_lines),
        "legibility": mouth,
    }
    del enc, head
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return result


def measure_published(dim: int, live_train, live_hold) -> dict:
    weights = MAIN / f"data/checkpoints/generator_weights_completion_{dim}_emb.pt"
    ecology = MAIN / f"data/checkpoints/generator_ecology_completion_{dim}_emb.json"
    if not weights.is_file():
        raise SystemExit(f"missing published checkpoint {weights}")
    before = sha256(weights)
    print(f"=== published mean-pool dim {dim} ===", flush=True)
    gen = load_generator(dim, str(weights), str(ecology))
    train_lines = [r["tokens"] for r in live_train]
    hold_lines = [r["tokens"] for r in live_hold]

    def encode(lines):
        return encode_texts(gen, lines)

    Ztr = encode(train_lines)
    Zho = encode(hold_lines)
    pop = population(Zho)
    sep = separability(Zho, [r["rhythm"] for r in live_hold])
    rhythm = fit_rhythm_probe(
        Ztr, [r["rhythm"] for r in live_train], Zho, [r["rhythm"] for r in live_hold],
    )
    print(
        f"PR {pop['participation_ratio']}  eff {pop['eff_rank_512cap']}  "
        f"rhythm {rhythm['holdout_acc']}",
        flush=True,
    )
    surface = sorted({t for rec in live_train for t in rec["tokens"]})
    print("order probes ...", flush=True)
    order = _order_block(encode, Ztr, train_lines, Zho, hold_lines, surface)
    print(
        f"reverse cos {order['reverse_cosine_holdout']['mean_cosine']}  "
        f"mlp in-line {order['mlp_hidden256']['holdout_in_line_micro']}",
        flush=True,
    )
    print("phase-0 mouth ...", flush=True)
    mouth = _legibility(encode, live_train, live_hold, dim)
    print(f"legibility holdout {mouth['holdout']}", flush=True)
    after = sha256(weights)
    if after != before:
        raise SystemExit("published checkpoint hash changed during measure")
    # ecology is hashed too; load_generator must not have flushed it.
    return {
        "name": f"published_mean_pool{dim}",
        "readout": "published_mean_pool",
        "dim": dim,
        "checkpoint": str(weights),
        "checkpoint_sha256": after,
        "field_norm": _norms(Zho),
        "population_live_holdout": pop,
        "separability_live_holdout": sep,
        "rhythm_linear_probe": rhythm,
        "order": order,
        "legibility": mouth,
        "note": (
            "Embeddings trained, transformer frozen, mean-pool. "
            "Completion rows for this checkpoint were sorted content bags; "
            "it is not re-scored on positioned blanks."
        ),
    }


def main() -> int:
    live = assert_live_intact()
    live_train = load_corpus(MAIN / "data" / "corpus" / "rhythm_train.jsonl")
    live_hold = load_corpus(MAIN / "data" / "corpus" / "rhythm_holdout.jsonl")
    comp_train = load_jsonl(SCRATCH / "order_train.jsonl")
    comp_hold = load_jsonl(SCRATCH / "order_holdout.jsonl")
    content = sorted({w for r in comp_train for w in r["targets"]})
    base = unigram_baseline(comp_train, comp_hold, content)
    print(
        f"ordered-row unigram peaked_top1 {base['peaked_top1']}  ce {base['ce']}  "
        f"|V|={len(content)}",
        flush=True,
    )
    results = []
    for dim in (128, 256):
        results.append(measure_published(dim, live_train, live_hold))
    for dim in (128, 256):
        for readout in READOUTS:
            path = REPO / "data" / "checkpoints" / f"order_encoder_{readout}_{dim}.pt"
            if not path.is_file():
                print(f"skip missing {path}", flush=True)
                continue
            results.append(
                measure_order(path, live_train, live_hold, comp_train, comp_hold, content)
            )
    payload = {
        "content_vocab": len(content),
        "chance_peaked_top1": round(1 / max(len(content), 1), 4),
        "rhythm_unigram_baseline_ordered_rows": base,
        "published_recall_at_8": {"128": 0.612, "256": 0.640},
        "published_median_rank": 2,
        "live_sha256": live,
        "runs": results,
    }
    out = LOG / "measure.json"
    assert_safe_output(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, default=_json_default),
        encoding="utf-8",
    )
    assert_live_intact()
    print(f"REPORT {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
