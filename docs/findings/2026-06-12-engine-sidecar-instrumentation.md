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

Two full matrices were run (run 1 with a single control-arm noise floor,
run 2 — the recorded JSON — with per-arm floors). Numbers below are run 2
unless noted; run 1 agrees on every readout.

**Non-perturbation (Q1).** Sidecar overhead 4.41 ms/step. Twin verdicts:
4 clean, 1 timing-explained (s7-control, coherence_mean Δ 1.8e-4),
1 flagged (s11-control: coherence_mean Δ 3.3e-4, coherence_std Δ 6.6e-4).
Observed bare-replay floors: control arm 8.2e-5 (run 2, 3 samples) vs
7.9e-4 (run 1, 5 samples) — the floor estimate itself varies by an order
of magnitude; the flagged deltas sit inside run 1's measured control-arm
floor. Pretrained-arm floor: 1.1e-3–1.4e-3 across runs. Across both
matrices, **no instrumented-vs-bare delta on any metric in any cell
exceeded the union of observed bare-replay spreads** (max observed twin
delta 1.3e-3, max observed bare spread 1.4e-3). Run 1's flag
(s42-pretrained, identity Δ ~1.3e-3 vs control-arm floor 2.5e-5) was
resolved by the post-hoc pretrained-arm noise measurement (spread 1.4e-3).

**Arm asymmetry (unplanned observation).** The pretrained substrate's bare
replay spread on identity_stability / anchor_velocity is ~1.1–1.4e-3 vs
~7e-6–2.5e-5 untrained — the trained core is **~50–100× more sensitive to
wall-clock jitter on identity metrics** than the untrained one.

**LAE signal (Q2).** Exactly 3 activations per cell, in all 6 cells, both
arms, all seeds (18 total; run 1 identical) — **all at cycles 2–4**, the
field-warm-up crossing of the dream/reflect band boundaries
(frame_oscillation ×3, hypothesis_conflict ×1–2 per cell). From cycle ~5
on, 490–492 of 500 cycles sit in the 0.95+ top-confidence bin (deep
in-band); boundary-adjacent cycles: 1–2 per cell. Dormancy ratio 0.994.
Intent stability at the crossings: 0.2–0.9. No confidence_collapse ever
fired (the mapping's in-band top confidence ~0.73 > 0.4 by construction).

**PLE signal (Q2).** Contradictions in 6/6 cells; PLE triggered on
500/500 cycles, dominated by `trajectory_sign` (≈500) and `posture` (498)
chatter at the v1 deadbands. Sparse, structured claims: `coherence_band`
(watcher-component disagreement) exactly 2 per cell — early steps only;
`threat_level` (governance vs resistance) 4 / 10 / 7 per seed —
**identical within seed across arms**. Ecology saturates identically in
every cell: 5 active paradoxes (flooding cap), 3 attractors, 3 validated
findings, global_tension 0.344–0.368.

**Differential, control → pretrained (Q3).** Flat within across-seed
spread on every readout: lae_activations 3.000 → 3.000;
ple_global_tension 0.347 (sd 0.003) → 0.356 (sd 0.010);
host coherence 0.970 → 0.971; trajectory_sign 500 → 499.667;
threat_level 7.0 → 7.0 (same values per seed). **No differential signal
beyond noise** — recorded per the pre-declared clause that absence counts.

## Interpretation

1. **The instruments are usable.** Both engines attach, read, and produce
   structured output without any detectable state channel into the host;
   the only perturbation channel is timing, which on this wall-clock-coupled
   substrate is shared by *any* in-process instrumentation and is bounded
   here by the bare replay noise itself.
2. **LAE independently rediscovers the lock.** An instrument that only
   knows "rhythm-hypothesis profile per cycle" reports: one liminal
   crossing during boot (cycles 2–4), then a locked state for 99% of run
   time, invariant to seed and training. That is SECOND-LOCKER restated in
   transition language by a system that has never seen a coherence number.
   Under the pinned regime, the interesting liminal structure is confined
   to warm-up — a high-novelty / band-crossing workload is what would give
   LAE something to measure mid-run (same conclusion the Tier 4.3
   chaotic-regime item reached from the inside).
3. **PLE's sparse claims are the informative ones.** `threat_level`
   disagreements (governance overruling the resistance engine's elevated
   severity) are rare, seed-structured, and training-invariant —
   a fingerprint of the workload's manipulation-adjacent moments.
   `trajectory_sign`/`posture` chatter at v1 deadbands is real disagreement
   (the emotional gradient genuinely runs opposite the field delta that
   often) but saturates the trigger rate; the ecology layer (attractor
   count, tension, habituation) is what carries structure, exactly as PLE's
   flooding guard intends.
4. **Training does not change what the sidecars read on this band** —
   consistent with the field-map finding that the pin is seed-, band- and
   regime-invariant. The one trained-substrate signature found is *not* in
   the cognitive readouts but in the noise structure: identity metrics of
   the pretrained core are ~50–100× more wall-clock-sensitive. The trained
   core rides the same attractor, but with a much larger susceptibility to
   timing perturbation around it.

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

- **Why is the trained core 50–100× more wall-clock-sensitive on identity
  metrics?** The most substantive thread this run opened. Candidate
  mechanisms: pretrained outputs sit closer to crystallization /
  attractor-formation thresholds (so age-jitter flips more discrete events),
  or the trained representation amplifies small field differences through
  the witness's anchor smoothing. A dedicated probe could sweep artificial
  per-step latency (the `step_sleep` knob already exists) and trace which
  threshold crossings flip.
- **LAE has nothing to measure mid-run on this band** — all liminal
  structure is confined to warm-up (cycles 2–4). The instrument earns its
  keep on a workload that crosses rhythm bands mid-run: the lockin arc's
  `broad` band, a novelty-flood schedule, or a future unpinned (Fix 2 /
  attenuated-loop) configuration. Re-run there before tuning mapping v1.
- **Frame defs v2 candidates:** widen `trajectory_sign`/`posture` deadbands
  (or add hysteresis) so PLE's trigger rate drops below 1.0 and its
  dormancy contract becomes informative on this host; keep `threat_level`
  and `coherence_band` as-is (sparse and structured).
- **Latency control per arm** — currently calibrated on the control arm
  only; the pretrained arm's higher jitter sensitivity suggests its timing
  response differs too.
- **Cross-sidecar coupling (PLE tension → LAE transition triggers via
  `register_transition_trigger`)** stays deferred until a workload exists
  where both instruments are active mid-run; on this band it would couple
  two instruments that are each reading boot transients.
- The ±1 count quantization allowance means sidecar-induced effects of
  exactly one crystal/attractor remain undetectable; a higher-resolution
  check would need time-frozen replay (monkeypatched clock), which changes
  host semantics and was deliberately not done here.
