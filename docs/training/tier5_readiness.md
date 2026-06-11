# Tier 5 readiness — how training gates meta-cognition

- **Date:** 2026-06-11
- **Status:** Tier 5 remains **unspecified** per `ROADMAP.md` discipline; this
  document does not specify it. It records why the training path is the
  prerequisite, and what is already anchored for whoever specifies Tier 5.

## What Tier 5 is anchored to

The only committed anchor (`ROADMAP.md`, Tiers 5–7): *meta-cognition /
attentional control — the system __directing__ attention rather than
experiencing it; the reflective loop knowing where its own attention is, not
just responding to it.* "Focus" was explicitly deferred to Tier 5 during the
Tier 4.2 design.

The lock-in arc made that anchor concrete: the reflective loop (cycle step 6)
*is* the system's attention — it converges every expression toward the
identity anchor, and that same convergence is the proven lock
(`2026-06-07-reconstruction-ablation.md`: coherence and rigidity are the same
mechanism). A designed control surface already exists: the Fix-2 governor —
conditional attenuation of the loop's convergence gain, gated on surviving
novelty (`gnov` trigger W=10/T≈0.65, gain floor 0.45, rails;
`2026-06-08-fix2-trigger-calibration.md`). That is exactly "the loop knowing
where its attention is (gnov: is something new surviving?) and directing it
(attenuation: loosen the anchor-pull, bounded)."

## Why it is deferred, and what un-defers it

Deferred because the attention it would direct is currently noise: the
deterministic generator is near-collinear (eff_rank ~1.6 at dim 64) and the
live diversity is ~half dropout, so `gnov` itself is ~40% dropout-driven —
loosening the loop would admit noise, not novelty
(`2026-06-08-generator-dropout-diversity.md`, `ROADMAP.md`).

**The un-deferral condition is therefore upstream: real, deterministic
generator diversity.** Training is the documented lever, now proven live
(`2026-06-11-trainer-gradient-path.md`). The prerequisite stack:

```
training Phase 1–2   corpus + offline pretraining; full-stack validation
        │            (also likely closes the Tier 4.3 high-novelty gap —
        │             a trained generator on a broad corpus is the
        │             non-phase-consistent workload that item needs)
        ▼
training Phase 3     architect decisions: .eval(), boot checkpoint
        ▼
training Phase 4     online training — the system learns from experience
        ▼
training Phase 5     re-run migration/ablation probes on real diversity;
        │            gnov re-calibrated on a dropout-free substrate
        ▼
Fix 2 un-deferred    loop-loosening governor on real signal
        ▼
Tier 5 specification meta-cognition / attentional control — specified
                     deliberately (multi-instance collision + epistemic
                     discipline, per ROADMAP), not assumed
```

## What Tier 5 will already have when it gets specified

- **A sensor:** `gnov` (surviving-novelty), calibrated; plus the
  `StreamMetastabilityMonitor`s (stage A/C) as the observe-only precedent for
  self-observation instruments.
- **An actuator:** the railed convergence-gain attenuation (floor 0.45) on the
  reflective loop — the cost probe harness
  (`identity_stability_baseline.py` / `reflective_loop_cost_probe.py`)
  already measures what touching it costs identity.
- **A decision pattern:** governance arbitrates; subsystems report. A Tier 5
  attentional controller should follow the same authority hierarchy — it
  reports/requests, `SelfhoodGovernance` decides — and the wiring precedent
  for a new tier is the 4.x pattern (attach explicitly, neutral default =
  byte-identical behavior, terminal-sink discipline until a feedback loop is
  deliberately and verifiably introduced).
- **A validation template:** physics validated → psychology characterized →
  findings recorded with controls (the 4.2/4.3 precedent).

## The open questions that belong to Tier 5 (not to the training plan)

- Whether attentional control is *only* loop-gain modulation, or also includes
  directing which attractors/rhythms receive the loop's convergence.
- Whether the controller may ever read `dilation_factor` / subjective time
  (currently forbidden terminal sinks — relaxing that is a deliberate
  architectural change, not a default).
- The bonded-adversarial probe (ROADMAP "Tier 5/6") — bond mechanics plus a
  slowly-hostile source — which also resolves Tier 4.2's central
  unfalsifiable claim and should be designed alongside Tier 5.
