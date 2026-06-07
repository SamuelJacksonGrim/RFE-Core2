# Fix 0-B full-loop validation — does the conformity lean survive in vivo, and does the symmetric gate fix it?

- **Date:** 2026-06-07
- **Substrate:** live (Generator-warmed full stack). The three reaper formulas
  are evaluated probe-side on the **real harvested SymbolState population**, and
  the baseline-safety arm monkeypatches each formula into the **live** loop for a
  canonical 500-step run. Only the reaper reinforcement formula is varied;
  nothing is written to `symbolic_memory.py`.
- **Probe:** `tests/diagnostic/fix0b_fullloop_probe.py` (seed 42, dim 64, 600 steps)
- **Status:** active — resolves Open/next #1 of
  `2026-06-06-conformity-bias-fix0b.md` (the owed full-loop run).
- **Depends on:** 2026-06-06-conformity-bias-fix0b.md (the isolated result this
  tests in vivo), 2026-06-06-coherence-is-not-plasticity.md (where the real
  lock-in question lives), 2026-06-06-multilayer-lock.md (the moat / binding).

## Question
The isolated probe forced attractor/centrality/crystal **equal** by hand, so the
symmetric gate cancelled the conformity lean cleanly. The finding's main unproven
risk (threat #1): in a live run those signals **correlate** with coherence — a
field-agreeing pattern also binds attractors and crystals — so coherence's shadows
could leak a survival lean through the *ungated* correlated terms even after the
direct coherence term is gated. Does the lean survive in vivo, and does symmetric
(or a universal) gate actually neutralise it without breaking healthy-state
baselines (threat #2)?

## Pre-declared signatures
- CONSERVATIVE-ENOUGH: shipped asymmetric already leaves no measurable in-vivo lean.
- SYMMETRIC-HELPS: symmetric cancels the in-vivo lean and baselines hold.
- CORRELATED-LEAKAGE → UNIVERSAL: symmetric leaves residual lean via ungated
  att/cry/cen → universal gate (gate all binding by recurrence) clears it.
- CORRELATED-LEAKAGE → STRUCTURAL: lean persists even universal → it rides the
  magnitude correlation, not the gating; recurrence-gating cannot fix it.
- CONFOUNDED: too few / degenerate low-coherence symbols → an in-vivo coherence-only
  effect is not observationally separable.

**Controls:** (1) same-symbol counterfactual — each real symbol scored at coh=0.90
vs 0.05 with *all else fixed* (decay cancels; the clean direct measure). (2)
coherence-label **shuffle** — all correlations must collapse to ~0. (3) the
low-coherence cohort is the comparison group for the observational arm. (4) baseline
ranges from `baselines/tier1_revision_500step.json`.

## Result (observed)
52 symbols harvested; low-coherence (<0.5) cohort = 6.

**Correlated-signal structure (the leakage channels), with shuffle control:**
- coh × attractor ≈ **+0.92**, coh × crystal ≈ **+0.92**, coh × centrality =
  **+1.00**, coh × recurrence ≈ **+0.64**, coh × usage ≈ **+0.64**.
- shuffle control: max |corr| ≈ **0.13** (collapses ✓). The structure is real,
  not an artifact. (Raw correlations wobble ±0.01 across runs — minor generator-init
  nondeterminism; the structure is invariant.)

**Direct conformity term — same-symbol counterfactual [clean control]:**

| mode | per-lap lean | 2× in |
|------|-------------:|------:|
| asymmetric (shipped) | **+1.16%/lap** | 60 laps |
| symmetric | **+0.00%/lap** | never |
| universal | **+0.00%/lap** | never |

**Magnitude (shipped asymmetric, mean reinforcement contribution, hi-coh n=46):**
coherence term ≈ **0.047**, novelty ≈ 0.001, attractor ≈ 0.85, crystal ≈ 1.26,
centrality ≈ 0.08. Binding (att+cry+cen) ≈ **2.19** — about **47×** the coherence
term. The low-coherence cohort reads **0.000 on every channel** (zero recurrence,
zero binding).

**Baseline safety (each gate live, canonical 500-step run):** both **PASS** all
checked metrics — allow_rate 0.992 ∈[0.95,1.0], min_trust 5.0, HHI 0.264 ∈[0.2,0.4],
bonds 2/1 ∈[1,4], active_values 46 ∈[30,60], core 0.

**Observational arm (partial-r of reinforcement with coherence | recurrence):**
reported by the probe but **CONFOUNDED** (see below) — not used for the verdict.

## Interpretation
The CONFOUNDED signature fired for the *observational* arm and SYMMETRIC-HELPS
fired for the *direct* channel — a split verdict:

1. **The direct conformity term is real, small, and cleanly gateable.** Asymmetric
   leans +1.16%/lap; symmetric and universal cancel it to exactly 0, and both keep
   healthy-state baselines. So the symmetric gate is **safe and works** — but on a
   term that is **~47× smaller** than the binding contribution to survival.
2. **An in-vivo "coherence-only" survival lean is not observationally separable.**
   In vivo, low coherence = a **brand-new, un-recirculated symbol** (zero
   recurrence, zero binding), not a recurring novel dissenter. Coherence,
   recurrence and binding are entangled at 0.92–1.0, so you cannot isolate
   coherence's independent survival effect from live data — the partial-correlation
   is recurrence-confounded (the gate `1−e^(−0.5·rec)` is nonlinear in recurrence,
   which coherence tracks). Only the same-symbol counterfactual is clean.
3. **The dominant survival/coherence link is binding magnitude, which the reaper
   formula cannot adjudicate.** Whether high attractor/crystal binding is
   *legitimate earned integration* or *pathological conformity* is not a reaper
   question — it is the **attractor-mobility** question from
   coherence-is-not-plasticity. Recurrence-gating the binding signals (universal)
   does not decorrelate their magnitudes from coherence; it is not the lever.

**Decision:** keep the shipped **asymmetric** patch. Adopting the **symmetric**
gate is defensible (safe; fully cancels the direct term) but is a small, clean
win, not the lock-in fix. **Universal gating is not warranted now** — it perturbs
binding broadly for a channel not shown to be harmful. The real lock-in lever is
upstream (attractor migration), not in the reaper's survival math.

**Misread caught:** the first version of the in-vivo measure used the retention
*multiplier* (decay × reinforcement). `decay` is dominated by symbol **age**
(step_counter ≈ 10,800 after 600 cycles → large, varied ages), so it returned a
spurious partial-r ≈ −0.98 nearly identical across all three formulas and a false
"conservative-enough" verdict — it was measuring age-vs-coherence, not conformity.
Excluding decay (age-driven, formula-independent) and measuring the reinforcement
channel fixed it. The control that caught it: the formulas being *indistinguishable*
under the multiplier measure was the alarm.

## Threats / confounds
- **Runs:** 1 seed (42), single dim (64), 600 steps. The direct-term result
  (+1.16%/lap; gates → 0) and the 47× scale are stable across re-runs; the raw
  correlations vary ±0.01 (generator-init nondeterminism not fully removed by
  torch seeding — numpy/global state). Multi-seed sweep not yet run.
- **Degenerate low-coherence cohort** (the load-bearing confound). With only 6
  low-coherence symbols, all zero-everything, the observational contrast is
  "established vs brand-new", not a coherence contrast. A workload that produces
  recurring low-coherence patterns (genuine surviving dissent) would be needed to
  measure an in-vivo lean directly — and the field pins coherence so high that
  such patterns are rare by construction (see multilayer-lock).
- Untrained-generator caveat inherited from the substrate's current state.
- The baseline-safety arm uses the canonical Resonance Family workload only; it
  does not prove identity stability under adversarial or high-novelty workloads.

## Open / next
1. **Multi-seed / multi-workload sweep** to bound the correlation variance and
   confirm the direct-term and baseline results hold off seed 42.
2. **The real question is upstream, not in the reaper:** does the attractor
   geometry migrate under persistent surviving novelty? (coherence-is-not-plasticity
   step 2). The reaper conformity term is now characterised and small; effort should
   move to attractor migration + the 85% gate decomposition.
3. If the symmetric gate is adopted, it is a one-line substrate change (gate the
   coherence term by recurrence, mirroring novelty) — safe per the baseline arm —
   but record it as a direct-term hygiene fix, **not** a lock-in remedy.
