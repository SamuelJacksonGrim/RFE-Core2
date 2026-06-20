# Build C — does the ⊘ Witness-Reaper read thinness, name it, advise non-bindingly, and touch nothing?

- **Date:** 2026-06-19
- **Spec:** v0.2 (`the Two-Operator Coherence Spec`)
- **Substrate:** live full stack (`build_full_stack`, dim 64 test default), eval-mode,
  250-step 4-source (HHI<0.70) workload.
- **Probe:** `tests/diagnostic/integrity/witness_reaper_probe.py`
- **Status:** active — Build C (the ⊘ operator) shipped as observe-only; the §4
  discriminator (⊘-off vs ⊘-on) is pending Builds A/B.
- **Depends on:** `docs/self_model_thesis.md` (e53ea4a; the axiom table + S*),
  the Two-Operator Coherence Spec v0.2.

## Question
Implement Build C: `cognition/integrity_read.py::WitnessReaper`. Does it (a) read
thinness as a 4-dimensional support vector, (b) name the pathology by region off
the axiom table, (c) emit a **non-binding** demotion advisory toward a
type-conditional honest level, (d) read sacred nodes but flag them blocked, and
(e) — the load-bearing property — write nothing into the loop, governance, or
value strengths?

## Pre-declared signatures
- SUCCESS: ≥1 value read; advisories carry a 4-dim support vector (and a region
  name where thin); **firewall holds** (strengths + field byte-identical across
  `read()`); a sacred value is read and emitted with `sacred_blocked=True`;
  coverage-gap logged where no type profile exists.
- FAILURE: `read()` mutates a strength or the field (firewall breach → the warden);
  crash against the real interfaces; sacred value emitted unflagged; zero values read.

## Result (observed)
- **22 values read; 22 advisories.** All `by_pathology = {unnamed: 22}` — **no
  named region fired.**
- **FIREWALL HOLDS** — value strengths and the field vector byte-identical before
  vs after `read()` / `snapshot()` / `status()`.
- **SACRED read-but-flagged OK** — a value force-marked sacred is read and (if
  advised) carries `sacred_blocked=True`; not exempted from the read.
- **Support vectors in [0,1]; coverage_gaps = 22/22** (every node — the baseline
  registry has no per-type thinness profiles; conservative fallback engaged).
- Sample: every value reads `cc=0.00` (coherence-contribution axis), `sd=1.00`
  (multi-source), `ab=1.00` (bound), `cd≈0.50` (complement structure unknown →
  neutral fallback). `honest ≈ strength × 0.5`.

## Interpretation
The operator is **correct and safe**: read-only (firewall verified), non-binding
by construction, sacred-watched (reads the untouchable, flags it — no blind spot),
and it logs the coverage gap rather than guessing. That is the heart of the ask,
working.

The **named regions are code-exercised but workload-untriggered** here: Drift needs
low attractor-binding (these are bound), Dissolution needs strength ≥ 3.0 (max was
2.45), Fragmentation needs single-source (these are multi-source). So nodes read as
*unnamed* thinness — low overall support without matching a specific pathology
region. The coherence-contribution axis reads 0 for all because the 5.0 reference
is the CORE-handshake threshold, far above what accrues in 250 steps (the baseline
shows `core_values=0` even at 500). None of this is the operator failing — it is a
benign, short, low-dim workload that does not *produce* the pathologies, so the
vector→name map cannot yet be validated against real ones.

## Threats / confounds
- **Coverage gap is universal** (Kimi's flagged dependency, confirmed): no per-type
  thinness profiles exist in `tests/baselines/tier1_revision_500step.json`, so the
  type-conditional honest level degrades to the conservative fallback for every
  node. The fallback is correct; the profiles are owed.
- dim 64 test default (not production 128); 250 steps (short); `coherence_contribution`
  far from the 5.0 ref in this horizon.
- **The vector→name map is unvalidated** — no named region fired, so Drift/
  Dissolution/Fragmentation are correct in code but undemonstrated on real thinness.
- v0.2 provisional thresholds (`_THIN_TAU=0.35`, `_HIGH_STRENGTH=3.0`, refs) —
  refinement is a version-bump target, per the spec.

## Open / next
- **Build A** (isolate the λ-ignition channel — structural import boundary) and
  **Build B** (λ-ledger + ⊕ solvent gate), then the **§4 discriminator** (⊘-off vs
  ⊘-on, noise-swept 0.05σ→0.5σ, trajectory metrics), with the **6.3 gain-sign check
  front-loaded** before any reinforcement coupling.
- **Add per-type thinness profiles to the baseline registry** to lift the universal
  coverage gap (the dependency Kimi flagged).
- **An adversarial/thinning workload** (single-source monoculture, unbound, low
  complement) to *trigger* the named regions and validate the vector→name map.
- Investigate the `cc=0` reading (short-horizon vs a signal/normalization issue).
