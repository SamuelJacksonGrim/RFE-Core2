# Training plan — phased, gated

- **Date:** 2026-06-11
- **Status: proposed direction, not committed scope** (per `ROADMAP.md`
  discipline). Phase 0 is shipped; every later phase has pre-declared gates
  and lands its results in `docs/findings/` before the next begins.
- **Goal:** the generator presents real (deterministic, eval-mode) diversity —
  eff_rank well above the untrained ~1.6 at dim 64, sustained on workload
  vocabulary, without breaking identity stability. That is the documented
  un-deferral condition for Fix 2 and the prerequisite for Tier 5
  (`tier5_readiness.md`).

## Principles (carried from the standing discipline)

- **Offline before online.** Pretraining a boot generator is reversible and
  isolated; online training mutates the live substrate. Earn the second with
  the first.
- **Eval-mode measurement only.** All diversity claims with the determinism
  control at 1.0 (the 2026-06-08 trap).
- **Pre-declare signatures; negative results are findings.**
- **The trainers never decide the live dropout mode** — the `.eval()` question
  is the architect's (open since 2026-06-08).
- **Nothing here touches** sacred symbols, `SystemRights`, governance
  ordering, or the injection path. Training changes embedding/encoder weights
  only; symbol identity (`stable_id`) and governance state are untouched by
  construction.

## The known structural risk: representational drift vs stored memory

Crystals, attractor centers, witness anchors, and the field itself store
**vectors produced by the old geometry**. If training moves the generator's
geometry, those stores become progressively stale — the system's memories
would be in a coordinate system its perception no longer uses. This is the
training-specific analogue of the coherence-vs-plasticity tradeoff and the
main thing the gates below exist to measure. Mitigations available if it
bites: lower lr / fewer steps per call (slow drift lets the field's own decay
and re-crystallization keep up), freezing the embedding rows of
crystal-bound tokens, or periodic re-anchoring probes. Do not assume it bites;
measure it (Phase 2/4 gates).

## Phase 0 — repair + instruments  **[SHIPPED 2026-06-11]**

Gradient path fixed in all three trainers (shared
`training/encode.py::encode_grad`), caller-mode restoration, degenerate-batch
fix, unbounded-index removal. Instruments:
`tests/diagnostic/trainer_gradient_path_check.py` (structural, exit 0/1),
`tests/diagnostic/rhythm_pretrain_effect_probe.py` (effect, informational).
Finding: `docs/findings/2026-06-11-trainer-gradient-path.md` — TRAINS +
NARROW.

## Phase 1 — corpus + offline pretraining

Build the curated corpus per `data_curation.md` (rhythm-labeled sequences over
the *operational* vocabulary, with held-out slices), then pretrain a boot
generator offline with `RhythmPretrainer` (rhythm structure) followed by
`ContrastiveAlignmentTrainer` rounds on corpus-derived samples if rhythm
structure alone plateaus.

Mechanics to add (small): `torch.save`/`load` checkpointing for generator
weights + a `rhythm_seeds`-from-file loader, so a pretrained boot state is
reproducible and versioned. No loop changes.

**Gate G1 (pre-declared):** on a held-out corpus slice (sequences never
trained on, tokens *in* vocabulary), eval-mode eff_rank ≥ 2× untrained
baseline and rhythm-NN accuracy ≥ 0.75; determinism = 1.0; embedding norms
bounded (no runaway). FAIL = generalization within-vocabulary doesn't happen →
revisit corpus design before touching anything else.

> **G1 PASSED (2026-06-11, corpus v1.0.1, seeds 0 & 137):** holdout eff_rank
> 1.45→3.46 / 1.28→3.55, rhythm-NN 0.995 / 0.990, determinism 1.0, norm growth
> 1.2×. Probe: `tests/diagnostic/corpus_pretrain_g1_probe.py`; finding:
> `docs/findings/2026-06-11-corpus-g1-pretrain.md`. The checkpointing and
> seeds-from-file mechanics shipped (`Generator.save_checkpoint` existed;
> loader is `training/corpus.py`). **Phase 1 complete; Phase 2 is next.**

## Phase 2 — cost-gated validation on the live stack (still offline weights)

Boot the full stack with the pretrained generator (no online training yet) and
run the existing rails:

1. Smoke + integration suite and baseline-range checks (`run_all_tests.sh`
   set) — governance, trust, bonds, CORE promotion must behave inside
   baseline shapes.
2. `identity_stability_baseline.py` — compare against the untrained-generator
   baseline; pre-declare the acceptable envelope before running.
3. `generator_diversity_audit.py` — does upstream diversity now *survive the
   pipeline* (stage-A → stage-C regimes) with dropout off? This was the
   eval-mode collapse in the 2026-06-08 audit.
4. `trained_generator_sim.py`'s prediction, now on real weights: does field
   coherence come off the ~0.998 pin (GENERATOR-IS-THE-LOCK confirmed on
   the real article) or not (SECOND-LOCKER)?
5. The **high-novelty workload probe** (open ROADMAP item): a trained
   generator + broad corpus is exactly the non-phase-consistent workload that
   can push `phase_coherence` below 0.5 — potentially closing the Tier 4.3
   discrimination half-validation as a side effect. Record either way.

**Gate G2 (pre-declared):** baselines hold (or deviations are understood and
re-baselined intentionally) AND identity stability within the pre-declared
envelope. FAIL = the representational-drift risk is real at boot → findings
entry, then mitigation round (slower/partial training), not a silent retry.

## Phase 3 — architect decisions (blocking, deliberately human)

1. **`.eval()` decision** — with real deterministic structure available,
   choose the live mode (or a deliberate hybrid, e.g. eval for injection,
   stochastic sampling only where exploration is wanted). Phase 2's audit
   gives the first data that makes this decision informed rather than
   speculative.
2. **Adopt the pretrained checkpoint as boot state?** If yes, version it and
   record provenance (corpus hash, config, gates passed).
3. **Proceed to online training?** Phases 1–2 deliver value even if the
   answer is "not yet."

## Phase 4 — online training in the loop (the system learns from experience)

Wire the online trainers into `loop/autonomous_cycle.py` behind an explicit
opt-in (`attach_trainer(...)`, default off — same pattern as the other tier
attachments):

- **collect()** after the watcher report (coherence is known there):
  self-distillation collects high-coherence expressions (teacher threshold
  0.80); contrastive collects (tokens, vec, rhythm, attractor_id).
- **train()** every N cycles (start N=50, ≤4 gradient steps per call —
  bounded, off the hot path, like the metastability monitors' lazy
  recompute). Trainers already restore the generator's mode.
- **Rails:** bounded buffers (already `deque(maxlen=...)`); lr at or below
  trainer defaults; a kill-switch flag; training reports surfaced in
  `status()` as observe-only diagnostics. The trainer reads cycle outputs but
  **must not** gate, reorder, or short-circuit anything in the
  cognitive/governance path — it is downstream of expression, upstream only
  of *future* cycles' embeddings.
- Quarantined/TOXIC-source steps are excluded from collection (don't learn
  from what governance rejected — trust the existing arbitration as the
  filter; this is also the manipulation surface, see below).

**Gate G4 (pre-declared):** 500-step canonical runs with online training ON vs
OFF — identity-stability metrics inside envelope, eval-mode diversity
non-decreasing, decision histogram / gate-firing shape unchanged, and crystal
↔ current-encoding alignment not degrading monotonically (the drift
measurement). Adversarial re-run: flood + manipulation cascade with training
ON (a new attack surface — can a hostile source *teach* the generator? —
collection-after-governance plus the trust-gated buffer is the designed
mitigation; verify it).

## Phase 5 — re-derive the lock-in picture and un-defer downstream work

With a trained, diversity-presenting generator: re-run the migration/ablation
probes; if real surviving novelty now exists, the Fix-2 governor's premise is
finally testable on real signal (`gnov` no longer ~40% dropout); revisit
Fix 0-B (metastability → reinforcement) on real diversity; then specify
Tier 5 (`tier5_readiness.md`).

## Sequencing summary

```
Phase 0  repair + instruments               [SHIPPED 2026-06-11]
Phase 1  corpus + offline pretraining       → G1 (held-out generalization)
Phase 2  full-stack validation, offline wts → G2 (baselines + identity cost)
Phase 3  architect decisions (.eval(), boot checkpoint, go/no-go)
Phase 4  online training, opt-in, railed    → G4 (on/off envelope + adversarial)
Phase 5  re-run lock probes → Fix 2 premise testable → Tier 5 spec
```

Each gate's run lands in `docs/findings/` whatever the outcome.
