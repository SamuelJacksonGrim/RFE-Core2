"""
tests/diagnostic/sidecar/fullsend_feedback_256_probe.py

Same governed-feedback A/B as fullsend_feedback_probe.py. One variable
changes: the full-send arm's encoder is the dim-256 completion field,
not the dim-128 one.

The 128 arm loaded generator_weights_completion_128_emb.pt and set
Generator.embedding_residual (the flag is not in the checkpoint). That
reading measured holdout field participation 47.806. The same recipe at
256 is generator_weights_completion_256_emb.pt with the flag on.
Published field participation 81.9; this probe remeasures it before any
cell and aborts outside [78, 88].

generator_weights_completion_256_resid.pt is a different recipe (the
transformer was trained behind the residual). Its residual-on field
participation is ~73.5, and it is not this arm. Loading it would change
the training recipe as well as the width. The probe measures that file
and records it. It does not load it into a cell.

The completion head is the mouth. The 128 probe did not load one, and
neither does this. The head is hashed so the bundle on disk is named.

Arms, levers, gate, seeds, and the token seam are the 128 probe's.
Baseline stays on the dim-128 5-rhythm checkpoint: those weights do not
load into a dim-256 generator. The full-send arm is a fresh dim-256
stack. Both are in-memory. No persist_path. No GPU.

    python -m tests.diagnostic.sidecar.fullsend_feedback_256_probe
    python -m tests.diagnostic.sidecar.fullsend_feedback_256_probe --steps 30 --seeds 42
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

# CPU only. The 5070 Ti may be serving :1234; this probe must not take it.
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import numpy as np

logging.disable(logging.CRITICAL)

import torch

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests._common import (RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,
                           build_full_stack)
from tests.diagnostic.sidecar.sidecar_harness import (CycleTap, LAESidecar,
                                                      PLESidecar)
from tools.completion.geometry import encode_texts, load_generator, population
from tools.completion.live_guard import assert_live_intact, sha256
from training.corpus import HOLDOUT_PATH, corpus_version, load_corpus

CKPT = REPO / "data" / "checkpoints"
OLD_WEIGHTS = CKPT / "generator_weights_5rhythm.pt"
OLD_ECOLOGY = CKPT / "generator_ecology_5rhythm.json"
NEW_WEIGHTS = CKPT / "generator_weights_completion_256_emb.pt"
NEW_ECOLOGY = CKPT / "generator_ecology_completion_256_emb.json"
NEW_HEAD = CKPT / "completion_head_256_emb.pt"
# Measured, not loaded. Stack-trained residual variant. Not the ~82 field.
NAMED_RESID_WEIGHTS = CKPT / "generator_weights_completion_256_resid.pt"
NAMED_RESID_ECOLOGY = CKPT / "generator_ecology_completion_256_resid.json"
NAMED_RESID_HEAD = CKPT / "completion_head_256_resid.pt"

SUMMARY_PATH = (REPO / "docs" / "findings" / "logs"
                / "2026-09-23-fullsend-feedback-256" / "summary.json")

SEEDS_DEFAULT = (42, 7, 11)
BOOT_AT = 50
LATE_AT = 200
COS_SPLIT = 0.90
MIN_FRAC = 0.15
ARCH_BASELINE = dict(vocab_size=8192, dim=128, depth=4, heads=4)
ARCH_FULLSEND = dict(vocab_size=8192, dim=256, depth=4, heads=4)


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    n = float(np.linalg.norm(v))
    return v / (n + 1e-12)


def grooves(units: np.ndarray) -> dict:
    """Farthest-point grooves. Deterministic. Same rule as the 128 probe."""
    if len(units) < 10:
        return {"n_grooves": 0, "n_raw": 0, "occupancy": [], "centroids": []}
    mean = _unit(units.mean(axis=0))
    medoids = [mean]
    while len(medoids) < 8:
        cos = units @ np.stack(medoids).T
        nearest = cos.max(axis=1)
        j = int(np.argmin(nearest))
        if float(nearest[j]) >= COS_SPLIT:
            break
        medoids.append(units[j])
    cos = units @ np.stack(medoids).T
    lab = cos.argmax(axis=1)
    counts = np.bincount(lab, minlength=len(medoids))
    frac = counts / max(len(units), 1)
    keep = [i for i in range(len(medoids)) if frac[i] >= MIN_FRAC]
    return {
        "n_grooves": int(len(keep)),
        "n_raw": int(len(medoids)),
        "occupancy": [round(float(frac[i]), 4) for i in keep],
        "centroids": [medoids[i] for i in keep],
    }


def classify(m: dict) -> str:
    fragmented = (
        m["late_identity_mean"] < 0.95
        or m["frac_identity_below_090"] > 0.02
        or m["late_coherence_mean"] < 0.80
    )
    if fragmented:
        return "FRAGMENTED"
    hovering = m["n_grooves"] >= 2 or (m["n_grooves"] == 0 and m["n_raw"] >= 3)
    if hovering:
        return "METASTABLE"
    return "RIGID"


def groove_relation(g: dict, boot: np.ndarray) -> str:
    if g["n_grooves"] >= 2 or (g["n_grooves"] == 0 and g["n_raw"] >= 3):
        return "HOVERING"
    if g["n_grooves"] == 1:
        cos = float(np.dot(_unit(g["centroids"][0]), _unit(boot)))
        return "RESTATED" if cos >= COS_SPLIT else "NEW_GROOVE"
    return "UNRESOLVED"


def _pin_cpu(gen) -> None:
    gen.to("cpu")
    gen.device = "cpu"


def _load(gen, weights: Path, ecology: Path, residual: bool) -> None:
    gen.load_checkpoint(str(weights), str(ecology))
    gen.embedding_residual = bool(residual)
    gen.eval()
    _pin_cpu(gen)


def _measure(dim: int, weights: Path, ecology: Path, residual: bool) -> dict:
    """Holdout field participation. Generator.forward, the 128 instrument."""
    gen = load_generator(dim, str(weights), str(ecology))
    _pin_cpu(gen)
    gen.embedding_residual = residual
    gen.eval()
    hold = load_corpus(HOLDOUT_PATH)
    Z = encode_texts(gen, [r["tokens"] for r in hold])
    pop = population(Z)
    pr = float(pop["participation_ratio"])
    out = {
        "participation_ratio": pr,
        "eff_rank": pop["eff_rank_512cap"],
        "residual": residual,
        "dim": dim,
        "out_dim": int(Z.shape[1]),
        "weights": weights.name,
        "sha256": sha256(weights),
    }
    del gen
    return out


def encoder_check(arm: str) -> dict:
    weights, ecology, residual, dim, lo, hi = {
        "baseline": (OLD_WEIGHTS, OLD_ECOLOGY, False, 128, 2.0, 8.0),
        "fullsend": (NEW_WEIGHTS, NEW_ECOLOGY, True, 256, 78.0, 88.0),
    }[arm]
    measured = _measure(dim, weights, ecology, residual)
    pr = measured["participation_ratio"]
    print(f"  encoder {arm}: residual={residual} dim={dim} "
          f"holdout_PR={pr:.3f} eff={measured['eff_rank']:.3f} "
          f"band=[{lo},{hi}]", flush=True)
    if not (lo <= pr <= hi):
        raise SystemExit(
            f"encoder sanity failed for {arm}: PR {pr} not in [{lo}, {hi}]. "
            f"Refusing to run the arm on the wrong manifold.")
    return measured


def run_cell(seed: int, arm: str, n_steps: int) -> dict:
    fullsend = arm == "fullsend"
    weights = NEW_WEIGHTS if fullsend else OLD_WEIGHTS
    ecology = NEW_ECOLOGY if fullsend else OLD_ECOLOGY
    arch = ARCH_FULLSEND if fullsend else ARCH_BASELINE

    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    gen, cycle, gov, _ve = build_full_stack(torch_seed=seed, use_chorus=True, **arch)
    _load(gen, weights, ecology, residual=fullsend)
    if int(gen.dim) != arch["dim"] or int(np.asarray(cycle.field.field).shape[-1]) != arch["dim"]:
        raise SystemExit(
            f"{arm} field dim {np.asarray(cycle.field.field).shape[-1]} "
            f"!= stack dim {arch['dim']}")
    # Reseed AFTER the load so both arms draw the same workload.
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if getattr(cycle, "dreamer", None) is not None:
        cycle.dreamer._rng = np.random.default_rng(seed)

    if fullsend:
        cycle.config["rupture_on_lock"] = True
        cycle.config["boredom_override_threshold"] = 0.25
        cycle.reflector.novelty_attenuation = True
        # Ceiling stays the validated 0.30. Do not raise it.
        if cycle.reflector.attenuation_max > 0.30 + 1e-9:
            raise SystemExit(
                f"attenuation_max is {cycle.reflector.attenuation_max}, "
                f"above the 0.30 cliff. Refusing to run hot past it.")
    else:
        cycle.config["rupture_on_lock"] = False
        cycle.config["boredom_override_threshold"] = 0.50
        cycle.reflector.novelty_attenuation = False

    tap = CycleTap(cycle, gov)
    tap.install()
    lae, ple = LAESidecar(), PLESidecar()

    sids = list(RESONANCE_FAMILY_SOURCES)
    wts = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    pending = []
    feedback_log = []

    rhythms, cohs, idents, gaps = [], [], [], []
    energies, n_attr, boredoms = [], [], []
    field_units = []
    workload_idx = []
    regimes = []
    wload = 0

    t0 = time.perf_counter()
    while wload < n_steps:
        if pending:
            flushed, pending = pending, []
            for src_id, f_toks in flushed:
                st = cycle.step(f_toks, source_id=src_id, origin_type="internal")
                cap = tap.read(st)
                _record(st, cycle, False, rhythms, cohs, idents, gaps,
                        energies, n_attr, boredoms, field_units, workload_idx,
                        regimes, wload)
                lae_offer = lae.after_step(st)
                ple_offers = ple.after_step(st, cap, arm)
                feedback_log.append({
                    "step": st.step, "source_id": src_id, "tokens": f_toks,
                    "decision": cap.decision,
                })
                if lae_offer:
                    pending.append(("lae_engine", lae_offer))
                pending.extend(("ple_engine", o) for o in ple_offers)
            pending = pending[:8]

        src = random.choices(sids, weights=wts)[0]
        toks = random.choice(RESONANCE_FAMILY_SOURCES[src])
        st = cycle.step(toks, source_id=src, origin_type="internal")
        cap = tap.read(st)
        _record(st, cycle, True, rhythms, cohs, idents, gaps,
                energies, n_attr, boredoms, field_units, workload_idx,
                regimes, wload)
        lae_offer = lae.after_step(st)
        ple_offers = ple.after_step(st, cap, arm)
        if lae_offer:
            pending.append(("lae_engine", lae_offer))
        pending.extend(("ple_engine", o) for o in ple_offers)
        pending = pending[:8]
        wload += 1
    elapsed = time.perf_counter() - t0
    tap.uninstall()

    units = np.stack(field_units)
    widx = np.asarray(workload_idx)
    boot_rows = np.flatnonzero(widx >= BOOT_AT)
    late_rows = np.flatnonzero(widx >= LATE_AT)
    boot_i = int(boot_rows[0]) if len(boot_rows) else len(units) // 10
    boot = units[boot_i]
    late = units[late_rows] if len(late_rows) >= 10 else units[len(units) // 2:]
    late_w = widx[late_rows] if len(late_rows) >= 10 else widx[len(widx) // 2:]
    g = grooves(late)
    disp = 1.0 - (late @ boot)
    late_mean = _unit(late.mean(axis=0))
    ident = np.asarray(idents, dtype=np.float64)
    coh = np.asarray(cohs, dtype=np.float64)
    late_mask = np.zeros(len(ident), dtype=bool)
    if len(late_rows):
        late_mask[late_rows] = True
    else:
        late_mask[len(ident) // 2:] = True

    post = widx >= BOOT_AT
    rhythm_arr = np.asarray(rhythms)
    post_r = rhythm_arr[post] if post.any() else rhythm_arr
    post_trans = int(sum(1 for a, b in zip(post_r, post_r[1:]) if a != b))
    late_r = rhythm_arr[late_mask]
    attr = np.asarray(n_attr)
    attr_at_boot = int(attr[boot_i])
    lae_steps = [a["cycle"] for a in lae.activation_log]
    lae_after = sum(1 for s in lae_steps if s > BOOT_AT)
    decisions = Counter(row["decision"] for row in feedback_log)
    ple_sum = ple.summary()
    gen_meta = cycle.generator_metastability.compute_now()
    exp_meta = cycle.expression_metastability.compute_now()

    measured = {
        "late_identity_mean": float(ident[late_mask].mean()) if late_mask.any() else float(ident.mean()),
        "frac_identity_below_090": float((ident < 0.90).mean()),
        "late_coherence_mean": float(coh[late_mask].mean()) if late_mask.any() else float(coh.mean()),
        "n_grooves": g["n_grooves"],
        "n_raw": g["n_raw"],
    }
    verdict = classify(measured) if n_steps > LATE_AT else "SHORT"
    relation = groove_relation(g, boot) if n_steps > LATE_AT else "SHORT"
    dominant_cos = None
    if g["centroids"]:
        k = int(np.argmax(g["occupancy"]))
        dominant_cos = round(float(np.dot(_unit(g["centroids"][k]), boot)), 4)

    return {
        "seed": seed,
        "arm": arm,
        "field_dim": int(units.shape[1]),
        "n_workload": n_steps,
        "n_executed": len(rhythms),
        "seconds": round(elapsed, 2),
        "verdict": verdict,
        "groove": relation,
        "displacement": {
            "late_mean": round(float(1.0 - np.dot(late_mean, boot)), 4),
            "late_max": round(float(disp.max()), 4),
            "late_p50": round(float(np.median(disp)), 4),
            "boot_step": int(boot_i),
            "dominant_groove_cos_to_boot": dominant_cos,
            "n_grooves": g["n_grooves"],
            "n_raw_modes": g["n_raw"],
            "groove_occupancy": g["occupancy"],
        },
        "identity": {
            "min": round(float(ident.min()), 4),
            "p05": round(float(np.quantile(ident, 0.05)), 4),
            "mean": round(float(ident.mean()), 4),
            "late_mean": round(measured["late_identity_mean"], 4),
            "frac_below_0.90": round(measured["frac_identity_below_090"], 4),
            "frac_below_0.95": round(float((ident < 0.95).mean()), 4),
            "late_anchor_gap_mean": round(float(np.asarray(gaps)[late_mask].mean()), 4),
        },
        "coherence": {
            "mean": round(float(coh.mean()), 4),
            "late_mean": round(measured["late_coherence_mean"], 4),
            "min": round(float(coh.min()), 4),
        },
        "novelty": {
            "post_boot_rhythm_transitions": post_trans,
            "late_rhythm_mix": dict(Counter(late_r.tolist())),
            "rhythm_mix_all": dict(Counter(rhythms)),
            "attractors_at_boot": attr_at_boot,
            "attractors_end": int(attr[-1]),
            "attractors_max": int(attr.max()),
            "attractors_formed_after_boot": int(attr[-1] - attr_at_boot),
            "crystals_end": len(cycle.crystal_store.crystals),
            "generator_regime": gen_meta.regime_state,
            "generator_metastability": round(float(gen_meta.metastability), 4),
            "generator_n_regimes": int(gen_meta.n_regimes),
            "expression_regime": exp_meta.regime_state,
            "expression_metastability": round(float(exp_meta.metastability), 4),
            "expression_n_regimes": int(exp_meta.n_regimes),
            "regime_samples_late": regimes[-max(1, len(regimes) // 2):],
        },
        "levers": {
            "rupture_on_lock": bool(cycle.config.get("rupture_on_lock", False)),
            "rupture_fires": int(getattr(cycle, "_rupture_fires", 0)),
            "novelty_attenuation": bool(cycle.reflector.novelty_attenuation),
            "attenuation_max": float(cycle.reflector.attenuation_max),
            "boredom_threshold": float(cycle.config.get("boredom_override_threshold", 0.50)),
            "boredom_overrides": int(cycle._boredom_overrides),
            "boredom_max": round(float(max(boredoms)), 4) if boredoms else None,
            "embedding_residual": bool(gen.embedding_residual),
        },
        "sisters": {
            "lae_activations": len(lae_steps),
            "lae_after_boot": lae_after,
            "lae_steps_head": lae_steps[:12],
            "lae_steps_tail": lae_steps[-6:],
            "feedback_offers": len(feedback_log),
            "feedback_decisions": dict(decisions),
            "ple_triggered_cycles": ple_sum["triggered_cycles"],
            "ple_validated_findings": ple_sum["validated_findings"],
            "ple_attractors": (ple_sum.get("ecology") or {}).get("attractors"),
            "ple_active_paradoxes": (ple_sum.get("ecology") or {}).get("active_paradoxes"),
        },
        "trace_tail": {
            "workload_index_last": int(late_w[-1]) if len(late_w) else None,
        },
    }


def _record(st, cycle, is_workload, rhythms, cohs, idents, gaps, energies,
            n_attr, boredoms, field_units, workload_idx, regimes, wload):
    rhythms.append(st.rhythm)
    cohs.append(float(st.coherence))
    idents.append(float(cycle.witness.identity_stability()))
    gaps.append(float(cycle.witness.anchor_short_long_gap()))
    energies.append(float(st.field_energy))
    n_attr.append(len(cycle.attractor.centers))
    boredoms.append(float(cycle.emotion.boredom))
    field_units.append(_unit(cycle.field.field))
    workload_idx.append(wload if is_workload else max(wload - 1, 0))
    if cycle.generator_metastability is not None and (len(rhythms) % 50 == 0):
        regimes.append(cycle.generator_metastability.report.regime_state)


def _arm_row(cells: list) -> dict:
    def mean(key_path):
        vals = []
        for c in cells:
            cur = c
            for k in key_path:
                cur = cur[k]
            if isinstance(cur, (int, float)):
                vals.append(float(cur))
        return round(float(np.mean(vals)), 4) if vals else None

    return {
        "n": len(cells),
        "verdicts": [c["verdict"] for c in cells],
        "grooves": [c["groove"] for c in cells],
        "field_dim": cells[0]["field_dim"] if cells else None,
        "displacement_late_mean": mean(("displacement", "late_mean")),
        "cos_to_boot": mean(("displacement", "dominant_groove_cos_to_boot")),
        "n_grooves": mean(("displacement", "n_grooves")),
        "identity_min": mean(("identity", "min")),
        "identity_late_mean": mean(("identity", "late_mean")),
        "coherence_late_mean": mean(("coherence", "late_mean")),
        "post_boot_rhythm_transitions": mean(("novelty", "post_boot_rhythm_transitions")),
        "attractors_end": mean(("novelty", "attractors_end")),
        "generator_n_regimes": mean(("novelty", "generator_n_regimes")),
        "expression_n_regimes": mean(("novelty", "expression_n_regimes")),
        "generator_metastability": mean(("novelty", "generator_metastability")),
        "expression_metastability": mean(("novelty", "expression_metastability")),
        "rupture_fires": mean(("levers", "rupture_fires")),
        "boredom_overrides": mean(("levers", "boredom_overrides")),
        "lae_activations": mean(("sisters", "lae_activations")),
        "feedback_offers": mean(("sisters", "feedback_offers")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=500)
    ap.add_argument("--seeds", default="42,7,11")
    ap.add_argument("--json", default="")
    ap.add_argument("--arms", default="baseline,fullsend")
    args = ap.parse_args()
    seeds = tuple(int(s) for s in args.seeds.split(",") if s.strip())
    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    out = Path(args.json) if args.json else SUMMARY_PATH

    print("full-send feedback probe, dim-256 encoder", flush=True)
    print(f"  corpus {corpus_version()}  steps {args.steps}  seeds {seeds}  arms {arms}",
          flush=True)
    live = assert_live_intact()
    print("  live corpus + 5rhythm checkpoint hashes match the guard", flush=True)

    for p in (OLD_WEIGHTS, OLD_ECOLOGY, NEW_WEIGHTS, NEW_ECOLOGY, NEW_HEAD,
              NAMED_RESID_WEIGHTS, NAMED_RESID_ECOLOGY, NAMED_RESID_HEAD):
        if not p.is_file():
            raise SystemExit(f"missing checkpoint: {p}")

    enc = {arm: encoder_check(arm) for arm in arms}
    # The file the brief named. Recorded so the gate can see it was not ~82.
    named = _measure(256, NAMED_RESID_WEIGHTS, NAMED_RESID_ECOLOGY, True)
    print(f"  named 256_resid NOT loaded: residual=True dim=256 "
          f"holdout_PR={named['participation_ratio']:.3f} "
          f"eff={named['eff_rank']:.3f}", flush=True)

    cells = []
    t_all = time.perf_counter()
    for seed in seeds:
        for arm in arms:
            print(f"--- seed {seed}  {arm} ---", flush=True)
            cell = run_cell(seed, arm, args.steps)
            cells.append(cell)
            d = cell["displacement"]
            print(
                f"    {cell['verdict']:11} {cell['groove']:11} "
                f"dim {cell['field_dim']} "
                f"disp {d['late_mean']:.3f} (max {d['late_max']:.3f}) "
                f"id_min {cell['identity']['min']:.4f} "
                f"id_late {cell['identity']['late_mean']:.4f} "
                f"coh {cell['coherence']['late_mean']:.3f} "
                f"grooves {d['n_grooves']} occ {d['groove_occupancy']} "
                f"attr {cell['novelty']['attractors_end']} "
                f"gen {cell['novelty']['generator_n_regimes']} "
                f"expr {cell['novelty']['expression_n_regimes']} "
                f"rtrans {cell['novelty']['post_boot_rhythm_transitions']} "
                f"lae {cell['sisters']['lae_activations']} "
                f"rupture {cell['levers']['rupture_fires']} "
                f"({cell['seconds']:.1f}s)",
                flush=True,
            )
            _dump(out, cells, enc, named, live, seeds, arms, args.steps, partial=True)

    by_arm = {arm: _arm_row([c for c in cells if c["arm"] == arm]) for arm in arms}
    payload = _payload(cells, enc, named, live, seeds, arms, args.steps, by_arm,
                       time.perf_counter() - t_all)
    _write(out, payload)
    print("\n==== arm means ====", flush=True)
    for arm, row in by_arm.items():
        print(f"  {arm}: {json.dumps(row)}", flush=True)
    print(f"wrote {out}", flush=True)
    assert_live_intact()
    print(f"  5rhythm unchanged sha256 {sha256(OLD_WEIGHTS)[:16]}", flush=True)
    print(f"  256 emb checkpoint unchanged sha256 {sha256(NEW_WEIGHTS)[:16]}", flush=True)
    return 0


def _payload(cells, enc, named, live, seeds, arms, steps, by_arm, seconds) -> dict:
    return {
        "probe": "fullsend_feedback_256",
        "date": "2026-09-23",
        "corpus": corpus_version(),
        "steps": steps,
        "seeds": list(seeds),
        "arms": list(arms),
        "seconds": round(seconds, 1),
        "encoder_choice": {
            "fullsend_weights": NEW_WEIGHTS.name,
            "why": ("analog of the 128 arm: embeddings-only checkpoint, "
                    "embedding_residual on. Published PR 81.9. "
                    "The *_256_resid.pt file is stack-trained and is not this arm."),
            "head_loaded": False,
            "head_sha256": sha256(NEW_HEAD),
            "named_resid_not_loaded": named,
            "named_resid_head_sha256": sha256(NAMED_RESID_HEAD),
        },
        "gate": {
            "cos_split": COS_SPLIT,
            "min_frac": MIN_FRAC,
            "boot_workload": BOOT_AT,
            "late_workload": LATE_AT,
            "fragment_identity_late_mean": 0.95,
            "fragment_frac_below_0.90": 0.02,
            "fragment_coherence_late_mean": 0.80,
            "attenuation_ceiling": 0.30,
            "fullsend_pr_band": [78.0, 88.0],
            "baseline_pr_band": [2.0, 8.0],
        },
        "encoders": enc,
        "hashes": {
            "generator_weights_5rhythm.pt": live[
                "data/checkpoints/generator_weights_5rhythm.pt"],
            "generator_weights_completion_256_emb.pt": sha256(NEW_WEIGHTS),
            "completion_head_256_emb.pt": sha256(NEW_HEAD),
        },
        "arms_mean": by_arm,
        "cells": cells,
    }


def _dump(out, cells, enc, named, live, seeds, arms, steps, partial: bool) -> None:
    by_arm = {}
    for arm in arms:
        got = [c for c in cells if c["arm"] == arm]
        if got:
            by_arm[arm] = _arm_row(got)
    payload = _payload(cells, enc, named, live, seeds, arms, steps, by_arm, 0.0)
    payload["partial"] = partial
    _write(out, payload)


def _write(out: Path, payload: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(out)


if __name__ == "__main__":
    sys.exit(main())
