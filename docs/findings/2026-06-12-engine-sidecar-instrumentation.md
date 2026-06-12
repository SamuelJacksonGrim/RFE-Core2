# Sidecar instrumentation — can LAE and PLE measure the running core without perturbing it, and does training change what they read?

- **Date:** 2026-06-12
- **Substrate:** live full stack, **eval mode** (Phase 3 Decision 1), corpus
  v1.1.0 8-epoch boots (per-seed checkpoints, shared with the field-map
  cache), 500 steps per cell, canonical Resonance-Family band only.
- **Probe:** `tests/diagnostic/sidecar/engine_sidecar_probe.py` — seeds
  (42, 7, 11) × {control-untrained, pretrained} × {sidecars off, on}, plus
  per-arm replay-noise controls (3 off-runs each) and a latency control.
  Sidecar adapters:
  `tests/diagnostic/sidecar/sidecar_harness.py` (mapping **v1**) feeding the
  Liminal Anchor Engine (`lae`, sibling repo) and the Paradox Lattice Engine
  via `ple.integration.rfecore2hook` (frame defs **v1**, implemented in the
  PLE repo for this arc). Raw: `logs/2026-06-12-engine-sidecar-baseline.json`.
- **Status:** active
- **Depends on:** 2026-06-12-phase2-fullstack-g2.md (eval-mode operating
  regime + pretrained boot), 2026-06-12-checkpoint-registry-orphan.md
  (checkpoint round-trip validity), 2026-06-12-secondlocker-field-map.md
  (the pin context every cell here sits inside).

## Question

Two external sidecar engines are wired observe-only around the autonomous
cycle: LAE structures *transitions* (rhythm-hypothesis profile per cycle),
PLE structures *contradictions* (discretized evaluator disagreements per
cycle). Three questions, in dependency order:

1. **Non-perturbation** — does attaching the instruments change the host?
2. **Signal** — do the instruments register anything on this substrate
   (LAE activations with interpretable triggers; PLE contradictions,
   attractors, findings)?
3. **Differential** — does generator pretraining change what they read?

## Pre-declared signatures (probe header, v2 — declared before the
## measurement run)

Signatures **v1** required byte-identical sidecars-on/off twins. Bring-up
falsified the premise before the measurement run: same-seed sidecars-OFF
replays diverge numerically from step 1 — the substrate is wall-clock-coupled
by design (crystal/attractor age decay, ethical flood windows, witness/trust
timestamps), so byte-identity is unattainable for ANY in-process re-run, not
just instrumented ones. v2 replaces it with two controls:

- **replay-noise control (per arm)** — 3 identical off-runs per arm;
  per-metric max spread is that arm's noise floor. Per-arm matters: run 1
  used a control-arm floor for both arms and flagged a false state channel
  on (s42, pretrained) — identity_stability/anchor_velocity twin deltas of
  ~1.3e-3 against a control-arm floor of 2.5e-5. A post-hoc 3-run
  pretrained-arm noise measurement showed the pretrained substrate's bare
  replay spread on those metrics is ~1.4e-3 — the flagged delta sits inside
  it. The pretrained substrate is ~50× more wall-clock-sensitive on
  identity metrics than the untrained one (itself an observation).
- **latency control** — one off-run with a per-step sleep matched to the
  sidecars' measured overhead. A wall-clock-coupled host responds to
  instrumentation *latency* even with zero state contact; this control
  separates the timing channel from a state channel. Calibrated on the
  control arm, applied to both (approximation, noted under threats).

Twin verdicts per cell: within 2× noise → **clean**; beyond noise but within
2×(noise + latency-control delta) → **timing-explained** (no state leak);
beyond that → **CONFOUNDED** (state channel suspected). Discrete event
counts (crystals, attractors, rhythm transitions/mix) carry a ±1
quantization allowance — bring-up observed bare off-runs flipping a
borderline crystallization by exactly 1 from timing jitter alone.

- **SUCCESS:** every twin clean or timing-explained; LAE ≥1 activation per
  cell OR explicably dormant (top-confidence histogram deep in-band); PLE
  ≥1 contradiction and ≥1 attractor per cell. Control→pretrained differences
  beyond across-seed spread are the differential finding; their absence is
  also recordable.
- **FAILURE:** LAE never activates anywhere despite boundary-adjacent
  energies (mapping v1 miscalibrated); or PLE detects zero contradictions
  (discretization v1 too coarse).
- **CONFOUNDED:** any twin beyond the timing-explained threshold; or rhythm
  never transitions in a cell (oscillation trigger unreachable — scope the
  LAE verdict).

## Result (observed)

PENDING — filled from the measurement run.

## Interpretation

PENDING.

## Threats / confounds

- Runs: 1 full matrix (this entry), plus 60-step bring-up runs (not
  evidence — statistics over 30-sample halves; used only to debug controls).
- The noise floor is a 5-sample max-spread estimate of a wall-clock-coupled
  process — it underestimates tail jitter; the ±1 count allowance papers over
  exactly that for discrete events, which means count effects of magnitude 1
  are below this probe's resolution.
- Mapping v1's `HYPOTHESES_TAU = 0.4` and the PLE discretization bands
  (frame defs v1) are first-pass constants: LAE trigger rates and PLE
  contradiction rates are functions of these knobs, so cross-arm
  *differences* are meaningful, absolute rates are not.
- PLE's `trajectory_sign` / `posture` claims fire on most cycles under
  frame defs v1 (the emotional gradient and the field-delta trend genuinely
  disagree that often at these deadbands) — the contradiction *ecology*
  (attractors, intensity, habituation) carries the structure, not the raw
  trigger rate.
- One band (canonical) only; band×training interactions belong to the
  lockin arc.
- Sidecar overhead is machine-load-dependent; the latency control was run
  in the same process episode as the cells it calibrates.

## Open / next

PENDING.
