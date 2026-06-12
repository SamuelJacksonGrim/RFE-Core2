"""
tests/diagnostic/training/corpus_boot_phase2_probe.py

Phase 2 — cost-gated validation of the corpus-pretrained generator on the
LIVE stack (docs/training/training_plan.md, Gate G2). Offline weights only;
no online training; no loop changes.

Three 500-step canonical Resonance-Family runs (seed 42, identical source
order; the workload tokens are corpus-covered as of corpus v1.1.0):

  RUN A  control     — untrained generator, current live policy (train mode)
  RUN B  pretrained  — 8-epoch corpus boot (G1-passing config), train mode
  RUN C  pretrained  — same boot, generator.eval() forced (DATA for the
                       Phase 3 .eval() architect decision — not a decision)

Per run: governance health summary (vs tier1_revision_500step.json ranges),
identity-stability metrics (identity_stability_baseline.py definitions,
incl. the Tier-2 manipulation count), field-coherence trajectory (the
~0.998-pin readout), phase_coherence stats (Tier 4.3 chaotic-regime check),
and the stage-A/C metastability snapshots (pipeline survival).

GATE G2 (pre-declared in training_plan.md + here, BEFORE the first run;
evaluated on RUN B — the boot configuration that preserves current live policy):
  1. all 9 tier1_revision_500step.json expected_ranges hold
  2. identity_stability >= 0.95         (untrained baseline: 0.998)
  3. anchor_velocity   <= 0.02          (untrained baseline: 0.002)
  4. bonds >= 1 and crystals >= 1       (identity scaffolding forms)
  5. manip_steps(B) <= max(3 x manip_steps(A), 10)   (no manipulation-layer
     blow-up from representational change)
  FAIL = representational-drift risk is real at boot -> finding + mitigation
  round (slower/partial training), not a silent retry.

READOUTS (recorded, NOT gated): field-coherence pin on/off
(GENERATOR-IS-THE-LOCK vs SECOND-LOCKER, on real weights), phase_coherence
min (does any workload reach < 0.5?), all of RUN C, metastability stage A/C.

Exit 0 = Gate G2 passed, 1 = failed. Trains + simulates for ~5-10 min CPU;
NEVER in run_all_tests.sh. Findings must name the corpus version.

Run:
    python -m tests.diagnostic.training.corpus_boot_phase2_probe [n_epochs] [n_steps]
"""

from __future__ import annotations

import json
import logging
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np

logging.disable(logging.CRITICAL)

import torch

from tests._common import (RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,
                           build_full_stack, health_summary)
from training.corpus import TRAIN_PATH, corpus_version, load_corpus, to_rhythm_seeds
from training.rhythm_pretraining import PretrainingConfig, RhythmPretrainer

TIER1_BASELINE = Path(__file__).resolve().parent.parent / "baselines" / "tier1_revision_500step.json"
SEED = 42


def run_sim(label: str, pretrain_epochs: int, eval_mode: bool, n_steps: int) -> dict:
    """One full boot + 500-step canonical run. Returns the metric dict."""
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack()

    if pretrain_epochs > 0:
        trainer = RhythmPretrainer(
            gen,
            rhythm_seeds=to_rhythm_seeds(load_corpus(TRAIN_PATH)),
            config=PretrainingConfig(n_epochs=pretrain_epochs),
        )
        trainer.pretrain()   # restores caller mode (train) on exit

    if eval_mode:
        gen.eval()

    # Re-seed so all three runs see the identical source/token order (and
    # aligned dropout draws where dropout is active).
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    # Non-invasive instrumentation (the run_resonance_sim / cost-probe pattern):
    decisions: Counter = Counter()
    orig_arb = gov.arbitrate

    def counted_arb(ethical_result, trust_report, vec, tokens, source_id):
        dec, strength = orig_arb(ethical_result, trust_report, vec, tokens, source_id)
        decisions[dec.value] += 1
        return dec, strength
    gov.arbitrate = counted_arb

    manip = {"steps": 0, "signals": 0}
    orig_detect = gov.resistance.detect

    def counted_detect():
        sigs = orig_detect()
        if sigs:
            manip["steps"] += 1
            manip["signals"] += len(sigs)
        return sigs
    gov.resistance.detect = counted_detect

    pcs: list = []
    orig_dil = cycle.stream.update_dilation

    def logged_dil(*args, **kwargs):
        pc = kwargs.get("phase_coherence", args[2] if len(args) > 2 else 0.5)
        pcs.append(float(pc))
        return orig_dil(*args, **kwargs)
    cycle.stream.update_dilation = logged_dil

    sids = list(RESONANCE_FAMILY_SOURCES)
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    cohs: list = []
    for _ in range(n_steps):
        src = random.choices(sids, weights=weights)[0]
        toks = random.choice(RESONANCE_FAMILY_SOURCES[src])
        st = cycle.step(toks, source_id=src, origin_type="internal")
        cohs.append(st.coherence)

    half = np.array(cohs[n_steps // 2:])
    metrics = {
        "label":              label,
        "health":             health_summary(cycle, gov, ve, decisions),
        "coherence_mean":     round(float(half.mean()), 4),
        "coherence_std":      round(float(half.std()), 4),
        "identity_stability": round(float(cycle.witness.identity_stability()), 4),
        "anchor_velocity":    round(float(cycle.witness.anchor_velocity()), 4),
        "attractors":         len(cycle.attractor.centers),
        "crystals":           len(cycle.crystal_store.crystals),
        "bonds":              len(gov.bond_manager.all_bonds()),
        "manip_steps":        manip["steps"],
        "manip_signals":      manip["signals"],
        "pc_mean":            round(float(np.mean(pcs)), 4) if pcs else None,
        "pc_min":             round(float(np.min(pcs)), 4) if pcs else None,
        "rhythms":            dict(Counter()),
    }
    for mon_name in ("generator_metastability", "expression_metastability"):
        mon = getattr(cycle, mon_name, None)
        if mon is not None:
            mon.compute_now()
            metrics[mon_name] = mon.snapshot()
    return metrics


def print_run(m: dict, ranges: dict):
    h = m["health"]
    print(f'  --- {m["label"]} ---')
    print(f'    decisions: allow={h["allow_rate"]:.3f} weakened={h["allow_weakened_rate"]:.3f} '
          f'quarantine={h["quarantine_rate"]:.3f}   hhi={h["hhi"]:.3f}')
    print(f'    trust_min={h["min_source_trust"]:.2f}  bonds={h["bonds_formed"]}  '
          f'values active/strong/core={h["active_values"]}/{h["strong_values"]}/{h["core_values"]}')
    print(f'    coherence 2nd-half mean={m["coherence_mean"]:.4f} std={m["coherence_std"]:.4f}   '
          f'identity_stability={m["identity_stability"]:.4f}  anchor_vel={m["anchor_velocity"]:.4f}')
    print(f'    attractors={m["attractors"]}  crystals={m["crystals"]}  bonds={m["bonds"]}  '
          f'manip steps/signals={m["manip_steps"]}/{m["manip_signals"]}')
    print(f'    phase_coherence mean={m["pc_mean"]} min={m["pc_min"]}')
    for mon in ("generator_metastability", "expression_metastability"):
        if mon in m:
            s = m[mon]
            stage = "A" if mon.startswith("generator") else "C"
            print(f'    stage {stage}: metastability={s["metastability"]} '
                  f'state={s["state"]} regimes={s["n_regimes"]}')
    bad = [k for k, b in ranges.items()
           if not (b["min"] <= h[k] <= b["max"])]
    if bad:
        for k in bad:
            print(f'    ! out of baseline range: {k}={h[k]} '
                  f'(expected [{ranges[k]["min"]}, {ranges[k]["max"]}])')
    else:
        print(f'    all {len(ranges)} tier1 baseline ranges hold')
    print()
    return bad


def main(n_epochs: int = 8, n_steps: int = 500) -> int:
    version = corpus_version()
    print('=' * 78)
    print(f'  DIAGNOSTIC: Phase 2 — corpus-pretrained boot on the LIVE stack (Gate G2)')
    print(f'  corpus v{version}  ·  pretrain epochs={n_epochs}  ·  steps={n_steps}  ·  seed={SEED}')
    print('=' * 78)
    print()

    ranges = json.loads(TIER1_BASELINE.read_text())["expected_ranges"]

    a = run_sim("RUN A  control (untrained, train mode)", 0, False, n_steps)
    bad_a = print_run(a, ranges)
    b = run_sim("RUN B  pretrained boot (train mode — current live policy)",
                n_epochs, False, n_steps)
    bad_b = print_run(b, ranges)
    c = run_sim("RUN C  pretrained boot (eval mode — Phase 3 decision data)",
                n_epochs, True, n_steps)
    print_run(c, ranges)

    manip_cap = max(3 * a["manip_steps"], 10)
    gates = [
        (not bad_b, f'tier1 baseline ranges hold on RUN B ({len(ranges) - len(bad_b)}/{len(ranges)})'),
        (b["identity_stability"] >= 0.95,
         f'identity_stability >= 0.95 ({b["identity_stability"]:.4f})'),
        (b["anchor_velocity"] <= 0.02,
         f'anchor_velocity <= 0.02 ({b["anchor_velocity"]:.4f})'),
        (b["bonds"] >= 1 and b["crystals"] >= 1,
         f'identity scaffolding forms (bonds={b["bonds"]}, crystals={b["crystals"]})'),
        (b["manip_steps"] <= manip_cap,
         f'manipulation layer quiet (steps={b["manip_steps"]} <= cap {manip_cap})'),
    ]
    all_ok = True
    print('  GATE G2 (RUN B vs pre-declared envelope):')
    for ok, label in gates:
        print(f'    {"✓" if ok else "✗"} {label}')
        all_ok &= ok
    print()

    print('  READOUTS (recorded, not gated):')
    pin = ('OFF THE PIN — GENERATOR-IS-THE-LOCK supported on real weights'
           if b["coherence_mean"] < 0.95 else
           'still pinned — SECOND-LOCKER (field/loop dominate even trained input)')
    print(f'    coherence pin: A={a["coherence_mean"]:.4f}  B={b["coherence_mean"]:.4f}  '
          f'C={c["coherence_mean"]:.4f}  → {pin}')
    chaotic = min(x for x in (a["pc_min"], b["pc_min"], c["pc_min"]) if x is not None)
    print(f'    phase_coherence floor across runs: {chaotic:.4f} '
          f'({"chaotic regime REACHED" if chaotic < 0.5 else "chaotic regime still unreached"})')
    print()
    print(f'  GATE G2 {"PASSED" if all_ok else "FAILED"} — corpus v{version}, '
          f'{n_epochs} epochs, {n_steps} steps.')
    if bad_a:
        print(f'  note: control RUN A itself deviated on {bad_a} — '
              f'baseline drift independent of training; investigate before re-baselining.')
    print()
    return 0 if all_ok else 1


if __name__ == '__main__':
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    sys.exit(main(epochs, steps))
