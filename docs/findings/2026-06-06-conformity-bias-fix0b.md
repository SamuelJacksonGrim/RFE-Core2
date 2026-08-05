# Conformity bias in the reaper — does coherence buy survival, and does a gated novelty term fix it?

- **Date:** 2026-06-06 · **Status:** historical — bias confirmed + fix decided (asymmetric shipped; symmetric validated isolation-only, closed out by the full-loop finding)
- **Substrate:** isolated (`DecayProfile.compute`, reaper math only) · **Probe:** `conformity_bias_probe.py`
- **Depends on:** `2026-06-06-read-side-boundary`, `2026-06-06-coherence-is-not-plasticity`

**Verdict:** conformity bias **CONFIRMED** at its true size **~3–7%/lap** (class-dependent) — *not* the ~10¹¹×
figure an early un-normalized version reported (artifact, caught + rebuilt to per-step multiplier). Coherence
gives a small, monotonic, **unopposed** per-lap survival lean that compounds: coherent doubles the gap over an
equally-recurrent novel pattern every ~11 laps (GLYPH, coh_w 0.10 → +6.56%/lap). The lean tracks `coh_w` across
three independent profiles (the trustworthy corroboration — the effect follows the knob). Control was the
construction itself: two `SymbolState`s equal in every reinforcement term except `field_coherence`.

**Fix:** a **symmetric gate** (gate BOTH coherence and novelty by recurrence) drives the lean to **−0.00%/lap**
with all target signatures holding (noise recur=0 → no bonus; high-recurrence parity 1.0000) — *in isolation*.
**Shipped conservative:** the **asymmetric** gated-novelty term (mirror novelty, gate by recurrence) — reduces
GLYPH 6.6% → 4.3% with zero identity-formation risk. Symmetric stayed a candidate.

**Closed out in vivo (`2026-06-07-fix0b-fullloop-validation`):** direct term small (+1.16%/lap), symmetric cancels
it with baselines intact — **but** a coherence-only lean is **not observationally separable** live (coherence /
recurrence / binding entangle 0.92–1.0; the real survival link is **binding magnitude**, which the reaper formula
can't adjudicate). **Decision: keep asymmetric**; symmetric is a safe minor upgrade, **not** the lock lever (that's
upstream attractor migration). Universal gate evaluated, not warranted.

*Consolidated 2026-08-05 — the true effect size, the artifact caught, the fix, and the in-vivo verdict preserved. Full history in git.*
