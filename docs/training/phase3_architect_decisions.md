# Phase 3 — Architect Decisions (Blocking)

**Status:** Phase 2 complete; Phase 3 is an explicit architect-only decision gate blocking Phase 4–5.

**Date:** 2026-06-12

**Context:** Phase 2 (corpus v1.1.0 extension + Gate G2 live-stack validation) confirmed the SECOND-LOCKER finding: with a trained generator on real operational vocabulary, the coherence lock persists but barely moves (0.9767 → 0.9701). The reflective loop is the operative lock, not generator low-rank. This finding un-defers **Fix 2** (the loop-governing intervention) and validates **training as the viable path forward**.

Phase 3 is **three explicit decisions** that only the architect can make, informed by the evidence Phase 2 delivered.

---

## Decision 1: Generator Train/Eval Mode in Live Deployment

**What:** Should the live system run the generator in `train()` mode (stochastic, dropout) or `eval()` mode (deterministic)?

**Evidence:**

- **Tier 4.3 phase_coherence depends on consistent field state.** Dropout nondeterminism in the generator adds stochastic jitter to the field, making the FFT-derived rhythm coupling less stable.
- **Phase 2 Gate G2 Run C (pretrained/eval):** All baselines held, identity_stability 0.9986, no representational drift, no formation blockers. The eval-mode boot is live-viable.
- **Prior decision:** Line ~204 in `training/rhythm_pretrainer.py` restores the caller's train/eval state on exit. Trainers no longer decide this unilaterally.
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
- Boot from `checkpoints/phase1_boot_v1.1.0.pt` (training plan §5.1)
- Recipe: corpus v1.1.0, 8 epochs, seed 0 or 42, contrastive-alignment trainer
- Gate G1 (held-out) PASSED: eff_rank 1.45→3.41, rhythm-NN 0.995, determinism 1.0
- Gate G2 (live-stack) PASSED: all baselines held, identity_stability 0.9986, no drift
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
1. Implement checkpoint save/load in `training/rhythm_pretrainer.py` (Phase 1 output; currently trained in-memory).
2. Run `training/train_phase1_boot.py` once with seed 0 (or 42) and save to `data/checkpoints/phase1_boot_v1.1.0.pt`.
3. In `loop/recursion1188.py` or startup: conditionally load the checkpoint if `BOOT_PRETRAINED=True` (config flag).
4. Document checkpoint version in ROADMAP current-understanding and in any deployment guide.

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
  
- **SECOND-LOCKER finding (Phase 2, 2026-06-12):** With a trained generator (eff_rank 3.41, proper structure), the coherence barely moves (0.9767 → 0.9701). The loop is the operative lock **and training addresses it by putting regime differences in high-energy directions** (reducing the common-mode dominance).

- **Conclusion from June 9 probe:** *"The real work is the generator — train (or architecturally constrain) it so regimes differ in high-energy directions, not just a small perp component."*

**Three implementation options:**

### Option A: Defer Fix 2 (Training First)
- **Rationale:** The untrained generator's common-mode makes Fix 2 dormant. Once trained (Phase 1 checkpoint), the regime separation improves and the loop's lock becomes less tight anyway (SECOND-LOCKER evidence).
- **Timing:** Validate that the trained generator separates regimes in high-energy directions (re-run the June 9 probe with pretrained checkpoint). If separation improves, Fix 2 becomes more targeted and valuable.
- **Risk:** If training doesn't improve regime separation (common-mode persists), deferral leaves the lock operative longer than necessary.

### Option B: Add Loop-Governor as Defensive Layer (No Defer)
- **Rationale:** Build the ReflectiveLoopGovernor anyway (skeleton exists in test harness; needs production integration). Even if it recovers only +0.024 migration on untrained gens, it's a defensive layer that can't hurt (0% manip at gain 0.6).
- **Requirements:**
  1. Implement `cognition/reflective_loop_governor.py` (common-mode-aware trigger, gain scheduling).
  2. Wire into `AutonomousCycle.step()` (e.g., post-generation novelty observation, pre-reflection gain blend).
  3. Gate on ≥2 sources (prevent single-source attack from opening the loop).
  4. Set operating point to gain ≥ 0.6 (0% manip at that threshold).
- **Timeline:** Can run in parallel with Phase 1 pretraining; doesn't block it.
- **Trade-off:** Small real-world effect (dormant until trained + even when engaged, +0.024 is marginal) vs. defensive completeness.

### Option C: Design but Defer Implementation
- **Rationale:** Sketch the spec (trigger with common-mode removal, gain curve, integration points), validate re-run the June 9 probe with trained generator to measure actual effect. If the trained generator separates regimes, Fix 2 becomes valuable and you have the spec ready.
- **Timeline:** Decision/spec in Phase 3; implementation in Phase 5 (post-Phase 4 online training) if evidence justifies it.
- **Trade-off:** Keeps the door open with minimal Phase 3 commitment; defers commitment until the trained data is in hand.

**Recommendation:** **Option C (design + defer implementation, re-validate post-training).**

Rationale:
1. The June 9 probe was run on an untrained generator. Phase 1 training should improve regime separation, changing the cost-benefit calculus.
2. SECOND-LOCKER shows that training addresses the lock directly (not just small-signal interventions).
3. Deferring gives you post-Phase 1 data to decide whether Fix 2 is worth the integration cost.
4. The spec can be ready in parallel (common-mode trigger, gain 0.6 operating point, integration sketch).

**Action if approved:**
1. Create `docs/training/fix2_specification_draft.md` with trigger spec (common-mode removal), gain schedule, integration points in `AutonomousCycle.step()`.
2. In Phase 5, re-run the June 9 probes with the trained checkpoint (regime separation measurement, Fix 2 effectiveness on trained gen).
3. Make final implementation decision post-Phase 5 probes based on actual trained-generator data.

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
