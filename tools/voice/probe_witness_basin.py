"""Does the witness gold core form its own basin?

Reads data/corpus/authoring/witness.md and the live train jsonl.
Does not modify either, does not write a checkpoint, does not boot the
field or resonance memory. Fresh generator, the live architecture
(dim 128, depth 4, heads 4, vocab 8192), CPU, supervised contrastive
pretraining — the same objective as training/rhythm_pretraining.py.

Two arms:

  additive  live train unchanged, plus the witness gold.
            The pulled words are still labeled reflect (and witness is
            still labeled stabilize). This is the contradictory-label
            case that folded the first rupture attempt.

  pulled    drop reflect-train sequences that contain a pulled word, and
            stabilize-train sequences that contain `witness`, then add the
            gold. The words leave their old company. The old lines are
            not relabeled, because that would drag analyze/inspect in.

Batch size is 256. The pretrainer's default of 8 would almost never put
two witness sequences in one batch (about 200 witness lines inside about
8500), so the loss would skip them and a "fold" would be a starved
positive, not a finding. 256 puts several witness lines in a batch
without repeating any sequence.

Readout is eval-mode, dropout off. Intra-cosine is the mean off-diagonal
pairwise cosine. Centroid cosine is the spherical centroid (mean of unit
vectors, re-normalized). That is the 2026-08-05 rupture check.

    python tools/voice/probe_witness_basin.py [--epochs 8] [--seed 0]
"""
from __future__ import annotations

import argparse
import collections
import json
import logging
import random
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.voice.lint_corpus_authoring import (  # noqa: E402
    PULL,
    load_core,
    load_live_bags,
    lint_file,
    parse_md,
)
from training.corpus import TRAIN_PATH, load_corpus  # noqa: E402
from training.rhythm_pretraining import (  # noqa: E402
    RHYTHM_IDS,
    PretrainingConfig,
    RhythmPretrainer,
)

WITNESS_MD = ROOT / "data" / "corpus" / "authoring" / "witness.md"
OUT_JSON = ROOT / "data" / "corpus" / "authoring" / "witness_separability.json"

BASE_RHYTHMS = ("stabilize", "dream", "reflect", "explore", "rupture")
# Where a pulled word is being removed from. `watch` is not in the gold
# core, so it is not pulled. `hold` and `self` are not anchors.
PULL_FROM = {
    "reflect": set(PULL),
    "stabilize": {"witness"},
}


def _unit_rows(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=np.float64)
    n = np.linalg.norm(z, axis=1, keepdims=True)
    return z / np.clip(n, 1e-8, None)


def _centroid(z: np.ndarray) -> np.ndarray:
    c = z.mean(axis=0)
    return c / (np.linalg.norm(c) + 1e-12)


def _pairwise_intra(z: np.ndarray) -> float:
    if len(z) < 2:
        return float("nan")
    sim = z @ z.T
    n = len(z)
    return float((sim.sum() - n) / (n * (n - 1)))


def _encode(gen, seqs: list[list[str]], chunk: int = 512) -> np.ndarray:
    gen.eval()
    parts = []
    with torch.no_grad():
        for i in range(0, len(seqs), chunk):
            parts.append(gen.encode_batch(seqs[i : i + chunk]))
    return _unit_rows(np.concatenate(parts, axis=0))


def _witness_records() -> list[dict]:
    rows = []
    for rhythm, tokens, _line in parse_md(WITNESS_MD):
        if rhythm != "witness":
            raise SystemExit(f"witness.md contains a {rhythm} line")
        rows.append({"tokens": tokens, "rhythm": "witness"})
    return rows


def _arm_records(train: list[dict], pulled: bool) -> tuple[list[dict], dict]:
    dropped = collections.Counter()
    kept = []
    for rec in train:
        if pulled:
            ban = PULL_FROM.get(rec["rhythm"])
            if ban and ban & set(rec["tokens"]):
                dropped[rec["rhythm"]] += 1
                continue
        kept.append(rec)
    witness = _witness_records()
    info = {
        "pulled": pulled,
        "dropped": {k: int(v) for k, v in dropped.items()},
        "train_kept": len(kept),
        "witness": len(witness),
    }
    return kept + witness, info


def _report(gen, records: list[dict], core: list[str]) -> dict:
    seqs = [r["tokens"] for r in records]
    labels = [r["rhythm"] for r in records]
    z = _encode(gen, seqs)
    names = list(BASE_RHYTHMS) + ["witness"]
    centroids = {}
    intra = {}
    to_own = {}
    for name in names:
        idx = [i for i, lab in enumerate(labels) if lab == name]
        zz = z[idx]
        centroids[name] = _centroid(zz)
        intra[name] = round(_pairwise_intra(zz), 4)
        to_own[name] = round(float((zz @ centroids[name]).mean()), 4)
    cent = {a: {} for a in names}
    for a in names:
        for b in names:
            if a < b:
                cos = round(float(np.dot(centroids[a], centroids[b])), 4)
                cent[a][b] = cos
    # nearest centroid
    C = np.stack([centroids[n] for n in names])
    scores = z @ C.T
    pred_i = scores.argmax(axis=1)
    acc = {}
    for name in names:
        idx = np.array([i for i, lab in enumerate(labels) if lab == name])
        acc[name] = round(float((pred_i[idx] == names.index(name)).mean()), 4)
    # witness sequences that do not land on witness
    misses = []
    w_idx = [i for i, lab in enumerate(labels) if lab == "witness"]
    for i in w_idx:
        if names[pred_i[i]] == "witness":
            continue
        row = {
            "tokens": seqs[i],
            "nearest": names[pred_i[i]],
            "cos": {names[k]: round(float(scores[i, k]), 4) for k in range(len(names))},
        }
        misses.append(row)
    misses.sort(key=lambda r: -r["cos"][r["nearest"]])
    # per core word: margin of its sequences, witness centroid minus best other
    fighters = []
    others = [n for n in names if n != "witness"]
    for word in core:
        idx = [i for i in w_idx if word in seqs[i]]
        if not idx:
            continue
        zz = z[idx]
        cos_w = zz @ centroids["witness"]
        cos_o = {n: zz @ centroids[n] for n in others}
        best_other = max(others, key=lambda n: float(cos_o[n].mean()))
        margin = float(cos_w.mean() - cos_o[best_other].mean())
        nn_frac = float(np.mean([names[pred_i[i]] == "witness" for i in idx]))
        fighters.append({
            "word": word,
            "n": len(idx),
            "nearest_centroid_frac": round(nn_frac, 4),
            "mean_cos_witness": round(float(cos_w.mean()), 4),
            "closest_other": best_other,
            "mean_cos_other": round(float(cos_o[best_other].mean()), 4),
            "margin": round(margin, 4),
        })
    fighters.sort(key=lambda r: r["margin"])
    # single-token read of each core word
    singles = _encode(gen, [[w] for w in core])
    single_rows = []
    S = singles @ C.T
    for i, word in enumerate(core):
        j = int(S[i].argmax())
        single_rows.append({
            "word": word,
            "nearest": names[j],
            "cos_witness": round(float(S[i, names.index("witness")]), 4),
            "cos_reflect": round(float(S[i, names.index("reflect")]), 4),
            "cos_explore": round(float(S[i, names.index("explore")]), 4),
            "cos_stabilize": round(float(S[i, names.index("stabilize")]), 4),
        })
    single_rows.sort(key=lambda r: r["cos_witness"] - r["cos_reflect"])
    return {
        "intra_pairwise": intra,
        "mean_cos_to_own_centroid": to_own,
        "centroid_cosine": {a: cent[a] for a in names if cent[a]},
        "nearest_centroid_acc": acc,
        "witness_misses": misses[:30],
        "witness_miss_count": len(misses),
        "word_margin": fighters,
        "single_token": single_rows,
    }


def _train(records: list[dict], seed: int, epochs: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    from agents.generator import Generator

    gen = Generator(
        vocab_size=8192,
        dim=128,
        depth=4,
        heads=4,
        dropout=0.1,
        device="cpu",
        auto_decay_interval=None,
    )
    seeds: dict[str, list[list[str]]] = {r: [] for r in list(BASE_RHYTHMS) + ["witness"]}
    for rec in records:
        seeds[rec["rhythm"]].append(list(rec["tokens"]))
    # The pretrainer looks up module-level RHYTHM_IDS. Witness is not in it.
    for i, name in enumerate(list(BASE_RHYTHMS) + ["witness"]):
        RHYTHM_IDS[name] = i
    trainer = RhythmPretrainer(
        gen,
        rhythm_seeds=seeds,
        config=PretrainingConfig(
            n_epochs=epochs,
            batch_size=256,
            log_interval=max(1, epochs // 4),
        ),
    )
    report = trainer.pretrain()
    return gen, {
        "epochs": report.epochs,
        "final_loss": report.final_loss,
        "loss_history": report.loss_history,
        "train_nn_acc": report.final_rhythm_acc,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--epochs",
        type=int,
        default=40,
        help="40 at batch 256 is about the live boot's 8 epochs at batch 8, "
             "in gradient steps. One epoch at batch 256 does not open the cones.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--arm", choices=("both", "additive", "pulled"), default="both")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("training.rhythm_pretraining").setLevel(logging.INFO)

    core = load_core()
    errors = lint_file(WITNESS_MD, core, load_live_bags())
    if errors:
        print("witness.md failed the lint; not training")
        for err in errors[:20]:
            print(" ", err)
        return 1

    train = load_corpus(TRAIN_PATH)
    arms = []
    if args.arm in ("both", "additive"):
        arms.append(False)
    if args.arm in ("both", "pulled"):
        arms.append(True)

    out = {
        "seed": args.seed,
        "epochs": args.epochs,
        "architecture": "Generator vocab 8192 dim 128 depth 4 heads 4, fresh, cpu",
        "batch_size": 256,
        "why_batch_256": (
            "Default batch 8 would rarely hold two witness sequences inside "
            "the 8527-line train, so witness would get no positive pair. "
            "Batch 256 is about 32x fewer steps per epoch, so the epoch "
            "count is raised to keep the gradient-step budget near the "
            "live boot (8 epochs at batch 8)."
        ),
        "arms": {},
    }
    for pulled in arms:
        name = "pulled" if pulled else "additive"
        records, info = _arm_records(train, pulled)
        n_w = sum(1 for r in records if r["rhythm"] == "witness")
        print("=" * 72)
        print(f"arm {name}  records {len(records)}  witness {n_w}  dropped {info['dropped']}")
        print(f"expected witness per batch of 256: {256 * n_w / len(records):.2f}")
        gen, train_info = _train(records, args.seed, args.epochs)
        metrics = _report(gen, records, core)
        # free the net before the next arm
        del gen
        arm = {"data": info, "train": train_info, "metrics": metrics}
        out["arms"][name] = arm
        intra = metrics["intra_pairwise"]["witness"]
        acc = metrics["nearest_centroid_acc"]["witness"]
        print(f"  witness intra-cosine {intra}  nearest-centroid acc {acc}")
        print("  witness centroid vs")
        wc = metrics["centroid_cosine"].get("witness", {})
        # centroid pairs are stored under the alphabetically earlier name
        for other in BASE_RHYTHMS:
            a, b = sorted(("witness", other))
            cos = metrics["centroid_cosine"].get(a, {}).get(b)
            print(f"    {other:12s} {cos}")
        print("  hardest words (lowest margin, witness minus closest other):")
        for row in metrics["word_margin"][:8]:
            print(
                f"    {row['word']:12s} margin {row['margin']:+.3f}  "
                f"toward {row['closest_other']}  "
                f"nn {row['nearest_centroid_frac']:.2f}"
            )
        print(f"  witness sequences off-basin: {metrics['witness_miss_count']}")

    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
