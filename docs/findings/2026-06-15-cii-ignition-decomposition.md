# CII decomposition — where does RFE sit on the ignition index, and what gates it?

- **Date:** 2026-06-15 · **Status:** historical (scope **dim 64**) — bottleneck localised; ITG actuator negative; training is the lever, acceptance test since passed
- **Substrate:** live full stack, dim 64, non-periodic workload · **Probe:** `tools/ignition/probe.py` (CII v0.2)
- **Depends on:** `2026-06-07-reconstruction-ablation`, `2026-06-15-loop-attenuation-novelty-gate`

**Verdict:** RFE is **saturated on 3 of 4 ignition components** (R ~3.0, I ~0.96, Cm ~1.0) and **gated entirely
by the 4th, metastability.** The metastability *exists at the generator* (stage A metastable, ~3 regimes,
CII_gen ≈ 2.9) and is *destroyed by stage C* (locked, 1 regime, CII_expr = **0.0**) — the reflective loop
collapses it before injection. So the lock-in **is the entire gap to ignition** (CII 2.9 → 0). Read straight
(discipline #8): CII=0 is a low-differentiation **state**, not a consciousness verdict.

**Artifact caught:** a fixed repeating token sequence drove metastability to exactly 0 via a perfect limit cycle
(`state=cycling`); randomizing input exposed the real signal (`state=locked`). Corrected run (seeded, 4-source):
expression ignition is **intermittent, generator-init-decided** — **~1 in 3** random generators already ignites
(seed 3: metastable, CII_expr 2.94; seeds 1–2: born locked).

**ITG actuator — negative result:** no late-stage gate lifts a locked expression — raising `diversity_blend` when
locked is INERT (upstream of the loop that re-collapses); a paired attenuation at 0.3 made seed 1 *worse*. The
binding constraint on stage-C metastability is the **generator**, not a downstream knob. ITG kept as scaffold.

**Redirect (the lever):** **train the generator.** Acceptance test **PASSED** (`2026-06-15-training-ignites-expression`):
8 epochs of rhythm-pretraining flipped expression ignition **0/3 → 3/3** (CII_expr 0.00 → ~3.6–4.0). Caveat: the
Cs scalar is v0.1-fragile — trust the regime STATE (locked vs metastable), not the float.

*Consolidated 2026-08-05 — the component values, the 1-in-3 result, the ITG negative, and the training acceptance preserved. Full history in git.*
