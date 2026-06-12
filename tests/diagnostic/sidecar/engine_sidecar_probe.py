"""
tests/diagnostic/sidecar/engine_sidecar_probe.py

First instrumentation run for the LAE + PLE measurement sidecars
(tests/diagnostic/sidecar/sidecar_harness.py — mapping v1, and PLE frame
defs v1 in ple/integration/rfecore2hook.py): can the two engines measure
the running core without perturbing it, and does generator training change
what they read?

Matrix: seeds {42, 7, 11} x arm {control, pretrained} x mode {off, on,
feedback} = 18 runs of n_steps on the canonical Resonance-Family band
(band sweeps belong to the lockin arc), plus per-arm REPLAY-NOISE CONTROLS
and a LATENCY CONTROL. Pretrained boot reuses the lockin field-map
checkpoint stem (trained once per seed, cached); both arms run eval-mode
(Phase 3 Decision 1).

Phase 2 — governed feedback (mode "feedback"): sister offers re-enter the
host through the FRONT DOOR, never directly into the field. An LAE
activation offers ["liminal", top1, top2]; a new validated PLE finding
offers ["paradox", claim, attractor_type]. Offers are submitted on the
next cycle as cycle.step(tokens, source_id="lae_engine"/"ple_engine") —
subject to the ethical gate, trust ledger, manipulation resistance, and
SelfhoodGovernance.arbitrate() like any other source (the sidecars emit;
governance decides). The pending queue is bounded (8). Feedback cells are
NOT twin-checked — perturbation is the point; the observe-only cells are
their control.
FEEDBACK signatures (pre-declared): SUCCESS = sister inputs pass the gate
in >=1 cell AND identity_stability >= 0.95 everywhere (the observe->
feedback differential, including null, is the recordable result).
FAILURE = the gate rejects every sister input (immune system treats the
family as hostile — recordable), or no offers reach the gate anywhere.
RAIL = identity_stability < 0.95 in any feedback cell: record and stop.

Non-perturbation check (signatures v2): probe bring-up showed same-seed
sidecars-OFF replays diverge numerically from step 1 — the substrate is
wall-clock-coupled by design (crystal/attractor age decay, ethical flood
windows, witness/trust timestamps), so the v1 byte-identical-twin check is
unattainable on this substrate and was retired before the measurement run.
v2 uses two controls:
  - replay-noise control: NOISE_RUNS identical off-runs PER ARM measure the
    per-metric spread of bare re-runs (the noise floor). Per-arm matters:
    run 1 calibrated the floor on the control arm only and flagged a false
    state channel on s42-pretrained — the pretrained substrate's bare
    replay noise on identity metrics (~1.4e-3) is ~50x the control arm's
    (~2.5e-5), and the post-hoc pretrained-arm noise measurement covered
    the flagged delta entirely.
  - latency control: one off-run with a per-step sleep matched to the
    sidecars' measured per-step overhead. A wall-clock-coupled host
    responds to instrumentation LATENCY even when no state leaks; this
    control separates the timing channel from a state channel. (Calibrated
    on the control arm; applied to both — a known approximation.)
Twin verdicts per metric: within 2x replay noise -> clean;
exceeds noise but within 2x(noise + latency-control delta) ->
timing-explained (no state leak); beyond that -> CONFOUNDED.
Discrete event counts (crystals, attractors, rhythm transitions/mix) carry
a +-1 quantization allowance: bring-up showed bare off-runs flipping a
borderline crystallization by exactly 1 from timing jitter alone, so a
small-sample noise floor underestimates their spread; count effects
smaller than +-1 are below this probe's resolution (recorded as a threat).
The floor itself is a NOISE_RUNS-sample max-spread estimate and is noisy
at short n_steps — twin verdicts are meaningful at the default 500 steps,
not on the 60-step smoke configuration.
Per-step fingerprints (StepState.as_dict() minus key/elapsed_ms) are still
compared and the first divergence step reported. Neither sidecar consumes
the seeded RNG streams (LAE/PLE are zero-dep; IDs come from uuid4).

PRE-DECLARED SIGNATURES v2 (before the measurement run — discipline #3/#4):
  SUCCESS: every sidecars-on twin is clean or timing-explained; LAE
      registers >=1 activation per cell OR is explicably dormant
      (top-confidence histogram shows energies stayed deep in-band); PLE
      detects >=1 contradiction and forms >=1 attractor per cell. Any LAE
      trigger-mix / PLE ecology difference between control and pretrained
      beyond the across-seed spread is the differential finding; its
      absence is also a recordable result.
  FAILURE: LAE never activates in any cell AND the histograms show
      boundary-adjacent energies that should have fired (mapping v1
      miscalibrated); or PLE detects zero contradictions anywhere
      (discretization v1 too coarse).
  CONFOUNDED: any sidecars-on twin exceeds even the timing-explained
      threshold (a state channel exists; that cell's sidecar readouts are
      suspect until the leak is found); or rhythm never transitions in a
      cell (oscillation trigger structurally unreachable there — scope the
      LAE verdict to cells where it can fire).

Informational. exit 0. Trains once per seed (~minutes, cached) + 22 x
n_steps cycles. NEVER in run_all_tests.sh.

Run:
    python -m tests.diagnostic.sidecar.engine_sidecar_probe \
        [n_steps] [--seeds 42,7,11] [--epochs 8] [--json PATH]
"""

from __future__ import annotations

import json
import logging
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

logging.disable(logging.CRITICAL)

import torch

from tests._common import (RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,
                           build_full_stack)
from tests.diagnostic.sidecar.sidecar_harness import (CycleTap, LAESidecar,
                                                      PLESidecar)
from training.corpus import TRAIN_PATH, corpus_version, load_corpus, to_rhythm_seeds
from training.rhythm_pretraining import PretrainingConfig, RhythmPretrainer

CHECKPOINT_DIR = (Path(__file__).resolve().parent.parent.parent.parent
                  / "data" / "checkpoints")
NOISE_RUNS = 3          # replay-noise control repetitions PER ARM
NOISE_FACTOR = 2.0      # twin deltas must sit within NOISE_FACTOR x spread
# Discrete event counts flip by +-1 under bare replay timing jitter
# (observed in bring-up); below that resolution, allow it.
COUNT_METRICS = ("crystals", "attractors", "rhythm_transitions",
                 "rhythm_mix.stabilize", "rhythm_mix.dream",
                 "rhythm_mix.reflect", "rhythm_mix.explore")


def seed_checkpoint(seed: int, n_epochs: int) -> tuple:
    """Train the boot generator once per seed; reuse via checkpoint.
    Same stem as the lockin field-map probe so the cache is shared."""
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


def fingerprint(state) -> tuple:
    """Per-step trajectory fingerprint: everything in StepState.as_dict()
    except key (uuid4) and elapsed_ms (wall clock)."""
    d = state.as_dict()
    d.pop("key"); d.pop("elapsed_ms")
    d["tokens"] = tuple(d["tokens"])
    return tuple(sorted(d.items()))


def run_cell(seed: int, pretrained: bool, mode: str, n_steps: int,
             n_epochs: int, step_sleep: float = 0.0) -> dict:
    """One (seed, arm, mode) run: eval-mode boot + n_steps.

    mode: "off" (bare host), "on" (sidecars observe), "feedback" (sidecars
    observe AND their token offers re-enter through the front door —
    cycle.step with source_id "lae_engine"/"ple_engine", subject to the
    ethical gate, trust ledger, and governance like any other source).
    step_sleep > 0 is the latency control: an "off" run with a matched
    per-step delay, isolating the wall-clock channel."""
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack()
    if pretrained:
        wp, ep = seed_checkpoint(seed, n_epochs)
        gen.load_checkpoint(wp, ep)
    gen.eval()  # Phase 3 Decision 1: eval-mode operating regime

    # identical source/token order across all runs of a (seed, arm)
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)

    arm = "pretrained" if pretrained else "control"
    sidecars = mode in ("on", "feedback")
    tap = lae = ple = None
    if sidecars:
        tap = CycleTap(cycle, gov)
        tap.install()
        lae, ple = LAESidecar(), PLESidecar()

    sids = list(RESONANCE_FAMILY_SOURCES)
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    prints, cohs, rhythms = [], [], []
    pending, feedback_log = [], []
    t_loop0 = time.perf_counter()
    for _ in range(n_steps):
        # Phase 2: flush sister offers from the previous cycle through the
        # front door BEFORE this cycle's workload step. Feedback steps are
        # full cycle steps — the sisters observe their own echo.
        if mode == "feedback" and pending:
            flushed, pending = pending, []   # echo offers accumulate fresh
            for src_id, f_toks in flushed:
                st_f = cycle.step(f_toks, source_id=src_id,
                                  origin_type="internal")
                cap_f = tap.read(st_f)
                lae_offer = lae.after_step(st_f)
                ple_offers = ple.after_step(st_f, cap_f, arm)
                feedback_log.append({
                    "cycle":     st_f.step,
                    "source_id": src_id,
                    "tokens":    f_toks,
                    "decision":  cap_f.decision,
                    "coherence": round(st_f.coherence, 4),
                })
                if lae_offer:
                    pending.append(("lae_engine", lae_offer))
                pending.extend(("ple_engine", o) for o in ple_offers)
            pending = pending[:8]   # bounded: never flood the gate

        src = random.choices(sids, weights=weights)[0]
        toks = random.choice(RESONANCE_FAMILY_SOURCES[src])
        st = cycle.step(toks, source_id=src, origin_type="internal")
        prints.append(fingerprint(st))
        cohs.append(st.coherence)
        rhythms.append(st.rhythm)
        if sidecars:
            cap = tap.read(st)
            lae_offer = lae.after_step(st)
            ple_offers = ple.after_step(st, cap, arm)
            if mode == "feedback":
                if lae_offer:
                    pending.append(("lae_engine", lae_offer))
                pending.extend(("ple_engine", o) for o in ple_offers)
                pending = pending[:8]
        elif step_sleep > 0.0:
            time.sleep(step_sleep)
    per_step_s = (time.perf_counter() - t_loop0) / n_steps
    if sidecars:
        tap.uninstall()

    half = np.array(cohs[n_steps // 2:])
    transitions = sum(1 for a, b in zip(rhythms, rhythms[1:]) if a != b)
    mix = Counter(rhythms)
    cell = {
        "seed": seed, "arm": arm, "mode": mode,
        "per_step_s": round(per_step_s, 6),
        "fingerprint": prints,   # stripped before JSON dump
        "host": {
            "coherence_mean":     round(float(half.mean()), 6),
            "coherence_std":      round(float(half.std()), 6),
            "identity_stability": round(float(cycle.witness.identity_stability()), 6),
            "anchor_velocity":    round(float(cycle.witness.anchor_velocity()), 6),
            "rhythm_transitions": transitions,
            "rhythm_mix":         dict(mix),
            "crystals":           len(cycle.crystal_store.crystals),
            "attractors":         len(cycle.attractor.centers),
        },
        "lae": lae.summary() if sidecars else None,
        "ple": ple.summary() if sidecars else None,
    }
    if mode == "feedback":
        sisters = {}
        for sid in ("lae_engine", "ple_engine"):
            rec = gov.trust_ledger.sources.get(sid)
            sisters[sid] = {
                "trust_score":  round(float(rec.trust_score), 4) if rec else None,
                "interactions": rec.interaction_count if rec else 0,
            }
        cell["feedback"] = {
            "steps":          len(feedback_log),
            "decisions":      dict(Counter(e["decision"] for e in feedback_log)),
            "log":            feedback_log[:64],
            "sister_sources": sisters,
        }
    return cell


def host_metrics(cell: dict) -> dict:
    """Flat scalar view of a run's host summary, for twin comparison."""
    h = cell["host"]
    flat = {k: float(v) for k, v in h.items() if k != "rhythm_mix"}
    for band in ("stabilize", "dream", "reflect", "explore"):
        flat[f"rhythm_mix.{band}"] = float(h["rhythm_mix"].get(band, 0))
    return flat


def replay_spread(runs: list) -> dict:
    """Per-metric max pairwise |delta| across repeated identical runs."""
    metrics = [host_metrics(r) for r in runs]
    return {k: max(abs(a[k] - b[k]) for a in metrics for b in metrics)
            for k in metrics[0]}


def twin_check(off: dict, on: dict, spread: dict, latency_delta: dict) -> dict:
    """Compare a sidecars-on run against its off-twin: byte-level first
    divergence (informational) + per-metric deltas vs the replay-noise
    floor and the latency-control deltas (the timing channel)."""
    div = None
    for i, (x, y) in enumerate(zip(off["fingerprint"], on["fingerprint"])):
        if x != y:
            div = i
            break
    m_off, m_on = host_metrics(off), host_metrics(on)
    deltas = {k: abs(m_off[k] - m_on[k]) for k in m_off}
    quant = {k: (1.0 if k in COUNT_METRICS else 0.0) for k in m_off}
    beyond_noise = {k: d for k, d in deltas.items()
                    if d > NOISE_FACTOR * spread[k] + quant[k] + 1e-12}
    confounded = {k: round(d, 6) for k, d in beyond_noise.items()
                  if d > (NOISE_FACTOR * (spread[k] + latency_delta[k])
                          + quant[k] + 1e-12)}
    verdict = ("clean" if not beyond_noise
               else "timing-explained" if not confounded
               else "CONFOUNDED")
    return {
        "seed": on["seed"], "arm": on["arm"],
        "first_divergence_step": div,
        "verdict": verdict,
        "beyond_noise": {k: round(d, 6) for k, d in beyond_noise.items()},
        "confounded": confounded,
        "deltas": {k: round(d, 6) for k, d in deltas.items() if d > 0},
    }


def main(argv) -> int:
    n_steps, seeds, n_epochs, json_path = 500, [42, 7, 11], 8, None
    args = list(argv)
    if args and not args[0].startswith("--"):
        n_steps = int(args.pop(0))
    while args:
        flag = args.pop(0)
        if flag == "--seeds":
            seeds = [int(s) for s in args.pop(0).split(",")]
        elif flag == "--epochs":
            n_epochs = int(args.pop(0))
        elif flag == "--json":
            json_path = Path(args.pop(0))

    print("=" * 78)
    print("  DIAGNOSTIC: LAE + PLE sidecar instrumentation — control vs pretrained")
    print(f"  corpus v{corpus_version()} · mapping v1 · frame defs v1 · "
          f"signatures v2 · epochs={n_epochs} · steps={n_steps} · "
          f"seeds={seeds} · eval-mode")
    print("=" * 78)

    # ----- replay-noise controls (per arm — the floors twins are judged
    # against; the arms' wall-clock sensitivities differ by ~50x) -----
    noise_by_arm, spread_by_arm = {}, {}
    for pretrained in (False, True):
        arm = "pretrained" if pretrained else "control"
        noise_by_arm[arm] = [run_cell(seeds[0], pretrained, "off",
                                      n_steps, n_epochs)
                             for _ in range(NOISE_RUNS)]
        spread_by_arm[arm] = replay_spread(noise_by_arm[arm])
        byte_identical = all(
            r["fingerprint"] == noise_by_arm[arm][0]["fingerprint"]
            for r in noise_by_arm[arm][1:])
        print(f'  replay-noise control (s{seeds[0]}, {arm}, off x{NOISE_RUNS}): '
              f'{"byte-identical" if byte_identical else "wall-clock jitter (expected)"}'
              f' — floor: ' + '  '.join(
                  f'{k}={v:.4g}'
                  for k, v in sorted(spread_by_arm[arm].items()) if v > 0))

    # ----- latency control: off-run with sidecar-matched per-step delay --
    probe_on = run_cell(seeds[0], False, "on", n_steps, n_epochs)
    base_run = noise_by_arm["control"][0]
    overhead = max(0.0, probe_on["per_step_s"] - base_run["per_step_s"])
    latency_run = run_cell(seeds[0], False, "off", n_steps, n_epochs,
                           step_sleep=overhead)
    m_base, m_lat = host_metrics(base_run), host_metrics(latency_run)
    latency_delta = {k: abs(m_base[k] - m_lat[k]) for k in m_base}
    print(f'  latency control: sidecar overhead {overhead * 1000:.2f} ms/step; '
          f'off+sleep deltas: ' + '  '.join(
              f'{k}={v:.4g}' for k, v in sorted(latency_delta.items()) if v > 0))

    cells, twins = [], []
    for seed in seeds:
        for pretrained in (False, True):
            arm_name = "pretrained" if pretrained else "control"
            off = (noise_by_arm[arm_name][0] if seed == seeds[0]
                   else run_cell(seed, pretrained, "off", n_steps, n_epochs))
            on = (probe_on if (seed == seeds[0] and not pretrained)
                  else run_cell(seed, pretrained, "on", n_steps, n_epochs))
            fb = run_cell(seed, pretrained, "feedback", n_steps, n_epochs)
            tw = twin_check(off, on, spread_by_arm[arm_name], latency_delta)
            twins.append(tw)
            cells.extend([off, on, fb])
            lae_act = on["lae"]["diagnostics"]["activation"]["activations"]
            trig = on["lae"]["trigger_counts"]
            ple_eco = on["ple"]["ecology"]
            print(f'  s{seed:<3} {on["arm"]:<10} '
                  f'coh={on["host"]["coherence_mean"]:.4f} '
                  f'twin={tw["verdict"]}'
                  f'{" " + str(tw["confounded"]) if tw["confounded"] else ""} '
                  f'lae_act={lae_act:<3} trig={dict(trig)} '
                  f'ple_trig={on["ple"]["triggered_cycles"]}/{n_steps} '
                  f'attr={len(ple_eco["attractors"])} find={ple_eco["findings"]}')
            fbk = fb["feedback"]
            print(f'       feedback   coh={fb["host"]["coherence_mean"]:.4f} '
                  f'id={fb["host"]["identity_stability"]:.4f} '
                  f'steps={fbk["steps"]} decisions={fbk["decisions"]} '
                  f'sisters={fbk["sister_sources"]}')

    # ----- verdicts (pre-declared, v2) -----
    print("-" * 78)
    on_cells = [c for c in cells if c["mode"] == "on"]
    fb_cells = [c for c in cells if c["mode"] == "feedback"]
    bad_twins = [t for t in twins if t["verdict"] == "CONFOUNDED"]
    timing = [t for t in twins if t["verdict"] == "timing-explained"]
    if bad_twins:
        print(f'  non-perturbation: CONFOUNDED — state channel suspected in '
              f'{[(t["seed"], t["arm"], t["confounded"]) for t in bad_twins]}')
    else:
        print(f'  non-perturbation: {len(twins) - len(timing)} clean twin(s), '
              f'{len(timing)} timing-explained (wall-clock channel only — '
              f'no state leak)')

    lae_dormant_unexplained = [
        c for c in on_cells
        if c["lae"]["diagnostics"]["activation"]["activations"] == 0
        and c["lae"]["boundary_adjacent_cycles"] > 0
    ]
    lae_total = sum(c["lae"]["diagnostics"]["activation"]["activations"]
                    for c in on_cells)
    if lae_total == 0 and lae_dormant_unexplained:
        print("  LAE: FAILURE — never activates despite boundary-adjacent "
              "energies (mapping v1 miscalibrated)")
    else:
        dormant = [c for c in on_cells
                   if c["lae"]["diagnostics"]["activation"]["activations"] == 0]
        print(f'  LAE: {lae_total} activations across {len(on_cells)} cells'
              + (f' — {len(dormant)} dormant cell(s), all deep-in-band '
                 f'(explicable)' if dormant else ""))
    no_transition = [c for c in on_cells if c["host"]["rhythm_transitions"] == 0]
    if no_transition:
        print(f'  CONFOUNDED(scope): rhythm never transitions in '
              f'{[(c["seed"], c["arm"]) for c in no_transition]} — oscillation '
              f'trigger unreachable there')

    ple_dead = [c for c in on_cells if c["ple"]["triggered_cycles"] == 0]
    ple_no_attr = [c for c in on_cells
                   if not c["ple"]["ecology"]["attractors"]]
    if len(ple_dead) == len(on_cells):
        print("  PLE: FAILURE — zero contradictions anywhere "
              "(discretization v1 too coarse)")
    else:
        print(f'  PLE: contradictions in {len(on_cells) - len(ple_dead)}/'
              f'{len(on_cells)} cells; attractors in '
              f'{len(on_cells) - len(ple_no_attr)}/{len(on_cells)} cells')

    # ----- feedback verdicts (Phase 2, pre-declared) -----
    fb_silent = [c for c in fb_cells if c["feedback"]["steps"] == 0]
    fb_allowed = [c for c in fb_cells
                  if any(d in c["feedback"]["decisions"]
                         for d in ("allow", "allow_weakened", "monitor"))]
    fb_rails = [c for c in fb_cells
                if c["host"]["identity_stability"] < 0.95]
    if fb_rails:
        print(f'  FEEDBACK: IDENTITY RAIL breached in '
              f'{[(c["seed"], c["arm"]) for c in fb_rails]} — record and stop')
    elif fb_silent and len(fb_silent) == len(fb_cells):
        print('  FEEDBACK: no sister offers reached the gate in any cell '
              '(no findings/activations under this workload)')
    elif not fb_allowed:
        print('  FEEDBACK: the gate rejected every sister input — the '
              'immune system treats the family as hostile (recordable)')
    else:
        print(f'  FEEDBACK: sister inputs gated through in '
              f'{len(fb_allowed)}/{len(fb_cells)} cells; identity rail held '
              f'in all (min id={min(c["host"]["identity_stability"] for c in fb_cells):.4f})')

    # ----- differential structure: observe-only vs feedback -----
    print("-" * 78)
    print("  feedback differential (mean across seeds+arms, observe -> feedback):")
    for metric in ("coherence_mean", "identity_stability",
                   "rhythm_transitions", "crystals", "attractors"):
        on_v = [c["host"][metric] for c in on_cells]
        fb_v = [c["host"][metric] for c in fb_cells]
        print(f'    host_{metric:<22} {np.mean(on_v):>10.4f} (sd {np.std(on_v):.4f}) '
              f'-> {np.mean(fb_v):>10.4f} (sd {np.std(fb_v):.4f})')

    # ----- differential structure: control vs pretrained -----
    print("-" * 78)
    print("  differential (sidecars-on, mean across seeds, control -> pretrained):")
    for metric, getter in [
        ("lae_activations", lambda c: c["lae"]["diagnostics"]["activation"]["activations"]),
        ("lae_boundary_adjacent", lambda c: c["lae"]["boundary_adjacent_cycles"]),
        ("ple_triggered_cycles", lambda c: c["ple"]["triggered_cycles"]),
        ("ple_active_paradoxes", lambda c: c["ple"]["ecology"]["active_paradoxes"]),
        ("ple_global_tension", lambda c: c["ple"]["ecology"]["global_tension"]),
        ("ple_findings", lambda c: c["ple"]["ecology"]["findings"]),
        ("host_rhythm_transitions", lambda c: c["host"]["rhythm_transitions"]),
        ("host_coherence_mean", lambda c: c["host"]["coherence_mean"]),
    ]:
        ctl = [getter(c) for c in on_cells if c["arm"] == "control"]
        pre = [getter(c) for c in on_cells if c["arm"] == "pretrained"]
        print(f'    {metric:<26} {np.mean(ctl):>10.3f} (sd {np.std(ctl):.3f}) '
              f'-> {np.mean(pre):>10.3f} (sd {np.std(pre):.3f})')
    for claim in ("coherence_band", "trajectory_sign", "posture", "threat_level"):
        ctl = [c["ple"]["contradictions_by_claim"].get(claim, 0)
               for c in on_cells if c["arm"] == "control"]
        pre = [c["ple"]["contradictions_by_claim"].get(claim, 0)
               for c in on_cells if c["arm"] == "pretrained"]
        print(f'    ple_claim[{claim}]{" " * max(0, 11 - len(claim))} '
              f'{np.mean(ctl):>10.3f} (sd {np.std(ctl):.3f}) '
              f'-> {np.mean(pre):>10.3f} (sd {np.std(pre):.3f})')

    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        dump_cells = [{k: v for k, v in c.items() if k != "fingerprint"}
                      for c in cells]
        json_path.write_text(json.dumps({
            "corpus_version": corpus_version(), "mapping": "v1",
            "frame_defs": "v1", "signatures": "v2",
            "n_steps": n_steps, "n_epochs": n_epochs, "seeds": seeds,
            "replay_noise": {"runs_per_arm": NOISE_RUNS,
                             "factor": NOISE_FACTOR,
                             "spread_by_arm": spread_by_arm},
            "latency_control": {"overhead_s_per_step": overhead,
                                "deltas": latency_delta},
            "twins": twins,
            "cells": dump_cells}, indent=1))
        print(f"  raw results written: {json_path}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
