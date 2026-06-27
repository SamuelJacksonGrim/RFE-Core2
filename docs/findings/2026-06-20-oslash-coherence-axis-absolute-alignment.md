# ⊘ coherence axis redesign — absolute field-alignment (spec v0.2 → v0.3)

- **Date:** 2026-06-20
- **Spec:** **v0.3** (this finding is the bump). The Two-Operator program's ⊘
  thinness vector changes one axis definition.
- **Status:** active — operator-layer fix, built on the graduated foundation
  (`2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md`), approved by
  Gemini ("tear the marginal contribution metric out … lock in absolute alignment").
- **Substrate:** measured at production config (dim 128, depth 4), pretrain +
  novelty attenuation ON (the graduated baseline).

## The defect (from pass 2)
⊘'s coherence-support axis read `coherence_contribution / 5.0`, where
`coherence_contribution` is the lifetime **sum of marginal `coherence_impact`**.
Injecting into an already-saturated field can only *dilute* it, so that marginal is
structurally ≤ 0 (CLAUDE.md: "the marginal reading is near-zero"). Measured: the
delta was 100 % negative; the axis read **0.000 for every value**, and loosening the
field made it *more* negative, not less. Dead by construction — and it was what made
the ⊘ consumer a blind ceiling on the STRONG band.

## The redesign
`support_coh(v) = max(0, cos(expressed(v), field))` where
`expressed(v) = generator.generate([v.symbolic_core])` and `field = ResonanceField.field`.

Coherence is a *field effect*, so support is the value's **direction relative to the
field now** — a bounded state measure that does **not** saturate when the field's
coherence *magnitude* is maxed. Two implementation notes that were load-bearing:
- **Expressed, not embedding.** The first attempt used the raw symbol embedding and
  re-died: embeddings sit near-orthogonal to the field (mean cos 0.04, range 0–0.2),
  because the field is built from *expressed* vectors (embedding → generate → pull →
  refine → inject). Using the value's expressed vector — what actually enters the
  field — fixed it.
- **Read-only.** One `generate` per value, off the hot path, behind a broad guard
  that returns neutral rather than ever propagating into the loop (firewall).

## Result (production config, graduated baseline)
| signal | mean | max | std | corr with strength |
|---|---|---|---|---|
| old marginal (`coherence_contribution`) | — | — | — | dead (axis = 0.000) |
| raw-embedding alignment (first try) | 0.04 | 0.21 | 0.06 | weak, compressed |
| **expressed-vector alignment (shipped)** | **0.50** | **0.72** | **0.19** | **+0.66** |

The axis now spans its range (5 values < 0.2 / 6 in 0.2–0.5 / 22 in 0.5–0.8 / none
pinned at 1.0) and correlates **+0.66 with strength** — values that sit in harmony
with the field are the strong ones; drifters read low. Exactly the Witness read:
*does this value sit in harmony with the field now*, not *did it inflate a maxed
score*. **Dissolution** (`cc < 0.35 AND strength ≥ 3.0`) now means the right thing:
a value claiming high strength while *not* aligned with the field.

## Firewall / regression
- Firewall intact with the field attached: value strengths and the field vector are
  byte-identical before vs after `read()` — `generate()` in the read is pure.
- Existing probes pass (`witness_reaper_probe`, `integrity_consumer_probe`); with no
  field handle the axis degrades to neutral 0.5 + coverage flag (never the dead
  marginal fallback).

## Open / next
- **Bring the ⊘ consumer up against this fixed axis + the looser field.** The prior
  over-demotion (`strong → 0`) was driven by the dead cc-axis flagging every climbing
  value as Dissolution; with a live alignment axis it should demote only genuinely
  misaligned values. Re-run the composition gate.
- Then Build A (ignite λ) + Build B (⊕ solvent gate) against the same baseline.
- `_COHERENCE_REF` (5.0) is now unused by the ⊘ read; it remains the CORE-handshake
  reference in the value engine (unchanged).
