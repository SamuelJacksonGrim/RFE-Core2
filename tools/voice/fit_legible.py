"""
tools/voice/fit_legible.py — the full cone-bounded legibility fit.

Same objective as the 8-epoch probe (training/legibility.py, LegibilityConfig
defaults). The only config change is epochs: 8 -> 30, and this runner stops
early if the rank term and the jaccard term both flatten. It does not retune
the four terms.

Every 5 epochs, and at the probe's epoch-8 point, it scores the untouched
holdout with a fresh Phase-0 TokenDecoder and checks the abort guards. A
tripped guard stops the fit and does not write a checkpoint.

Writes, only on a clean finish:
    data/checkpoints/generator_weights_5rhythm_legible.pt
    data/checkpoints/generator_ecology_5rhythm_legible.json

Never writes generator_weights_5rhythm.pt or generator_ecology_5rhythm.json.
Does not step the field, open resonance memory, or bind a port. CPU only.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, ".")

from agents.generator import Generator
from training.corpus import RHYTHMS, TRAIN_PATH, HOLDOUT_PATH, corpus_version, load_corpus
from training.decoder_training import _vocab_from
from training.legibility import LegibilityConfig, fit_encoder
from tools.voice.probe_legibility import (
    _arm_report,
    _centroids,
    _encode,
    _log,
    _row_report,
    _snapshot,
)

FROZEN_W = Path("data/checkpoints/generator_weights_5rhythm.pt")
FROZEN_E = Path("data/checkpoints/generator_ecology_5rhythm.json")
OUT_W = Path("data/checkpoints/generator_weights_5rhythm_legible.pt")
OUT_E = Path("data/checkpoints/generator_ecology_5rhythm_legible.json")
ECO_SNAP = Path("data/checkpoints/_legible_ecology_prefitsnap.json")
METRICS = Path("docs/findings/2026-09-22-legibility-fit-metrics.json")
DIM = 128

# Probe fit_history, epochs 1..8. A divergence here means this run is not
# the same trajectory, and it stops rather than being reported as one.
PROBE_HISTORY = [
    {"total": 1.662321714104199, "margin": 0.07842063351122082, "centroid": 0.015112683077755033, "jaccard": 0.1722736082604674, "rank": 0.9738665955965636},
    {"total": 1.2671772261134913, "margin": 0.022339353612700445, "centroid": 0.011983405348279925, "jaccard": 0.11875468712361133, "rank": 0.9163436186118205},
    {"total": 1.112404215531271, "margin": 0.008836632115445787, "centroid": 0.015055522948625635, "jaccard": 0.08791377370963331, "rank": 0.8711190956537841},
    {"total": 1.0402840131618938, "margin": 0.005470895372544889, "centroid": 0.01668436672599589, "jaccard": 0.07389901578426361, "rank": 0.8372336713994135},
    {"total": 0.9820188430489086, "margin": 0.003841245811257023, "centroid": 0.016544314086070804, "jaccard": 0.062471205338102874, "rank": 0.8086228204555199},
    {"total": 0.9368105784791415, "margin": 0.003096683448959203, "centroid": 0.01609878383240983, "jaccard": 0.054142604414068284, "rank": 0.7839410617703297},
    {"total": 0.9009331044603567, "margin": 0.002790976439666606, "centroid": 0.016169959534203908, "jaccard": 0.04829520133675122, "rank": 0.7608388808907055},
    {"total": 0.8717744233178311, "margin": 0.002232650798014518, "centroid": 0.01671276534678506, "jaccard": 0.04422415450948183, "rank": 0.7409699803493062},
]
PROBE_ROW = {
    "epoch": 8,
    "recall@8": 0.3554,
    "median_rank": 21,
    "exact_bag@8": 0.0432,
    "clean_within": 0.6156,
    "clean_across": 0.1178,
    "nn_acc_all": 0.995,
    "centroid_cos_min": 0.9759,
    "rupture_recall_clean": 0.283,
    "orphan_recall": 0.2901,
}

# Stopping rule, not an objective weight. Both terms must go quiet.
RANK_FLAT = 0.005
JACCARD_FLAT = 0.001
FLAT_WINDOW = 3

# Abort guards from the brief, on the clean holdout (the Phase 0 cut) for
# within/across and on both cuts for nearest-centroid accuracy.
# "Across climbing back toward within" means the cones are becoming
# indistinct, not that across ticked up off its early minimum while the
# gap is still large. The first run (stopped at epoch 20, nothing saved)
# showed that tick: clean across 0.105 -> 0.164 while within stayed at
# 0.59 and frozen across is 0.356. A 0.05-rebound rule fired on that and
# was wrong. The abort is the probe's own bar plus a hard merge:
#   nearest-centroid accuracy < 0.98 (all-holdout and clean)
#   any rhythm centroid cosine to the frozen checkpoint < 0.95
#   clean across > frozen clean across + 0.08
#   clean (within - across) < 0.10
NN_ACC_MIN = 0.98
CENTROID_COS_MIN = 0.95
ACROSS_CLIMB = 0.08
GAP_MIN = 0.10
TRAJECTORY_ABORT = 1e-3


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


def _config_delta(cfg: LegibilityConfig) -> dict:
    base = LegibilityConfig()
    return {
        k: {"probe": getattr(base, k), "fit": getattr(cfg, k)}
        for k in base.__dict__
        if getattr(base, k) != getattr(cfg, k)
    }


def _trajectory_delta(epoch: int, row: dict) -> dict:
    if epoch < 1 or epoch > len(PROBE_HISTORY):
        return {}
    exp = PROBE_HISTORY[epoch - 1]
    out = {}
    for k, v in exp.items():
        got = float(row[k])
        out[k] = {"probe": v, "fit": got, "abs": abs(got - v)}
    return out


def _flattened(history: list) -> bool:
    if len(history) < FLAT_WINDOW + 1:
        return False
    window = history[-(FLAT_WINDOW + 1):]
    for prev, cur in zip(window, window[1:]):
        if (prev["rank"] - cur["rank"]) >= RANK_FLAT:
            return False
        if (prev["jaccard"] - cur["jaccard"]) >= JACCARD_FLAT:
            return False
    return True


def _curve_row(epoch: int, loss_row: dict, arm: dict) -> dict:
    clean = arm["geometry_clean_holdout"] or {}
    cents = arm["centroid_cos_to_frozen"]
    per = arm["holdout_splits_clean"].get("per_rhythm", {})
    rupture = per.get("rupture", {})
    return {
        "epoch": epoch,
        "total": loss_row["total"],
        "margin": loss_row["margin"],
        "centroid": loss_row["centroid"],
        "jaccard": loss_row["jaccard"],
        "rank": loss_row["rank"],
        "gap_mean": loss_row.get("gap_mean"),
        "gap_p10": loss_row.get("gap_p10"),
        "recall@8": arm["mouth_holdout"]["recall@k"],
        "median_rank": arm["holdout_rank"]["median_rank"],
        "exact_bag@8": arm["mouth_holdout"]["exact_bag@k"],
        "train_recall@8": arm["mouth_train"]["recall@k"],
        "clean_within": clean.get("within_mean"),
        "clean_across": clean.get("across_mean"),
        "clean_nn_acc": clean.get("nn_centroid_acc"),
        "nn_acc": arm["geometry_vs_frozen_centroids"]["nn_centroid_acc"],
        "centroid_cos_min": min(cents.values()) if cents else None,
        "centroid_cos": cents,
        "within_per_rhythm": clean.get("within"),
        "rupture_recall_clean": rupture.get("recall@8"),
        "rupture_median_rank_clean": rupture.get("median_rank"),
        "orphan_recall": arm["holdout_splits_all"].get("orphan_token_recall@8"),
        "orphan_median_rank": arm["holdout_splits_all"].get("orphan_median_rank"),
        "trained_token_recall": arm["holdout_splits_all"].get("trained_token_recall@8"),
        "nn_jaccard": arm["nn_jaccard_holdout"]["within_cone_nn_jaccard"],
        "encode_cos_clean": arm.get("encode_cos_to_frozen_clean_mean"),
        "per_rhythm_clean": per,
    }


def _guard(row: dict, frozen_clean_across: float, prior: list) -> str | None:
    reasons = []
    nn = row["nn_acc"]
    nn_c = row["clean_nn_acc"]
    if nn is None or nn < NN_ACC_MIN:
        reasons.append(f"nearest-centroid accuracy {nn} < {NN_ACC_MIN}")
    if nn_c is None or nn_c < NN_ACC_MIN:
        reasons.append(f"clean nearest-centroid accuracy {nn_c} < {NN_ACC_MIN}")
    cmin = row["centroid_cos_min"]
    if cmin is None or cmin < CENTROID_COS_MIN:
        reasons.append(f"centroid cosine min {cmin} < {CENTROID_COS_MIN} ({row['centroid_cos']})")
    across = row["clean_across"]
    within = row["clean_within"]
    if across is None or within is None:
        reasons.append("clean within/across missing")
    else:
        gap = within - across
        if gap < GAP_MIN:
            reasons.append(
                f"clean across {across:.4f} is within {gap:.4f} of within {within:.4f}"
            )
        if across > frozen_clean_across + ACROSS_CLIMB:
            reasons.append(
                f"clean across {across:.4f} climbed more than {ACROSS_CLIMB} "
                f"above frozen {frozen_clean_across:.4f}"
            )
        if prior:
            min_across = min(p["clean_across"] for p in prior)
            if across > min_across + 0.02:
                _log(
                    f"  note: clean across {across:.4f} is up from its min "
                    f"{min_across:.4f}; gap to within is {gap:.4f} "
                    f"(frozen across {frozen_clean_across:.4f}). Not an abort."
                )
    return "; ".join(reasons) if reasons else None


def _prepare():
    train = load_corpus(TRAIN_PATH)
    holdout = load_corpus(HOLDOUT_PATH)
    vocab = _vocab_from(train)
    token_index = {t: i for i, t in enumerate(vocab)}
    gen = Generator(vocab_size=8192, dim=DIM, depth=4, heads=4, device="cpu")
    gen.load_checkpoint(str(FROZEN_W), str(FROZEN_E))
    gen.eval()
    if gen.device != "cpu":
        raise RuntimeError(f"fit refused non-cpu device {gen.device}")
    pipe = gen.registry.pipeline
    ecology = set(gen.registry.symbols)

    def canon(tok: str) -> str:
        return pipe.process(tok).token

    ecology_tokens = set()
    orphan_tokens = []
    for t in vocab:
        if canon(t) in ecology:
            ecology_tokens.add(t)
        else:
            orphan_tokens.append(t)

    def mark(records):
        out = []
        for rec in records:
            out.append({
                "tokens": list(rec["tokens"]),
                "rhythm": rec["rhythm"],
                "orphan": any(t not in ecology_tokens for t in rec["tokens"]),
            })
        return out

    train_m = mark(train)
    hold_m = mark(holdout)
    for t in orphan_tokens:
        gen.registry.register(t)
    gen._ensure_embedding_capacity()
    # Ecology as it should be saved: orphans registered, usage not inflated
    # by the measurement encodes or by the fit's own register() calls.
    if ECO_SNAP.exists():
        ECO_SNAP.unlink()
    gen.save_ecology(str(ECO_SNAP))

    trained_addrs = [gen.registry.symbols[canon(t)].address for t in ecology_tokens]
    orphan_addrs = []
    for t in orphan_tokens:
        st = gen.registry.symbols.get(canon(t))
        if st is not None:
            orphan_addrs.append(st.address)
    weight0 = gen.embedding.weight.detach().cpu().float().clone()

    clean_tr = [not r["orphan"] for r in train_m]
    clean_lists = [r["tokens"] for r, c in zip(train_m, clean_tr) if c]
    clean_rids = np.array(
        [RHYTHMS.index(r["rhythm"]) for r, c in zip(train_m, clean_tr) if c],
        dtype=np.int64,
    )
    _log("frozen centroids from clean train encodes ...")
    z_clean = _encode(gen, clean_lists)
    centroids_np = _centroids(z_clean, clean_rids)

    rid_tr = np.array([RHYTHMS.index(r["rhythm"]) for r in train_m], dtype=np.int64)
    rid_ho = np.array([RHYTHMS.index(r["rhythm"]) for r in hold_m], dtype=np.int64)
    toks_tr = [r["tokens"] for r in train_m]
    toks_ho = [r["tokens"] for r in hold_m]
    rhythms_ho = [r["rhythm"] for r in hold_m]
    clean_ho = [not r["orphan"] for r in hold_m]
    _log("frozen encode of train + holdout ...")
    z_tr_frozen = _encode(gen, toks_tr)
    z_ho_frozen = _encode(gen, toks_ho)
    return {
        "gen": gen,
        "vocab": vocab,
        "token_index": token_index,
        "train_m": train_m,
        "ecology_tokens": ecology_tokens,
        "orphan_tokens": orphan_tokens,
        "centroids_np": centroids_np,
        "rid_tr": rid_tr,
        "rid_ho": rid_ho,
        "toks_tr": toks_tr,
        "toks_ho": toks_ho,
        "rhythms_ho": rhythms_ho,
        "clean_ho": clean_ho,
        "z_tr_frozen": z_tr_frozen,
        "z_ho_frozen": z_ho_frozen,
        "trained_addrs": trained_addrs,
        "orphan_addrs": orphan_addrs,
        "weight0": weight0,
        "n_train": len(train),
        "n_holdout": len(holdout),
    }


def _eval_epoch(ctx, epoch: int, loss_row: dict, gen) -> dict:
    _log(f"YARDSTICK epoch {epoch}")
    rng_state = torch.get_rng_state()
    try:
        z_tr = _encode(gen, ctx["toks_tr"])
        z_ho = _encode(gen, ctx["toks_ho"])
        arm = _arm_report(
            f"epoch-{epoch}",
            z_tr, ctx["toks_tr"], ctx["rid_tr"],
            z_ho, ctx["toks_ho"], ctx["rid_ho"], ctx["rhythms_ho"],
            ctx["vocab"], ctx["ecology_tokens"], ctx["clean_ho"],
            ctx["centroids_np"], ctx["centroids_np"],
            frozen_z_ho=ctx["z_ho_frozen"],
        )
    finally:
        torch.set_rng_state(rng_state)
        gen.eval()
    return _curve_row(epoch, loss_row, arm)


def main() -> int:
    t_all = time.perf_counter()
    if torch.cuda.is_available():
        raise RuntimeError("cuda is visible; this fit is the Windows CPU checkout and will not run on it")
    for forbidden in (FROZEN_W, FROZEN_E):
        if not forbidden.exists():
            raise RuntimeError(f"missing frozen checkpoint {forbidden}")
    if OUT_W.resolve() == FROZEN_W.resolve() or OUT_E.resolve() == FROZEN_E.resolve():
        raise RuntimeError("refusing to point the legible outputs at the frozen checkpoint")

    frozen_before = {"weights": _file_id(FROZEN_W), "ecology": _file_id(FROZEN_E)}
    _log(f"frozen weights sha256 {frozen_before['weights']['sha256']} bytes {frozen_before['weights']['bytes']}")

    cfg = LegibilityConfig(epochs=30)
    delta = _config_delta(cfg)
    if list(delta) != ["epochs"] or delta["epochs"] != {"probe": 8, "fit": 30}:
        raise RuntimeError(f"config drifted from the probe: {delta}")
    _log(f"config delta vs probe: {delta}")

    ctx = _prepare()
    _log(
        f"corpus v{corpus_version()}  train={ctx['n_train']} holdout={ctx['n_holdout']} "
        f"vocab={len(ctx['vocab'])}  orphan_tokens={len(ctx['orphan_tokens'])}"
    )

    # Frozen clean across, measured with the same geometry the guards use,
    # so "climbed above frozen" is not taken from the published rounded table.
    from training.legibility import geometry_report
    clean_arr = np.array(ctx["clean_ho"], dtype=bool)
    frozen_geo = geometry_report(
        ctx["z_ho_frozen"][clean_arr], ctx["rid_ho"][clean_arr], ctx["centroids_np"],
    )
    frozen_clean_across = float(frozen_geo["across_mean"])
    frozen_clean_within = float(frozen_geo["within_mean"])
    _log(f"frozen clean within {frozen_clean_within:.4f}  across {frozen_clean_across:.4f}")

    # The probe trained the frozen mouth (seed 42) immediately before
    # fit_encoder. That call resets the torch RNG and then burns it.
    # Skipping it would change the rank term's negative samples, which is
    # a different trajectory, not the same fit. The recall is also the
    # check that this checkout still reads the published frozen number.
    _log("ARM frozen (probe prefix — same mouth, same RNG burn)")
    frozen_arm = _arm_report(
        "frozen",
        ctx["z_tr_frozen"], ctx["toks_tr"], ctx["rid_tr"],
        ctx["z_ho_frozen"], ctx["toks_ho"], ctx["rid_ho"], ctx["rhythms_ho"],
        ctx["vocab"], ctx["ecology_tokens"], ctx["clean_ho"],
        ctx["centroids_np"], ctx["centroids_np"],
    )
    frozen_recall = frozen_arm["mouth_holdout"]["recall@k"]
    _log(f"frozen holdout recall@8={frozen_recall} (probe 0.1029, phase0 0.1106)")

    curve = []
    trajectory = []
    abort_reason = None
    stop_reason = None
    mismatch = None

    def on_epoch(epoch, row, gen):
        nonlocal abort_reason, stop_reason, mismatch
        if epoch <= len(PROBE_HISTORY):
            delta_ep = _trajectory_delta(epoch, row)
            worst = max(v["abs"] for v in delta_ep.values())
            trajectory.append({"epoch": epoch, "worst_abs": worst, "terms": delta_ep})
            _log(f"  trajectory vs probe epoch {epoch}: worst abs {worst:.3e}")
            if worst > TRAJECTORY_ABORT:
                mismatch = (
                    f"epoch {epoch} losses diverged from the probe by {worst:.3e} "
                    f"(bar {TRAJECTORY_ABORT}). Not the same fit."
                )
                _log("TRAJECTORY MISMATCH " + mismatch)
                stop_reason = "trajectory_mismatch"
                return "stop"
        do_eval = (epoch % 5 == 0) or epoch == 8 or epoch == cfg.epochs or _flattened(fit_box["history_so_far"] + [row])
        # history inside fit_encoder is appended before the hook, so the
        # row is already the last entry. Read it off the closure list we copy.
        if do_eval:
            yard = _eval_epoch(ctx, epoch, row, gen)
            curve.append(yard)
            _log(
                f"CURVE epoch {epoch}  recall@8={yard['recall@8']}  "
                f"median_rank={yard['median_rank']}  exact_bag@8={yard['exact_bag@8']}  "
                f"within={yard['clean_within']}  across={yard['clean_across']}  "
                f"nn_acc={yard['nn_acc']}  centroid_min={yard['centroid_cos_min']}  "
                f"rupture={yard['rupture_recall_clean']}  orphan={yard['orphan_recall']}"
            )
            reason = _guard(yard, frozen_clean_across, curve[:-1])
            if reason:
                abort_reason = reason
                stop_reason = "abort"
                _log("ABORT " + reason)
                return "stop"
        if _flattened(fit_box["history_so_far"] + [row]):
            # The hook sees the epoch already logged. Flattening uses that
            # history, which the caller mirrors below. If this epoch was not
            # an eval point, score it before accepting the stop.
            if not curve or curve[-1]["epoch"] != epoch:
                yard = _eval_epoch(ctx, epoch, row, gen)
                curve.append(yard)
                reason = _guard(yard, frozen_clean_across, curve[:-1])
                if reason:
                    abort_reason = reason
                    stop_reason = "abort"
                    _log("ABORT " + reason)
                    return "stop"
            stop_reason = "flatten"
            _log(
                f"FLATTEN rank drop < {RANK_FLAT} and jaccard drop < {JACCARD_FLAT} "
                f"for {FLAT_WINDOW} epochs, stopping at {epoch}"
            )
            return "stop"
        return None

    # fit_encoder owns the history. The hook needs it for the flatten test,
    # and the history list is appended before the hook runs. Mirror by
    # wrapping: we pass a hook that reads fit_encoder's history through a
    # list the closure updates from the row argument only.
    fit_box = {"history_so_far": []}

    def on_epoch_tracked(epoch, row, gen):
        decision = on_epoch(epoch, row, gen)
        fit_box["history_so_far"].append(row)
        return decision

    cents = torch.tensor(ctx["centroids_np"], dtype=torch.float32)
    _log(f"FIT epochs={cfg.epochs} per_rhythm={cfg.per_rhythm} lr={cfg.lr}")
    try:
        fitted = fit_encoder(
            ctx["gen"], ctx["train_m"], cents, ctx["token_index"], cfg,
            log=_log, on_epoch=on_epoch_tracked,
        )
    finally:
        # Hashes are checked even when the fit raises.
        frozen_after_partial = {"weights": _file_id(FROZEN_W), "ecology": _file_id(FROZEN_E)}
        if frozen_after_partial != frozen_before:
            _log("FROZEN CHECKPOINT CHANGED DURING THE FIT")
            _log(json.dumps({"before": frozen_before, "after": frozen_after_partial}, indent=2))
            raise RuntimeError("frozen checkpoint bytes changed during the fit")

    history = fitted["history"]
    if stop_reason is None:
        stop_reason = "max_epochs" if len(history) >= cfg.epochs else "stop"
    improving = False
    if len(history) >= 2:
        improving = (
            (history[-2]["rank"] - history[-1]["rank"]) >= RANK_FLAT
            or (history[-2]["jaccard"] - history[-1]["jaccard"]) >= JACCARD_FLAT
        )

    saved = False
    rows_trained = None
    rows_orphan = None
    if abort_reason is None and mismatch is None:
        gen = ctx["gen"]
        weights_before_eco = _snapshot(gen)
        gen.load_ecology(str(ECO_SNAP))
        gen.load_state_dict({k: v.to(gen.device) for k, v in weights_before_eco.items()})
        gen.eval()
        rows_trained = _row_report(gen.embedding.weight.detach().cpu().float(), ctx["weight0"], ctx["trained_addrs"])
        rows_orphan = _row_report(gen.embedding.weight.detach().cpu().float(), ctx["weight0"], ctx["orphan_addrs"])
        gen.save_checkpoint(str(OUT_W), str(OUT_E))
        saved = True
        _log(f"SAVED {OUT_W}")
        _log(f"SAVED {OUT_E}")
    else:
        _log("checkpoint NOT saved")

    if ECO_SNAP.exists():
        ECO_SNAP.unlink()

    frozen_after = {"weights": _file_id(FROZEN_W), "ecology": _file_id(FROZEN_E)}
    untouched = frozen_after == frozen_before
    if not untouched:
        raise RuntimeError("frozen checkpoint bytes changed")

    report = {
        "corpus": corpus_version(),
        "device": "cpu",
        "torch": torch.__version__,
        "config_delta_vs_probe": delta,
        "flatten_rule": {
            "rank_drop_below": RANK_FLAT,
            "jaccard_drop_below": JACCARD_FLAT,
            "window": FLAT_WINDOW,
        },
        "guards": {
            "nn_acc_min": NN_ACC_MIN,
            "centroid_cos_min": CENTROID_COS_MIN,
            "across_climb": ACROSS_CLIMB,
            "gap_min": GAP_MIN,
            "note": (
                "A 0.05 across-rebound rule was tried on the first run and "
                "false-tripped at epoch 20 (across 0.164 vs within 0.587, "
                "frozen across 0.356). It is not part of this fit."
            ),
        },
        "frozen_clean_geometry": frozen_geo,
        "frozen_files_before": frozen_before,
        "frozen_files_after": frozen_after,
        "frozen_untouched": untouched,
        "orphan_tokens": len(ctx["orphan_tokens"]),
        "trained_tokens": len(ctx["ecology_tokens"]),
        "probe_row": PROBE_ROW,
        "frozen_holdout_recall@8": frozen_recall,
        "frozen_mouth": {
            "recall@8": frozen_arm["mouth_holdout"]["recall@k"],
            "exact_bag@8": frozen_arm["mouth_holdout"]["exact_bag@k"],
            "median_rank": frozen_arm["holdout_rank"]["median_rank"],
            "clean_within": (frozen_arm["geometry_clean_holdout"] or {}).get("within_mean"),
            "clean_across": (frozen_arm["geometry_clean_holdout"] or {}).get("across_mean"),
            "nn_acc": frozen_arm["geometry_vs_frozen_centroids"]["nn_centroid_acc"],
        },
        "trajectory_vs_probe": trajectory,
        "fit_history": history,
        "curve": curve,
        "stop_reason": stop_reason,
        "still_improving": improving,
        "abort_reason": abort_reason,
        "trajectory_mismatch": mismatch,
        "saved": saved,
        "checkpoint": str(OUT_W).replace("\\", "/") if saved else None,
        "ecology": str(OUT_E).replace("\\", "/") if saved else None,
        "saved_files": {
            "weights": _file_id(OUT_W) if saved else None,
            "ecology": _file_id(OUT_E) if saved else None,
        },
        "rows_trained": rows_trained,
        "rows_orphan": rows_orphan,
        "seconds": round(time.perf_counter() - t_all, 1),
    }
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(_jsonable(report), indent=2), encoding="utf-8")
    _log(f"WROTE {METRICS}")
    _log(f"stop_reason={stop_reason} still_improving={improving} saved={saved} seconds={report['seconds']}")
    if mismatch:
        return 3
    if abort_reason:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
