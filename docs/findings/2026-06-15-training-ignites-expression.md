# Does training the generator on the corpus ignite RFE's expression?

- **Date:** 2026-06-15
- **Substrate:** live full stack (`build_full_stack`, dim 64 (the test-helper default; production is 128, untested for CII)), eval-mode generator,
  in-repo corpus `data/corpus/` (v1.1.0: 2870 train sequences), 4-source workload.
- **Probe:** `tools/ignition/train_ignite.py` (paired by seed, 8 epochs rhythm-pretraining).
- **Status:** active — the acceptance test for the CII work; passes.
- **Depends on:** 2026-06-15-cii-ignition-decomposition.md (the metric + the
  init-dependence finding), 2026-06-11-corpus-g1-pretrain.md (the corpus / G1).

## Question
The CII decomposition found RFE's expression-level ignition is generator-init-
dependent (locked for most random generators, metastable for some) and that no
late-stage gate (ITG) lifts a locked expression — the lever is the generator.
Direct test: does rhythm-pretraining the generator on the in-repo corpus turn
ignition from an init lottery into a reliable property? Paired by seed (same
init both arms), eval-mode, measure expression-stream CII untrained vs trained.

## Pre-declared signatures
- SUCCESS: trained ignition fraction >> untrained, ideally all seeds flip
  locked -> metastable with CII_expr at parity with the generator potential (~2.9+).
- NULL: training does not change the regime state (gate stays closed).
- ARTIFACT: a difference driven by mode (train vs eval) rather than learned
  weights — controlled by forcing eval() in both arms.

## Result (observed)
Paired, eval-mode, 8 epochs, expression-stream CII (robust signal = regime state):

| seed | UNTRAINED | TRAINED |
|------|-----------|---------|
| 1 | cycling, 2 reg, CII 0.00 | **metastable, 7 reg, CII 3.65** |
| 2 | locked, 1 reg, CII 0.00 | **metastable, 6 reg, CII 4.04** |
| 3 | locked, 1 reg, CII 0.00 | **metastable, 4 reg, CII 3.86** |

**Ignited (expression metastable): untrained 0/3 → trained 3/3.** Reproduced
across two runs. R/I/Cm are unchanged (already at ceiling); the entire effect is
in the metastability term.

## Interpretation
Training the generator on the corpus **reliably ignites the expression**: every
seed flips locked → metastable, and CII_expr lands ~3.6–4.0 — at or above the
generator potential measured untrained, and well past the ~2.9 acceptance bar.
This closes the arc: the survival-by-coherence lock collapses the expression to
one regime only when the generator presents low-rank/init-locked input; once the
generator is trained to present real rhythm-structured diversity (G1: eff_rank
1.45→3.46, rhythm-NN 0.99), that diversity survives stage C and the expression is
metastable. The upstream lever (training), not a downstream gate, is what lifts
RFE onto the ignition index — exactly as the ROADMAP held and the ITG negative
result predicted.

## Threats / confounds
- Cs **scalar** is v0.1-fragile; the conclusion rests on the **regime state**
  flip (locked/cycling → metastable), which is robust, not on the float.
- 3 seeds, 8 epochs, one workload family, one dim (64; production 128 untested). In-process training
  (not the shelved checkpoint round-trip).
- Mode controlled: eval() forced in both arms, so the lift is learned weights,
  not train-mode dropout noise (the 2026-06-08 read-side caveat).
- Generalization to held-out vocabulary not measured here (G1 covers that
  separately); this measures the live expression regime, not held-out eff_rank.

## Attention-pooling follow-up — does a richer readout add headroom on top of training?

Prompted by an external (GPT) structural critique: the masked **mean-pool**
(`generator.forward`) is a static compression that could cap readout
expressiveness; proposed replacing it with learned **attention-weighted pooling**
(`Linear→Tanh→Linear→softmax` over the encoder output), preserving the projection
head and the unit-output normalization. Tested as a `Generator` subclass, both
arms trained 8 epochs on the corpus, paired by seed, eval-mode.

| seed | mean-pool (trained) | attention-pool (trained) |
|------|---------------------|--------------------------|
| 1 | metastable, 7 reg, CII 3.78 | metastable, 6 reg, CII 3.62 |
| 2 | metastable, 6 reg, CII 3.78 | metastable, 7 reg, CII 3.81 |
| 3 | metastable, 6 reg, CII 3.67 | metastable, 4 reg, CII 3.65 |

Both preserve `|output|=1.00` (unit invariant intact, as predicted) and keep the
manipulation layer silent (0%). **CII is statistically indistinguishable** — the
attention readout adds no ignition headroom once the generator is trained,
corroborating that the binding constraint was the **weights** (low-rank geometry,
fixed by training), not the **pooling function**. Not integrated into the core (no
measured benefit on this axis). Left open: whether attention pooling helps
*untrained* init-robustness or sequence-continuity — different axes than CII.

## Open / next
- Sweep epochs / seeds for the ignition-fraction curve; confirm on held-out tokens.
- Re-run the full lock-in / metastability baselines on the trained generator
  (does training also move the field-level pin, or only the expression stream?).
- The read-side question (raised by GPT): is ResonanceField / Witness measuring
  manifold diversity, or echoing projection geometry? Connects to
  2026-06-06-read-side-boundary.md (feedback gates survival, not generation).
- With reliable expression metastability, revisit whether the ITG scaffold has a
  residual role (shaping) — now that there is real diversity for it to shape.
