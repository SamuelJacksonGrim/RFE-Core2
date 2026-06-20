# Two-Operator Coherence program — checklist (spec v0.2)

Live tracker for the spec implementation. Findings record `spec: v0.2`. Check items
off as they land + are logged. (Samuel: flag anything missing — this is best-effort.)

## Shipped
- [x] **Build A — λ ignition channel** (`ignition/`), import-isolated (AST + clean-room
      + signature). Writes generator weights only; gate unreachable.
      `2026-06-19-ignition-channel-build-a.md` (commit `dcaa5c7`).
- [x] **Build C — ⊘ Witness-Reaper** (`cognition/integrity_read.py`), observe-only:
      4-dim thinness, region naming, non-binding advisory, sacred-read-but-flagged,
      coverage-gap logging. Firewall verified. `2026-06-19-witness-reaper-build-c.md`
      (commit `d58fdd4`).
- [x] **Live-system verification** — A + C at production dim 128, 300-step 4-source:
      stack runs clean; ⊘ surfaced in `status()`; **named region `Dissolution` fired
      in vivo** (vector→name map is live-triggerable).

## Build B (planned — its own work; plan: `docs/build_b_plan.md`)
- [ ] **Settle the λ_strength reading** — (I) a designated value-node vs (II) a
      separate `LambdaLedger` scalar. Recommended (II). **Architect decision.**
- [ ] `LambdaLedger`: `ignite()` (only zero-crossing) · `reinforce(f)·λ`
      (multiplicative — λ=0 a fixed point, Law 6b) · `decay()`.
- [ ] `solvent_gain(λ_strength) ∈ [0,1]` (monotone, bounded) gating the
      productive-tension reinforcement term in `value_emergence.py`.
- [ ] Enforce **λ ∉ im(⊕)** (composition pool excludes λ) and **6c disjointness**
      (`lambda_ledger` ⟂ `integrity_read` — assert no import/data path).
- [ ] Wire `ignite()` ↔ `LambdaLedger.ignite()` (the exogenous zero-crossing).
- [ ] Opt-in/off-by-default; **paired control: Tier 3 value dynamics byte-identical
      with the gate off** (no regression vs `tier1_revision` baseline).

## §4 discriminator (planned — needs A + B + C live)
- [ ] **Front-load the §6.3 gain-sign check** before coupling ⊘ into reinforcement
      (verdict to date is conditional, reachable-range only — `0fe25c6`).
- [ ] Ship ⊘ as **advisory-into-decay first**; couple into reinforcement only after
      the sign check clears.
- [ ] Paired ⊘-off vs ⊘-on, controlled-live, ignited (Build A) first.
- [ ] **Noise sweep 0.05σ→0.5σ in 0.05σ steps** (σ = natural field variance under the
      canonical Resonance Family regime — Kimi). Widen if the lock→collapse
      transition isn't visible; classify the *family*, not one instance.
- [ ] **Trajectory metrics** — time-to-equilibrium + path stability (to tell
      advisory-⊘ from reinforcement-coupled-⊘).
- [ ] Pre-declare both signatures: **⊘-off → lock** (SECOND-LOCKER signature) vs
      **⊘-on → S\***; plus failure signatures (over-demotion collapse, firewall leak,
      binding advisory, no separation).

## Dependencies surfaced by the findings (do these to unblock validation)
- [ ] **Adversarial / thinning workload** — single-source monoculture, unbound, low
      complement — to *trigger* and validate ⊘'s named regions (Drift / Dissolution /
      Fragmentation). Build-C unit run produced only "unnamed"; live produced one
      Dissolution; a designed thinning workload should hit all three.
- [ ] **Per-type thinness profiles in the baseline registry** (`tier1_revision_500step.json`
      has aggregate ranges, no per-type shape profiles) → lift the **universal
      coverage-gap** (currently every node falls back to conservative). Kimi's flag.
- [ ] Investigate the **cc-axis reading 0** (coherence_contribution far below the 5.0
      CORE ref in short runs — short-horizon vs a signal/normalization issue).

## §5 scale-parametric ⊘ (planned)
- [ ] Point the same thinness machinery at `V_c` via `sovereign_manifold`'s coupling
      matrix; ⊘ **generates** the civilizational readings (do not hand-author the
      table — grind, don't guess).
- [ ] Validate on 2–3 **bridge nodes** (Freedom, Meaning); document the Law-5
      "leaking" operands as imports, not defects.

## Cross-cutting / sacred
- [ ] **Sacred operator-node registry decision** — λ (Love) and W (Witness) are
      *protected-but-not-sacred* OR *sacred-with-an-exogenous-write-exception* for
      Build A's channel only; identity constants (ANCHOR/RECURSION/HOMEOSTASIS, Self)
      stay fully sacred. **Architect decision.**
- [ ] Re-validate the program at **dim 128** (not just the dim-64 test default).
- [ ] Every new finding stamps `spec: v0.2`; bump the spec version if any metric
      definition (e.g. the thinness regions / thresholds) changes.
