"""
tests/diagnostic/lockin/secondlocker_field_map_probe.py

Phase 3, Track B — SECOND-LOCKER field map: does the coherence pin hold across
seeds, token bands, and regimes with a trained generator? Plus Track A
piggyback: §6.3 gain-sign sampling on the REAL reachable coherence range
(the standalone gain_sign_check synthetic warm was CONFOUNDED — its phase-warm
cannot reach <0.49 and its control mixes metrics; see the 2026-06-12 finding).

The 2026-06-12 G2 finding flagged its own confound: one seed (42), one
workload (the 16-sequence canonical set) — "repetition itself sustains the
pin." This probe runs the matrix:

  TOKEN BANDS (v1 — versioned here; source structure HELD CONSTANT across
  bands: the 4 Resonance-Family source ids + weights, so HHI/monopoly effects
  cannot differ across cells — gate-decomposition lesson):
    canonical  16-seq Resonance Family workload (G2 anchor cell)
    broad      uniform sample over corpus v1.1.0 train sequences (full
               operational vocabulary; the high-novelty workload of the open
               ROADMAP item — Tier 4.3 chaotic-regime check rides this)
    rhythm     DEFAULT_RHYTHM_SEEDS (20 seqs, 4 rhythms)
    entry      recursion1188 DEFAULT_TOKENS + bootstrap WORDS 3-token chunks
    mixed      round-robin pool: canonical + rhythm + entry + 50 corpus seqs
               (corpus subsample fixed by rng(1188), stable across seeds)

  SEEDS: 42 (G2 anchor), 7, 11 (prior live-probe seeds).
  ARMS per cell: untrained-eval (control) vs pretrained-eval (the Phase 3
  Decision-1 operating mode; 8-epoch corpus v1.1.0 boot, per-seed checkpoint
  trained once and reused via Generator.save/load_checkpoint).

PRE-DECLARED SIGNATURES (before any run — discipline #3/#4):
  SECOND-LOCKER GENERALIZES: pretrained 2nd-half coherence >= 0.95 in every
      cell (controls also pinned) -> lock is seed-, band-, regime-invariant.
  BAND-DEPENDENT LOCK: >=1 band < 0.95 pretrained across ALL its seeds while
      its control stays >= 0.95 and canonical stays pinned -> the lock needs
      repetition; SECOND-LOCKER must be scoped, not generalized.
  CONFOUNDED(band): a band's CONTROL unpins too -> the band itself breaks
      coherence regardless of weights; pin readout not attributable to training.
  CHAOTIC REACHED: phase_coherence < 0.5 beyond step 0 in any cell -> the
      Tier 4.3 chaotic-regime half-validation closes (record either way).
  IDENTITY RAIL: identity_stability < 0.95 in any cell -> that (band, seed) is
      an identity-risk boundary; record, do not average away.
  GAIN-SIGN (per coherence bin, reachable range only):
      NEG = restoring force at that level; POS = amplifying (runaway side);
      |mean| <= noise floor (random-vec control magnitude) = CONFOUNDED bin.

Informational. exit 0. Trains once per seed (~minutes) + 30 x n_steps cycles.
NEVER in run_all_tests.sh. Findings must name corpus version + band defs v1.

Run:
    python -m tests.diagnostic.lockin.secondlocker_field_map_probe \
        [n_steps] [--seeds 42,7,11] [--bands canonical,broad,rhythm,entry,mixed] \
        [--epochs 8] [--json PATH]
"""

from __future__ import annotations

import json
import logging
import random
import sys
from collections import Counter, deque
from pathlib import Path

import numpy as np

logging.disable(logging.CRITICAL)

import torch

from tests._common import (RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,
                           build_full_stack, health_summary)
from training.corpus import TRAIN_PATH, corpus_version, load_corpus, to_rhythm_seeds
from training.rhythm_pretraining import (DEFAULT_RHYTHM_SEEDS, PretrainingConfig,
                                         RhythmPretrainer)
from training.run_contrastive_bootstrap import WORDS
from loop.recursion1188 import DEFAULT_TOKENS

TIER1_BASELINE = (Path(__file__).resolve().parent.parent.parent
                  / "baselines" / "tier1_revision_500step.json")
CHECKPOINT_DIR = (Path(__file__).resolve().parent.parent.parent.parent
                  / "data" / "checkpoints")

BAND_DEFS_VERSION = "v1"
GAIN_SAMPLE_EVERY = 25     # steps between in-run gain-sign samples
GAIN_N_PROBES = 6          # recent-derived probe vecs per sample


def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _eff_rank(mat: np.ndarray) -> float:
    """Participation-ratio effective rank of row vectors."""
    if len(mat) < 2:
        return 1.0
    s = np.linalg.svd(mat - mat.mean(0), compute_uv=False)
    p = (s ** 2) / max((s ** 2).sum(), 1e-12)
    return float(1.0 / max((p ** 2).sum(), 1e-12))


def _band_sequences(band: str) -> list:
    """Token-sequence pool for a band (definitions v1 — see header)."""
    canonical = [seq for seqs in RESONANCE_FAMILY_SOURCES.values() for seq in seqs]
    if band == "canonical":
        return canonical
    if band == "rhythm":
        return [seq for seqs in DEFAULT_RHYTHM_SEEDS.values() for seq in seqs]
    if band == "entry":
        words3 = [list(WORDS[i:i + 3]) for i in range(0, len(WORDS) - 2, 3)]
        return [list(s) for s in DEFAULT_TOKENS] + words3
    if band == "broad":
        return [r["tokens"] for r in load_corpus(TRAIN_PATH)]
    if band == "mixed":
        rng = np.random.default_rng(1188)  # fixed: band def stable across seeds
        corpus = [r["tokens"] for r in load_corpus(TRAIN_PATH)]
        sub = [corpus[i] for i in rng.choice(len(corpus), size=50, replace=False)]
        rhythm = [seq for seqs in DEFAULT_RHYTHM_SEEDS.values() for seq in seqs]
        words3 = [list(WORDS[i:i + 3]) for i in range(0, len(WORDS) - 2, 3)]
        entry = [list(s) for s in DEFAULT_TOKENS] + words3
        return canonical + rhythm + entry + sub
    raise ValueError(f"unknown band: {band}")


def _seed_checkpoint(seed: int, n_epochs: int) -> tuple:
    """Train the boot generator once per seed; reuse via checkpoint."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    stem = CHECKPOINT_DIR / f"fieldmap_{corpus_version()}_{n_epochs}ep_s{seed}"
    wp, ep = str(stem) + ".pt", str(stem) + ".ecology.json"
    if Path(wp).exists() and Path(ep).exists():
        return wp, ep
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack()
    trainer = RhythmPretrainer(gen,
                               rhythm_seeds=to_rhythm_seeds(load_corpus(TRAIN_PATH)),
                               config=PretrainingConfig(n_epochs=n_epochs))
    trainer.pretrain()
    gen.save_checkpoint(wp, ep)
    return wp, ep


def run_cell(band: str, seed: int, pretrained: bool, n_steps: int,
             n_epochs: int) -> dict:
    """One (band, seed, arm) run: eval-mode boot + n_steps, full readouts."""
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack()
    if pretrained:
        wp, ep = _seed_checkpoint(seed, n_epochs)
        gen.load_checkpoint(wp, ep)
    gen.eval()  # Phase 3 Decision 1: eval-mode operating regime

    # identical source/token order across the two arms of a cell
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)

    # instrumentation (non-invasive, the G2-probe pattern)
    decisions: Counter = Counter()
    orig_arb = gov.arbitrate
    def counted_arb(*a, **k):
        dec, strength = orig_arb(*a, **k)
        decisions[dec.value] += 1
        return dec, strength
    gov.arbitrate = counted_arb

    manip = {"steps": 0}
    orig_detect = gov.resistance.detect
    def counted_detect():
        sigs = orig_detect()
        if sigs:
            manip["steps"] += 1
        return sigs
    gov.resistance.detect = counted_detect

    pcs: list = []
    orig_dil = cycle.stream.update_dilation
    def logged_dil(*args, **kwargs):
        pc = kwargs.get("phase_coherence", args[2] if len(args) > 2 else 0.5)
        pcs.append(float(pc))
        return orig_dil(*args, **kwargs)
    cycle.stream.update_dilation = logged_dil

    gen_outs: deque = deque(maxlen=512)
    orig_generate = cycle.generator.generate
    def capturing_generate(*a, **k):
        out = orig_generate(*a, **k)
        gen_outs.append(np.asarray(out, dtype=float))
        return out
    cycle.generator.generate = capturing_generate

    seqs = _band_sequences(band)
    sids = list(RESONANCE_FAMILY_SOURCES)
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    cohs, rhythms, gain_samples = [], [], []
    probe_rng = np.random.default_rng(seed + 7000)
    for t in range(n_steps):
        # §6.3 piggyback: observe-only, BEFORE this step's injection
        # (guardrail: coherence_impact is only meaningful pre-inject)
        if t % GAIN_SAMPLE_EVERY == 0 and len(cycle.field.history) >= 8:
            level = float(cycle.field.internal_coherence())
            pool = list(cycle.field.history)[-16:]
            recent, anti = [], []
            for _ in range(GAIN_N_PROBES):
                base = pool[probe_rng.integers(len(pool))]
                v = _unit(np.asarray(base) + 0.10 * probe_rng.standard_normal(len(base)))
                recent.append(float(cycle.field.coherence_impact(v)))
                anti.append(float(cycle.field.coherence_impact(-v)))
            novel = [float(cycle.field.coherence_impact(
                _unit(probe_rng.standard_normal(len(pool[0])))))
                for _ in range(GAIN_N_PROBES)]
            gain_samples.append({
                "step": t, "coherence_level": round(level, 4),
                "recent_mean": round(float(np.mean(recent)), 6),
                "novel_mean": round(float(np.mean(novel)), 6),
                "anti_mean": round(float(np.mean(anti)), 6),
            })
        src = random.choices(sids, weights=weights)[0]
        toks = random.choice(seqs)
        st = cycle.step(toks, source_id=src, origin_type="internal")
        cohs.append(st.coherence)
        rhythms.append(st.rhythm)

    half = np.array(cohs[n_steps // 2:])
    transitions = sum(1 for a, b in zip(rhythms, rhythms[1:]) if a != b)
    gmat = np.array(gen_outs)
    metrics = {
        "band": band, "seed": seed,
        "arm": "pretrained" if pretrained else "control",
        "coherence_mean": round(float(half.mean()), 4),
        "coherence_std": round(float(half.std()), 4),
        "identity_stability": round(float(cycle.witness.identity_stability()), 4),
        "anchor_velocity": round(float(cycle.witness.anchor_velocity()), 4),
        "eff_rank": round(_eff_rank(gmat), 3),
        "mean_cos": round(float(np.mean([
            np.dot(_unit(gmat[i]), _unit(gmat[j]))
            for i in range(0, len(gmat) - 1, 7)
            for j in range(i + 1, min(i + 8, len(gmat)), 3)])), 3) if len(gmat) > 8 else None,
        "pc_mean": round(float(np.mean(pcs)), 4) if pcs else None,
        "pc_min_post0": round(float(np.min(pcs[1:])), 4) if len(pcs) > 1 else None,
        "rhythm_transitions": transitions,
        "rhythm_mean_dwell": round(n_steps / (transitions + 1), 1),
        "rhythm_mix": dict(Counter(rhythms)),
        "attractors": len(cycle.attractor.centers),
        "crystals": len(cycle.crystal_store.crystals),
        "bonds": len(gov.bond_manager.all_bonds()),
        "manip_steps": manip["steps"],
        "health": health_summary(cycle, gov, ve, decisions),
        "gain_samples": gain_samples,
    }
    for mon_name in ("generator_metastability", "expression_metastability"):
        mon = getattr(cycle, mon_name, None)
        if mon is not None:
            mon.compute_now()
            snap = mon.snapshot()
            metrics[mon_name] = {k: snap[k] for k in
                                 ("metastability", "state", "n_regimes")}
    return metrics


def main(argv) -> int:
    n_steps = 500
    seeds = [42, 7, 11]
    bands = ["canonical", "broad", "rhythm", "entry", "mixed"]
    n_epochs = 8
    json_path = None
    args = list(argv)
    if args and not args[0].startswith("--"):
        n_steps = int(args.pop(0))
    while args:
        flag = args.pop(0)
        if flag == "--seeds":
            seeds = [int(s) for s in args.pop(0).split(",")]
        elif flag == "--bands":
            bands = args.pop(0).split(",")
        elif flag == "--epochs":
            n_epochs = int(args.pop(0))
        elif flag == "--json":
            json_path = Path(args.pop(0))

    version = corpus_version()
    ranges = json.loads(TIER1_BASELINE.read_text())["expected_ranges"]
    print("=" * 78)
    print("  DIAGNOSTIC: SECOND-LOCKER field map (Track B) + reachable-range")
    print("  gain-sign sampling (Track A piggyback)")
    print(f"  corpus v{version} · bands {BAND_DEFS_VERSION} · epochs={n_epochs} "
          f"· steps={n_steps} · seeds={seeds} · eval-mode (Decision 1)")
    print("=" * 78)

    cells = []
    for seed in seeds:
        for band in bands:
            for pretrained in (False, True):
                m = run_cell(band, seed, pretrained, n_steps, n_epochs)
                cells.append(m)
                rail = "  !! IDENTITY RAIL" if m["identity_stability"] < 0.95 else ""
                base_bad = [k for k, b in ranges.items()
                            if not (b["min"] <= m["health"][k] <= b["max"])]
                flag = f"  baseline-dev:{base_bad}" if base_bad else ""
                print(f'  s{seed:<3} {band:<10} {m["arm"]:<10} '
                      f'coh={m["coherence_mean"]:.4f} id={m["identity_stability"]:.4f} '
                      f'effR={m["eff_rank"]:6.2f} pc_min={m["pc_min_post0"]} '
                      f'dwell={m["rhythm_mean_dwell"]:6.1f} manip={m["manip_steps"]}'
                      f'{rail}{flag}')

    # ----- field-map verdicts (pre-declared) -----
    print("-" * 78)
    pin = {}
    for band in bands:
        pre = [c for c in cells if c["band"] == band and c["arm"] == "pretrained"]
        ctl = [c for c in cells if c["band"] == band and c["arm"] == "control"]
        pre_pinned = all(c["coherence_mean"] >= 0.95 for c in pre)
        ctl_pinned = all(c["coherence_mean"] >= 0.95 for c in ctl)
        if not ctl_pinned:
            v = "CONFOUNDED (control unpins — band breaks coherence itself)"
        elif pre_pinned:
            v = "pinned (lock holds)"
        else:
            v = "UNPINNED under trained weights (band-dependent lock)"
        pin[band] = v
        print(f"  {band:<10} -> {v}")
    if all("pinned (lock holds)" in v for v in pin.values()):
        print("  VERDICT: SECOND-LOCKER GENERALIZES — seed-, band-, regime-invariant.")
    chaotic = [c for c in cells
               if c["pc_min_post0"] is not None and c["pc_min_post0"] < 0.5]
    print(f'  Tier 4.3 chaotic regime: '
          f'{"REACHED in " + str(len(chaotic)) + " cells" if chaotic else "still unreached in every cell"}')
    rails = [c for c in cells if c["identity_stability"] < 0.95]
    print(f'  identity rail: {len(rails)} cell(s) below 0.95'
          + (f' — {[ (c["band"], c["seed"], c["arm"]) for c in rails ]}' if rails else ""))

    # ----- §6.3 gain-sign over the reachable range -----
    print("-" * 78)
    print("  §6.3 gain-sign (reachable range, real field states, real probe vecs):")
    samples = [g for c in cells for g in c["gain_samples"]]
    if samples:
        levels = np.array([s["coherence_level"] for s in samples])
        print(f'  coherence levels reached: [{levels.min():.3f}, {levels.max():.3f}] '
              f'(n={len(samples)})')
        bins = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.01)]
        for lo, hi in bins:
            sel = [s for s in samples if lo <= s["coherence_level"] < hi]
            if not sel:
                print(f"    [{lo:.2f},{hi:.2f}) — unreachable (no samples)")
                continue
            rec = float(np.mean([s["recent_mean"] for s in sel]))
            nov = float(np.mean([s["novel_mean"] for s in sel]))
            ant = float(np.mean([s["anti_mean"] for s in sel]))
            noise = max(1e-6, abs(nov) * 0.25)
            sign = ("CONFOUND" if abs(rec) <= noise
                    else ("POS (amplifying)" if rec > 0 else "NEG (restoring)"))
            print(f"    [{lo:.2f},{hi:.2f}) n={len(sel):<4} recent={rec:+.5f} "
                  f"novel={nov:+.5f} anti={ant:+.5f} -> {sign}")

    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps({
            "corpus_version": version, "band_defs": BAND_DEFS_VERSION,
            "n_steps": n_steps, "n_epochs": n_epochs, "seeds": seeds,
            "bands": bands, "cells": cells}, indent=1))
        print(f"  raw matrix written: {json_path}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
