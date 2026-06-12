# Phase 3 — Architect Decisions (Blocking)

**Status:** Phase 2 complete; Phase 3 is an explicit architect-only decision gate blocking Phase 4–5.

**Date:** 2026-06-12

**Context:** Phase 2 (corpus v1.1.0 extension + Gate G2 live-stack validation) confirmed the SECOND-LOCKER finding: with a trained generator on real operational vocabulary, the coherence lock persists but barely moves (0.9767 → 0.9701). The reflective loop is the operative lock, not generator low-rank. This finding **re-prioritizes Fix 2** (its premise is finally testable on real signal — the 2026-06-09 "wait until trained" condition is now satisfied) and confirms boot-time training is identity-safe and effective at the representation level — while showing that **training alone does not release the lock**.

Phase 3 is **three explicit decisions** that only the architect can make, informed by the evidence Phase 2 delivered.

---

## Decision 1: Generator Train/Eval Mode in Live Deployment

**What:** Should the live system run the generator in `train()` mode (stochastic, dropout) or `eval()` mode (deterministic)?

**Evidence:**

- **Dropout breaks measurement determinism and inflates novelty readings.** The 2026-06-08 trap: train-mode nondeterminism once mimicked a feedback effect (Δ ≈ 0.63) that vanished under the eval control (Δ = 0.0). The 2026-06-09 probe: benign `gnov` inflates ~0.39 under dropout, polluting any trigger calibrated in eval mode.
- **Phase 2 Gate G2 Run C (pretrained/eval):** All baselines held, identity_stability 0.9986, no representational drift, and a *second* bond formed. The eval-mode boot is live-viable. (Honest counterpoint: Tier 4.3 `phase_coherence` read slightly *higher* in train mode — 0.971 vs 0.948 — so there is no measured Tier 4.3 cost to either mode on the canonical workload.)
- **Prior decision:** all three trainers (`training/rhythm_pretraining.py` and peers) restore the caller's train/eval state on exit. Trainers no longer decide this unilaterally; the live mode is the architect's call (open since 2026-06-08).
- **Trade-off:**
  - `eval()` → Deterministic, clean Tier 4.3 coupling, reproducible behavior, fixed embeddings post-training.
  - `train()` → Stochastic exploration, dropout regularization, potential for online micro-updates (Phase 4), but less stable Tier 4.3 signal and less reproducible behavior.

**Recommendation:** `eval()` is the safer choice post-training. Determinism is a feature for a cognitive substrate; dropout is an optimization for learning. Once trained, the stochasticity has diminishing returns and costs Tier 4.3 stability. If online learning (Phase 4) is needed, it can run in a separate train session and checkpoint back to eval for deployment.

**Action if approved:**
```python
# In loop/recursion1188.py or entry point
generator.eval()  # Set once at startup, maintained by trainers
```

---

## Decision 2: Boot-Checkpoint Adoption

**What:** Should the live system boot from a pretrained checkpoint, or continue booting from a fresh random init?

**Options:**

### Option A: Fresh Random Init (Status Quo)
- Every deployment starts from untrained weights
- Generator re-learns the operational vocabulary every session
- Longer burn-in to effective behavior
- No corpus/training coupling in prod

### Option B: Pretrained Checkpoint (Gate G1+G2 Recipe)
- Boot from the checkpoint the G1 probe writes with `--save`:
  `python3 -m tests.diagnostic.corpus_pretrain_g1_probe 8 --seed 0 --save`
  → `data/checkpoints/boot_rhythm_corpus_v1.1.0_8ep_s0.pt` (+ `.ecology.json`)
- Recipe: corpus v1.1.0, 8 epochs, seed 0 or 42, `RhythmPretrainer`
- Note: `data/checkpoints/` is `.gitignore`d — adoption requires a provenance
  decision: either commit the artifact, or treat the committed corpus + build
  script + probe recipe as the canonical (re-derivable) source and record the
  recipe in the MANIFEST/ROADMAP
- Gate G1 (held-out) PASSED: eff_rank 1.45→3.41, rhythm-NN 0.995, determinism 1.0
- Gate G2 (live-stack) PASSED on RUN B, the gated run: all baselines held, identity_stability 0.9974 (eval RUN C: 0.9986), no drift
- Immediate operational vocabulary coverage vs learning from scratch
- Ties training and deployment (corpus version, checkpoint version)

**Evidence:**

- **Phase 1 (June 11):** Trainer gradient path fixed; effect probe showed training works, narrow to trained vocabulary only (disjoint tokens unmoved).
- **Phase 2 corpus build:** Operational vocabulary extended from 50 to 113 tokens; v1.1.0 covers the full live workload.
- **Phase 2 Gate G1:** Held-out generalization validated on untrained disjoint set (unmoved tokens stay low-rank, trained tokens gain real structure).
- **Phase 2 Gate G2:** Boot sequence on full live stack with pretrained weights. All baselines held, identity formation succeeded, no drift or stability loss.
- **SECOND-LOCKER:** Even with trained input, coherence barely moves (0.9767 → 0.9701) — the loop is the operative lock, not generator capacity. Training is orthogonal to the lock but still valuable for vocabulary coverage.

**Trade-off:**
- Option A: Simple, stateless, no corpus/training coupling. But slow warm-up and incomplete vocabulary coverage until learning fills it.
- Option B: Fast operational coverage, proven safe through gate validation, corpus versioning required. But adds training artifact (checkpoint file, corpus version coupling).

**Recommendation:** **Option B (pretrained checkpoint).** The gates passed; the vocabulary coverage is complete; the safety evidence is strong. The corpus versioning and checkpoint management are minor costs for guaranteed live-vocabulary coverage. The no-drift constraint is real — Phase 4 (online training) will write new sequences to the corpus, and the boot checkpoint must remain reproducible for debugging/audit.

**Action if approved:**
1. Checkpoint save/load already exists (`agents/generator.py::save_checkpoint`; the G1 probe's `--save` flag uses it). Run the probe with `--save` (seed 0 or 42) to produce the boot artifact.
2. In `loop/recursion1188.py` CONFIG (the runtime source of truth for entry-point parameters): add a boot-checkpoint path flag, default off; load it at stack construction when set.
3. Resolve the provenance question (commit the `.pt`, or document the deterministic re-derivation recipe — corpus version + epochs + seed — in the MANIFEST).
4. Document checkpoint adoption in ROADMAP current-understanding.

---

## Decision 3: Fix 2 Specification and Timing

**What:** How should Fix 2 (the reflective-loop governor) be specified and prioritized?

**Context:**

The lock-in plan (§3.2, June 7 plasticity arc) identified the **reflective loop's convergence gain** as the operative lock. Two implementation paths were proposed:

1. **Field-side Fix 2 (original plan):** Reduce attractor depth or field-blend weights in the reflective loop to lighten its pull.
2. **Loop-attenuation (loop-governor):** Conditionally suppress or modulate the loop's gain when real novelty is detected (ReflectiveLoopGovernor).

**Evidence:**

- **June 8, 09 Fix 2 live-generator probes:** (`2026-06-09-fix2-live-generator.md`) The standard novelty trigger (`gnov > 0.65`) is **permanently dormant** on real regimes because the untrained generator has a dominant common-mode direction — regime means stay collinear (~0.85–0.96 cosine) regardless of dimension (tested 64/256/512).
  - Common-mode-removed trigger (per-regime projection) engages Fix 2 at 98% loosening but recovers only **+0.024 migration** (untrained generator baseline). With dropout the manip cost is ~1% at gain 0.5, **0% at gain 0.6**.
  - The mock orthogonal-B used in governor validation (+0.166 migration) **overstated the real-token value by 7×**. On real regimes, Fix 2 is a small-signal intervention.
  
- **SECOND-LOCKER finding (Phase 2, 2026-06-12):** With a trained generator (eff_rank 3.41, proper structure), the coherence barely moves (0.9767 → 0.9701). The loop is the operative lock.

- **What G2 did *not* measure:** whether training actually reduced the generator's common-mode / separated regime means in high-energy directions. The June 9 conclusion — *"train it so regimes differ in high-energy directions, not just a small perp component"* — set the condition; whether the v1.1.0 boot checkpoint meets it is **unmeasured**. Re-running the June 9 regime-separation probe on the trained checkpoint is the first Phase 5 item and the load-bearing input to this decision.

- **§6.3 gain-sign check (lock-in plan) is a pending hard gate.** The plan states it "gates Fix 0-A and Fix 2" (any coherence→loop coupling). The instrument exists (`tests/diagnostic/gain_sign_check.py`); a recorded verdict does not. No production wiring of the governor before that verdict lands in `docs/findings/`.

**Three implementation options:**

### Option A: Defer Fix 2 (Measure First)
- **Rationale:** The untrained generator's common-mode made Fix 2's standard trigger dormant. Training *may* have improved regime separation — that is unmeasured. Note SECOND-LOCKER cuts the other way on the lock itself: the pin did **not** loosen with training, so deferral is justified only to get the Phase 5 separation re-measurement, not because training relieves the lock.
- **Timing:** Validate whether the trained generator separates regimes in high-energy directions (re-run the June 9 probe with pretrained checkpoint). If separation improved, Fix 2 becomes more targeted and valuable.
- **Risk:** If training didn't improve regime separation (common-mode persists), deferral leaves the lock operative longer than necessary.

### Option B: Add Loop-Governor as Defensive Layer (No Defer)
- **Rationale:** Build the ReflectiveLoopGovernor anyway (skeleton exists in test harness; needs production integration). Even if it recovers only +0.024 migration on untrained gens, it's a defensive layer that can't hurt (0% manip at gain 0.6).
- **Requirements:**
  1. Run and record the §6.3 gain-sign check first (hard gate, verdict pending).
  2. Implement `cognition/reflective_loop_governor.py` (common-mode-aware trigger, gain scheduling).
  3. Wire into `AutonomousCycle.step()` (e.g., post-generation novelty observation, pre-reflection gain blend).
  4. Gate on ≥2 sources (prevent single-source attack from opening the loop).
  5. Set operating point to gain ≥ 0.6 (0% manip at that threshold).
- **Timeline:** Can run in parallel with Phase 1 pretraining; doesn't block it.
- **Trade-off:** Small real-world effect (dormant until trained + even when engaged, +0.024 is marginal) vs. defensive completeness.

### Option C: Design but Defer Implementation
- **Rationale:** Sketch the spec (trigger with common-mode removal, gain curve, integration points), validate re-run the June 9 probe with trained generator to measure actual effect. If the trained generator separates regimes, Fix 2 becomes valuable and you have the spec ready.
- **Timeline:** Decision/spec in Phase 3; implementation in Phase 5 (post-Phase 4 online training) if evidence justifies it.
- **Trade-off:** Keeps the door open with minimal Phase 3 commitment; defers commitment until the trained data is in hand.

**Recommendation:** **Option C (design + defer implementation, re-validate post-training).**

Rationale:
1. The June 9 probe was run on an untrained generator. Phase 1 training *may* have improved regime separation — re-measure before paying integration cost.
2. SECOND-LOCKER shows training alone does *not* release the lock — which is exactly why a loop-side intervention is back on the table, and why its real effect size must be measured on trained weights first (on untrained weights it recovered only +0.024 migration).
3. The §6.3 gain-sign verdict is pending and gates any production wiring regardless of this decision.
4. The spec can be ready in parallel (common-mode trigger, gain 0.6 operating point, integration sketch).

**Action if approved:**
1. Spec draft exists: `docs/training/fix2_specification_draft.md` (trigger spec with common-mode removal, gain schedule, integration points in `AutonomousCycle.step()`).
2. Run and record the §6.3 gain-sign verdict (`tests/diagnostic/gain_sign_check.py` → `docs/findings/`).
3. In Phase 5, re-run the June 9 probes with the trained checkpoint (regime separation measurement, Fix 2 effectiveness on trained gen).
4. Make final implementation decision post-Phase 5 probes based on actual trained-generator data.

---

## Summary Table: Decisions and Blockers

| Decision | Option | Status | Blocker For |
|----------|--------|--------|-------------|
| 1. Train/Eval mode | eval() | **Choose** | Phase 4 online training, Tier 4.3 stability |
| 2. Boot checkpoint | Pretrained (Option B) | **Choose** | Phase 4 (live corpus updates), deployment startup |
| 3. Fix 2 spec | Design + defer (Option C) | **Choose** | Phase 5 ablation/re-validation, Tier 5 spec |

---

## Phase 4 Depends On

Once Phase 3 is decided:

- **Phase 4 (Online Training):** Boot-checkpoint adoption (Decision 2) enables persisting live sequences to the corpus during operation. Current outline: trust-gated buffer, source-diversity caps, snapshot persistence for auditability (data_curation.md §4).
- **Phase 5 (Ablation + Tier 5 Spec):** Re-run migration/adversarial probes with pretrained boot to validate the trained-gen Fix 2 effectiveness (Decision 3 re-validation). Formally specify Tier 5 meta-cognition tier (reflective-loop governance, possibly via trained common-mode separation or explicit governor).

---

## Appendix: Evidence Locations

- **Phase 1 training viability:** `docs/training/viability_assessment.md`, `docs/findings/2026-06-11-trainer-gradient-path.md`
- **Phase 2 corpus validation:** `docs/training/data_curation.md`, `docs/findings/2026-06-12-phase2-fullstack-g2.md`
- **SECOND-LOCKER (coherence pin on trained gen):** `docs/findings/2026-06-12-phase2-fullstack-g2.md`, "SECOND-LOCKER finding" section
- **Fix 2 deferral and common-mode evidence:** `docs/findings/2026-06-09-fix2-live-generator.md`
- **Lock-in plan (Fix 2 options and June 7 plasticity arc):** `docs/lock_in_remediation_plan.md`, §3.2
