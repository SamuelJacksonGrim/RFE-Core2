"""Score participation, legibility, completion, and rhythm on one instrument.

The population numbers are the dim-256 instrument. Legibility is the Phase 0
protocol: frozen encoder, fresh TokenDecoder, hidden 256, BCE, 20 epochs,
seed 42, recall@8 on the live holdout.

Completion accuracy is read two ways:
  - co-trained head (completion checkpoints only): the objective's own mouth
  - frozen linear probe, same probe for every encoder, context vectors only
    (the held-out word is not in the input). The probe is the matched
    comparison. The rhythm-unigram baseline is what a rhythm centroid can do
    by ignoring the context.

Rhythm recoverability is a linear probe fit on the live TRAIN lines and
scored on the live HOLDOUT lines, plus nearest-centroid transfer.

    python -m tools.completion.measure --which all
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from agents.decoder import TokenDecoder
from tools.completion.corpus import content_of, load_jsonl
from tools.completion.geometry import (
    encode_texts,
    load_generator,
    nearest_centroid_accuracy,
    population,
    separability,
)
from tools.completion.geometry import dump_json
from tools.completion.live_guard import (
    BASELINE_ECOLOGY,
    BASELINE_WEIGHTS,
    FROZEN_ECOLOGY,
    FROZEN_WEIGHTS,
    REPO,
    assert_live_intact,
)
from training.completion import CompletionHead, pack_targets
from training.corpus import HOLDOUT_PATH, RHYTHMS, TRAIN_PATH, corpus_version, load_corpus
from training.decoder_training import _vocab_from, evaluate, train_decoder

SCRATCH = REPO.parent / "scratch" / "completion"
LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-completion"


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _content_vocab(records) -> list[str]:
    return sorted({t for rec in records for t in content_of(rec["tokens"])})


def _entropy(rows) -> float:
    total = 0.0
    for row in rows:
        dist = row["target_dist"]
        total += -sum(p * math.log(p) for p in dist.values() if p > 0)
    return total / max(len(rows), 1)


def _mode_set(row) -> set[str]:
    best = max(row["targets"].values())
    return {w for w, c in row["targets"].items() if c == best}


def completion_scores(logits: torch.Tensor, rows, tokens: list[str]) -> dict:
    """logits (N, V) lined up with rows. tokens[j] is class j."""
    if len(rows) == 0:
        return {}
    pred = logits.argmax(dim=-1).tolist()
    topk = logits.topk(min(8, logits.shape[1]), dim=-1).indices.tolist()
    mode_hit = []
    peaked_hit = []
    support_hit = []
    cross_peaked = []
    for i, row in enumerate(rows):
        modes = _mode_set(row)
        guess = tokens[pred[i]]
        mode_hit.append(guess in modes)
        if row["support"] == 1:
            peaked_hit.append(guess in modes)
            if row.get("cross_rhythm"):
                cross_peaked.append(guess in modes)
        got = {tokens[j] for j in topk[i]}
        support = set(row["targets"])
        support_hit.append(len(support & got) / len(support))
    return {
        "n": len(rows),
        "mode_top1": round(sum(mode_hit) / len(mode_hit), 4),
        "peaked_n": len(peaked_hit),
        "peaked_top1": round(sum(peaked_hit) / len(peaked_hit), 4) if peaked_hit else None,
        "cross_peaked_n": len(cross_peaked),
        "cross_peaked_top1": (
            round(sum(cross_peaked) / len(cross_peaked), 4) if cross_peaked else None
        ),
        "support_recall@8": round(sum(support_hit) / len(support_hit), 4),
    }


def _word_ce(logits: torch.Tensor, rows, index, device: str) -> float:
    target = pack_targets([r["target_dist"] for r in rows], index, device)
    return float((-(target * torch.log_softmax(logits, dim=-1)).sum(-1)).mean())


def unigram_baseline(train_rows, hold_rows, vocab: list[str]) -> dict:
    """Add-one rhythm marginal. Ignores the context. The centroid policy."""
    index = {t: i for i, t in enumerate(vocab)}
    counts = {r: Counter() for r in RHYTHMS}
    for row in train_rows:
        for w, c in row["targets"].items():
            if w in index:
                counts[row["rhythm"]][w] += c
    q = {}
    for rhythm, ctr in counts.items():
        vec = np.ones(len(vocab), dtype=np.float64)
        for w, c in ctr.items():
            vec[index[w]] += c
        vec /= vec.sum()
        q[rhythm] = vec
    logits = []
    kept = []
    for row in hold_rows:
        if row["rhythm"] not in q:
            continue
        logits.append(np.log(q[row["rhythm"]]))
        kept.append(row)
    tensor = torch.tensor(np.stack(logits), dtype=torch.float32)
    scores = completion_scores(tensor, kept, vocab)
    # logits are already log q. Do not pass them through log_softmax.
    ce_sum = 0.0
    for row, log_q in zip(kept, logits):
        ce_sum += -sum(p * float(log_q[index[w]]) for w, p in row["target_dist"].items())
    scores["ce"] = round(ce_sum / max(len(kept), 1), 4)
    scores["entropy_floor"] = round(_entropy(kept), 4)
    return scores


def fit_soft_probe(Xtr, rows_tr, Xho, rows_ho, vocab, epochs=40, lr=1e-2, seed=42) -> dict:
    """Fresh linear softmax on frozen context vectors. Same probe every encoder."""
    _seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    index = {t: i for i, t in enumerate(vocab)}
    V = len(vocab)
    D = Xtr.shape[1]
    layer = nn.Linear(D, V).to(device)
    opt = torch.optim.Adam(layer.parameters(), lr=lr)
    Ptr = pack_targets([r["target_dist"] for r in rows_tr], index, device)
    Xtr_t = torch.tensor(Xtr, dtype=torch.float32, device=device)
    n = len(rows_tr)
    layer.train()
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
        ho_logits = layer(torch.tensor(Xho, dtype=torch.float32, device=device))
    train_scores = completion_scores(tr_logits, rows_tr, vocab)
    hold_scores = completion_scores(ho_logits, rows_ho, vocab)
    train_scores["ce"] = round(_word_ce(tr_logits, rows_tr, index, device), 4)
    hold_scores["ce"] = round(_word_ce(ho_logits, rows_ho, index, device), 4)
    return {"train": train_scores, "holdout": hold_scores}


def fit_rhythm_probe(Ztr, ytr, Zho, yho, epochs=40, lr=1e-2, seed=42) -> dict:
    """5-way linear probe. Fit on train lines, score holdout lines."""
    _seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    name_to_i = {r: i for i, r in enumerate(RHYTHMS)}
    ytr_t = torch.tensor([name_to_i[y] for y in ytr], dtype=torch.long, device=device)
    yho_t = torch.tensor([name_to_i[y] for y in yho], dtype=torch.long, device=device)
    Xtr = torch.tensor(Ztr, dtype=torch.float32, device=device)
    Xho = torch.tensor(Zho, dtype=torch.float32, device=device)
    layer = nn.Linear(Xtr.shape[1], len(RHYTHMS)).to(device)
    opt = torch.optim.Adam(layer.parameters(), lr=lr)
    n = len(ytr)
    layer.train()
    for _epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        for start in range(0, n, 256):
            ix = perm[start:start + 256]
            opt.zero_grad()
            loss = F.cross_entropy(layer(Xtr[ix]), ytr_t[ix])
            loss.backward()
            opt.step()
    layer.eval()
    with torch.no_grad():
        tr_acc = float((layer(Xtr).argmax(-1) == ytr_t).float().mean())
        ho_acc = float((layer(Xho).argmax(-1) == yho_t).float().mean())
    return {
        "train_acc": round(tr_acc, 4),
        "holdout_acc": round(ho_acc, 4),
        "chance": round(1 / len(RHYTHMS), 4),
    }


def centroid_transfer(Ztr, ytr, Zho, yho) -> float:
    """Nearest train-centroid, scored on holdout. Not resubstitution."""
    def _unit(Z):
        Z = np.asarray(Z, dtype=np.float64)
        n = np.linalg.norm(Z, axis=1, keepdims=True)
        return Z / np.maximum(n, 1e-12)

    Ztr = _unit(Ztr)
    Zho = _unit(Zho)
    ytr = np.asarray(ytr)
    yho = np.asarray(yho)
    centroids = []
    names = []
    for rhythm in RHYTHMS:
        block = Ztr[ytr == rhythm]
        if len(block) == 0:
            continue
        c = block.mean(axis=0)
        centroids.append(c / (np.linalg.norm(c) + 1e-12))
        names.append(rhythm)
    pred = np.array(names)[(Zho @ np.stack(centroids).T).argmax(axis=1)]
    return round(float((pred == yho).mean()), 4)


@torch.no_grad()
def cotrained_completion(gen, head: CompletionHead, rows, cond_scale: float) -> dict:
    device = gen.device
    rhythm_index = {name: i for i, name in enumerate(head_rhythms(head))}
    logits = []
    for start in range(0, len(rows), 256):
        batch = rows[start:start + 256]
        ids = torch.tensor(
            [rhythm_index[r["rhythm"]] for r in batch], dtype=torch.long, device=device,
        )
        h = torch.tensor(
            gen.encode_batch([r["context"] for r in batch]), dtype=torch.float32, device=device,
        )
        code = F.normalize(head.rhythm_embed(ids), dim=-1)
        conditioned = F.normalize(h + cond_scale * code, dim=-1)
        logits.append(head.head(conditioned))
    stacked = torch.cat(logits, dim=0)
    scores = completion_scores(stacked, rows, head.vocab)
    scores["ce"] = round(_word_ce(stacked, rows, head.index, device), 4)
    scores["entropy_floor"] = round(_entropy(rows), 4)
    return scores


def head_rhythms(head: CompletionHead):
    # Saved alongside the module; the embedding row order is RHYTHMS.
    return RHYTHMS


def load_head(path: str, dim: int, device: str) -> tuple[CompletionHead, float]:
    blob = torch.load(path, map_location=device, weights_only=False)
    if blob["dim"] != dim:
        raise SystemExit(f"head dim {blob['dim']} != encoder dim {dim}")
    if list(blob["rhythms"]) != list(RHYTHMS):
        raise SystemExit(f"head rhythm order {blob['rhythms']} != {RHYTHMS}")
    head = CompletionHead(blob["vocab"], dim, len(RHYTHMS), device)
    head.load_state_dict(blob["state_dict"])
    head.eval()
    return head, float(blob.get("cond_scale", 0.25))


@torch.no_grad()
def median_true_rank(decoder, X, token_lists) -> float | None:
    decoder.eval()
    logits = decoder(X)
    order = logits.argsort(dim=-1, descending=True)
    ranks = torch.empty_like(order)
    idx = torch.arange(order.shape[1], device=order.device).unsqueeze(0).expand_as(order)
    ranks.scatter_(1, order, idx)
    meds = []
    for i, toks in enumerate(token_lists):
        js = [decoder.index[t] for t in toks if t in decoder.index]
        if not js:
            continue
        meds.append(float(torch.median(ranks[i, js].float())) + 1.0)
    if not meds:
        return None
    return round(statistics.median(meds), 2)


def legibility(gen, train_records, hold_records, dim: int) -> dict:
    """Phase 0 mouth. Fresh decoder every call. Seed 42."""
    _seed(42)
    vocab = _vocab_from(train_records)
    Xtr = torch.tensor(
        encode_texts(gen, [r["tokens"] for r in train_records]),
        dtype=torch.float32, device=gen.device,
    )
    Xho = torch.tensor(
        encode_texts(gen, [r["tokens"] for r in hold_records]),
        dtype=torch.float32, device=gen.device,
    )
    ttr = [r["tokens"] for r in train_records]
    tho = [r["tokens"] for r in hold_records]
    dec = TokenDecoder(vocab, dim=dim, hidden=256, device=gen.device)
    train_decoder(gen, dec, Xtr, ttr, epochs=20)
    tr = evaluate(dec, Xtr, ttr, top_k=8)
    ho = evaluate(dec, Xho, tho, top_k=8)
    tr["median_true_rank"] = median_true_rank(dec, Xtr, ttr)
    ho["median_true_rank"] = median_true_rank(dec, Xho, tho)
    return {"train": tr, "holdout": ho}


def measure_one(spec: dict, live_train, live_hold, comp_train, comp_hold, vocab, skip_legibility: bool) -> dict:
    print(f"=== {spec['name']} ===", flush=True)
    gen = load_generator(spec["dim"], spec["weights"], spec["ecology"])
    print(f"device {gen.device} embedding {tuple(gen.embedding.weight.shape)}", flush=True)

    Ztr = encode_texts(gen, [r["tokens"] for r in live_train])
    Zho = encode_texts(gen, [r["tokens"] for r in live_hold])
    ytr = [r["rhythm"] for r in live_train]
    yho = [r["rhythm"] for r in live_hold]
    pop = population(Zho)
    sep = separability(Zho, yho)
    rhythm = fit_rhythm_probe(Ztr, ytr, Zho, yho)
    centroid = centroid_transfer(Ztr, ytr, Zho, yho)
    resub = nearest_centroid_accuracy(Zho, yho)
    print(
        f"PR {pop['participation_ratio']}  eff {pop['eff_rank_512cap']}  "
        f"rhythm_probe {rhythm['holdout_acc']}  centroid_xfer {centroid}  "
        f"within {sep['within_centroid_cos']}",
        flush=True,
    )

    # Mark holdout rows whose context is a train cross-rhythm stem, so the
    # slice tests the condition the model could have learned.
    cross_ctx = {tuple(r["context"]) for r in comp_train if r["cross_rhythm"]}
    hold_marked = []
    for row in comp_hold:
        item = dict(row)
        item["cross_rhythm"] = tuple(row["context"]) in cross_ctx
        hold_marked.append(item)
    train_marked = []
    for row in comp_train:
        item = dict(row)
        item["cross_rhythm"] = tuple(row["context"]) in cross_ctx
        train_marked.append(item)

    Xctx_tr = encode_texts(gen, [r["context"] for r in train_marked])
    Xctx_ho = encode_texts(gen, [r["context"] for r in hold_marked])
    print("fitting frozen completion probe ...", flush=True)
    probe = fit_soft_probe(Xctx_tr, train_marked, Xctx_ho, hold_marked, vocab)
    probe["holdout"]["entropy_floor"] = round(_entropy(hold_marked), 4)
    probe["train"]["entropy_floor"] = round(_entropy(train_marked), 4)
    print(
        f"frozen probe holdout peaked_top1 {probe['holdout']['peaked_top1']}  "
        f"ce {probe['holdout']['ce']}",
        flush=True,
    )

    cotrained = None
    if spec.get("head"):
        head, scale = load_head(spec["head"], spec["dim"], gen.device)
        if head.vocab != vocab:
            raise SystemExit("completion head vocab does not match the live content vocab")
        cotrained = {
            "train": cotrained_completion(gen, head, train_marked, scale),
            "holdout": cotrained_completion(gen, head, hold_marked, scale),
            "cond_scale": scale,
        }
        print(
            f"cotrained holdout peaked_top1 {cotrained['holdout']['peaked_top1']}  "
            f"ce {cotrained['holdout']['ce']}",
            flush=True,
        )

    mouth = None
    if not skip_legibility:
        print("training phase-0 mouth ...", flush=True)
        mouth = legibility(gen, live_train, live_hold, spec["dim"])
        print(f"legibility holdout {mouth['holdout']}", flush=True)

    return {
        "name": spec["name"],
        "objective": spec["objective"],
        "dim": spec["dim"],
        "weights": spec["weights"],
        "ecology": spec["ecology"],
        "population_live_holdout": pop,
        "separability_live_holdout": sep,
        "rhythm_linear_probe": rhythm,
        "rhythm_centroid_transfer": centroid,
        "rhythm_centroid_resubstitution_holdout": round(resub, 4),
        "frozen_completion_probe": probe,
        "cotrained_completion": cotrained,
        "legibility": mouth,
    }


def _specs() -> dict:
    def completion(dim):
        # Embeddings trained, transformer left at init. Training the stack
        # collapses participation back to ~4; see the finding.
        weights = REPO / f"data/checkpoints/generator_weights_completion_{dim}_emb.pt"
        ecology = REPO / f"data/checkpoints/generator_ecology_completion_{dim}_emb.json"
        head = REPO / f"data/checkpoints/completion_head_{dim}_emb.pt"
        if not (weights.exists() and ecology.exists() and head.exists()):
            return None
        return {
            "name": f"completion{dim}",
            "objective": "completion",
            "dim": dim,
            "weights": str(weights),
            "ecology": str(ecology),
            "head": str(head),
        }

    frozen = {
        "name": "contrastive_frozen128",
        "objective": "contrastive",
        "dim": 128,
        "weights": str(REPO / FROZEN_WEIGHTS),
        "ecology": str(REPO / FROZEN_ECOLOGY),
    }
    paired = {
        "name": "contrastive_paired128",
        "objective": "contrastive",
        "dim": 128,
        "weights": str(REPO / BASELINE_WEIGHTS[128]),
        "ecology": str(REPO / BASELINE_ECOLOGY[128]),
    }
    c256 = {
        "name": "contrastive256",
        "objective": "contrastive",
        "dim": 256,
        "weights": str(REPO / BASELINE_WEIGHTS[256]),
        "ecology": str(REPO / BASELINE_ECOLOGY[256]),
    }
    return {
        "frozen128": frozen,
        "contrastive128": paired,
        "contrastive256": c256,
        "completion128": completion(128),
        "completion256": completion(256),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--which",
        default="all",
        choices=["all", "frozen128", "contrastive128", "contrastive256", "completion128", "completion256"],
    )
    ap.add_argument("--skip-legibility", action="store_true")
    args = ap.parse_args()

    live = assert_live_intact()
    live_train = load_corpus(TRAIN_PATH)
    live_hold = load_corpus(HOLDOUT_PATH)
    comp_train = load_jsonl(SCRATCH / "completion_train.jsonl")
    comp_hold = load_jsonl(SCRATCH / "completion_holdout.jsonl")
    vocab = _content_vocab(live_train)
    base = unigram_baseline(comp_train, comp_hold, vocab)
    print(
        f"unigram baseline peaked_top1 {base['peaked_top1']}  ce {base['ce']}  "
        f"entropy floor {base['entropy_floor']}  |V|={len(vocab)}",
        flush=True,
    )

    specs = _specs()
    if args.which == "all":
        chosen = ["frozen128", "contrastive128", "contrastive256", "completion128", "completion256"]
    else:
        chosen = [args.which]

    results = []
    for name in chosen:
        spec = specs[name]
        if spec is None:
            print(f"skip {name}: checkpoint missing", flush=True)
            continue
        results.append(
            measure_one(spec, live_train, live_hold, comp_train, comp_hold, vocab, args.skip_legibility)
        )

    payload = {
        "corpus_version": corpus_version(),
        "content_vocab": len(vocab),
        "chance_peaked_top1": round(1 / len(vocab), 4),
        "rhythm_unigram_baseline": base,
        "live_sha256": live,
        "runs": results,
    }
    tag = args.which
    path = LOG / f"measure_{tag}.json"
    dump_json(str(path), payload)
    assert_live_intact()
    print(f"REPORT {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
