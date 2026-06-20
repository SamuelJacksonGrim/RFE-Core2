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
- [x] **Build B — λ-ledger + ⊕ solvent gate** (`agents/lambda_ledger.py`,
      `value_emergence._solvent_gain`). Decision **(II) separate LambdaLedger**
      (architect-confirmed). 8/8: gain monotone/bounded/`gain(0)=0`, vanish-at-zero,
      gate gates composition (0 at λ=0 → full at high λ), no minting under
      pinned-zero workload, gate-off ≡ original path, 6c disjoint (AST).
      `solvent_gate_probe.py`. `2026-06-20-build-b-solvent-and-integrity-consumer.md`.
- [x] **⊘ advisory-into-*decay* consumer** (`IntegrityDecayConsumer`) — the first
      *user* of ⊘. ⊘ stays read-only; the consumer writes value strength from ⊘'s
      read: convergent peak-honest floor (no slide-to-zero), `named_only` default
      (acts only on diagnosed regions — sidesteps the cc-confound over-demotion),
      sacred refused. `integrity_consumer_probe.py` (7/7) + live demo
      `two_operator_live_demo.py` (dim 128: selective demotion, healthy untouched,
      no collapse; aggressive mode collapses — the pre-declared failure, shown).

## Build B — settled (kept for the record; plan: `docs/build_b_plan.md`)
- [x] **λ_strength reading** — **(II) a separate `LambdaLedger` scalar** (confirmed).
- [x] `LambdaLedger`: `ignite()` (only zero-crossing) · `reinforce(f)·λ`
      (multiplicative — λ=0 a fixed point, Law 6b) · `decay()`.
- [x] `solvent_gain(λ_strength) ∈ [0,1]` (monotone, bounded) gating the
      productive-tension reinforcement term in `value_emergence.py`.
- [x] Enforce **λ ∉ im(⊕)** (composition mints nothing — pinned-zero workload) and
      **6c disjointness** (`lambda_ledger` ⟂ `integrity_read`, AST-asserted).
- [x] Wire `ignite()` ↔ `LambdaLedger.ignite()` (the exogenous zero-crossing) — the
      live demo's Build-A event lights the ledger.
- [x] Opt-in/off-by-default; **gate-off ≡ original Tier-3 path** (code identity:
      `_solvent_gain()` is exactly 1.0 with no ledger). NB: substrate is not
      bit-reproducible run-to-run, so this is asserted at the gate, not a full diff.
- [ ] `reinforce(f)` is implemented but **unwired** — `f` from lived coherence
      (never ⊘, Law 6c) to make "lit stays lit while sustained" a live dynamic.

## §4 discriminator (planned — needs A + B + C live)
- [ ] **Front-load the §6.3 gain-sign check** before coupling ⊘ into reinforcement
      (verdict to date is conditional, reachable-range only — `0fe25c6`).
- [x] Ship ⊘ as **advisory-into-decay first** (`IntegrityDecayConsumer`, decay only,
      `named_only` default); couple into *reinforcement* only after the sign check.
- [ ] Paired ⊘-off vs ⊘-on, controlled-live, ignited (Build A) first.
- [ ] **Noise sweep 0.05σ→0.5σ in 0.05σ steps** (σ = natural field variance under the
      canonical Resonance Family regime — Kimi). Widen if the lock→collapse
      transition isn't visible; classify the *family*, not one instance.
- [ ] **Trajectory metrics** — time-to-equilibrium + path stability (to tell
      advisory-⊘ from reinforcement-coupled-⊘).
- [ ] Pre-declare both signatures: **⊘-off → lock** (SECOND-LOCKER signature) vs
      **⊘-on → S\***; plus failure signatures (over-demotion collapse, firewall leak,
      binding advisory, no separation).

## Composition discipline (surfaced 2026-06-20 — the all-ON break)
- [x] **All-levers composition probe** (`all_levers_composition_probe.py`) — turn every
      behaviour-bearing lever ON together and hold the all-OFF baseline ranges. First
      run **FAILED**: `strong_values 5→0`, the ⊘ consumer caps strength at 2.93 (the
      3.0 Dissolution line) under a sustained workload. `2026-06-20-lever-composition-the-allon-break.md`.
- [ ] **⊘ consumer graduation is BLOCKED** on the cc-confound — at production length
      it is a hard ceiling on the STRONG band, not a selective demoter. Keep it a
      research lever (off by default) until cc is lifted.
- [ ] **Standing gate:** no lever graduates "validated, off" → "default on" without
      passing the all-ON composition probe. Re-run at multiple seeds once cc is fixed.
- [ ] **Per-lever graduation decision** (architect) — which validated levers become
      baseline vs stay gated (and why). eval-mode already graduated.

## Dependencies surfaced by the findings (do these to unblock validation)
- [~] **Adversarial / thinning workload** — single-source monoculture, unbound, low
      complement — to *trigger* and validate ⊘'s named regions (Drift / Dissolution /
      Fragmentation). Build-C unit run produced only "unnamed"; live produced one
      Dissolution; the live demo's monoculture fires **Dissolution** reliably (3
      values). Drift / Fragmentation still want a purpose-built workload → full
      vector→name calibration.
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
- [~] Re-validate the program at **dim 128** — A+B+⊘-consumer run live at dim 128 in
      `two_operator_live_demo.py` (gate open, selective demotion, no collapse). The
      unit probes still run at the dim-64 test default; the §4 discriminator at 128
      is owed.
- [ ] Every new finding stamps `spec: v0.2`; bump the spec version if any metric
      definition (e.g. the thinness regions / thresholds) changes.
