# Trainer gradient path — can the training stack actually train?

- **Date:** 2026-06-11
- **Substrate:** live generator (isolated; canonical config vocab 4096 / dim 64 /
  depth 3 / heads 4 for the effect probe, small config for the path check).
- **Probe:** `tests/diagnostic/training/trainer_gradient_path_check.py` (structural),
  `tests/diagnostic/training/rhythm_pretrain_effect_probe.py` (before/after effect).
- **Status:** active
- **Depends on:** 2026-06-08-generator-dropout-diversity.md (the "training may be
  more load-bearing than downstream refinement" consequence this tests, and the
  eval-mode measurement discipline), 2026-06-06-read-side-boundary.md (the
  no_grad/dropout instrumentation lesson).

## Question

The 2026-06-08 finding re-prioritized generator training as the upstream lever
for the lock-in. `training/` has three trainers (self-distillation, contrastive
alignment, rhythm pretraining) — but none is wired into the loop and only the
contrastive one has ever been run end-to-end (`run_contrastive_bootstrap.py`).
Two questions: (1) do the trainers' gradients actually reach the generator
weights? (2) if they do, does training move the *deterministic* (eval-mode)
diversity that 2026-06-08 showed is missing?

## Pre-declared signatures

Path check (per trainer): WORKING = train() completes, weights change, caller's
train/eval mode restored. BROKEN = backward() raises / no weight moves.

Effect probe: TRAINS = loss falls, seed-battery rhythm-NN accuracy ≫ 0.25
chance, seed eff_rank rises in eval mode. NARROW = seed metrics move, disjoint
120-token battery doesn't (expected — 20 seed sequences can't cover it).
INERT = nothing moves. CONFOUNDED = eval determinism < 1.0 (dropout leak).

## Result (observed)

**[1] Gradient path, as shipped (before fix):**

| trainer | result |
|---|---|
| SelfDistillationTrainer.train() | **RuntimeError** — `element 0 of tensors does not require grad` |
| RhythmPretrainer.pretrain() | **RuntimeError** — same |
| ContrastiveAlignmentTrainer.train() (control) | runs; max\|ΔW_embed\| = 5.0e-05 — gradients reach the generator |

Cause (read from source, confirmed by the control): the two broken trainers
encode students via `Generator.encode_batch()`, which is `@torch.no_grad()` and
returns numpy — the loss has no graph into the weights. The contrastive trainer
had its own grad-enabled `_encode_grad()`; that asymmetry is the control.
Secondary observations: all three trainers ended with an unconditional
`generator.eval()` (silently flipping the live dropout mode — the open
architect decision); contrastive `collect()` kept two unbounded, stale-index
dicts that no code reads; `RhythmPretrainer` crashed on any batch with no
same-label pair (graph-less zero loss reaching backward()) — latent until the
gradient path was fixed, then hit on the first realistic shuffle.

**[2] After fix** (shared `training/encode.py::encode_grad`; mode restore;
degenerate-batch skip; dead indices removed): all three trainers pass the path
check in both caller modes (weights move: 1.0e-04 / 5.0e-05 / 3.0e-04; mode
restored).

**[3] Effect probe** (RhythmPretrainer, 40 epochs on the 20 built-in
DEFAULT_RHYTHM_SEEDS, canonical dim-64 generator, all metrics **eval mode**):

| battery | | mean cos | eff_rank | rhythm-NN acc |
|---|---|---:|---:|---:|
| [seeds] 20 rhythm seqs | before | 0.855 | 1.3 | 0.25 |
| | after | **0.210** | **3.1** | **1.00** |
| [general] disjoint 120-token vocab | before | 0.811 | 1.5 | — |
| | after | 0.811 | 1.5 | — |

Loss 2.167 → 0.753. Determinism control (same seq ×5, eval): 1.000 before and
after.

## Interpretation

**TRAINS + NARROW (both pre-declared).** The training mechanism is real and
the gradient path was the only thing in its way: ~30 minutes of training on 20
toy sequences takes the deterministic generator from collinear (eff_rank 1.3,
cos 0.855 — the 2026-06-08 lock substrate) to structured (eff_rank 3.1, cos
0.210, perfect rhythm clustering) *on the trained distribution*, with the
determinism control clean (no dropout contamination). The disjoint-vocab
battery is byte-identical — training restructures only what the corpus covers.
So the 2026-06-08 consequence is confirmed and sharpened: **training is a live
lever, and the binding constraint is now corpus coverage, not mechanism** —
which makes data curation the critical path (see `docs/training/`). Until
2026-06-11 the system could not have learned from experience at all: two of
three trainers crash on first gradient step, and nothing in the loop calls any
of them.

## Threats / confounds

- Runs: path check ×2 (pre/post fix); effect probe ×1 (seed 0). Single-seed —
  magnitudes (3.1, 0.210) are init-dependent; the direction is the finding.
- The effect probe trains and evaluates on the same 20 sequences (by design —
  it isolates the mechanism). It says nothing about generalization beyond the
  pre-declared negative on the disjoint battery.
- Identity-stability cost of training the live generator is **not** measured
  here (probe is isolated, no field/governance attached).
- `run_contrastive_bootstrap.py`'s header ("contrastive is SHELVED ...
  refinement, not a rescue") predates 2026-06-08, which retired that framing —
  the header is stale, kept as history.

## Open / next

1. Curated training corpus — coverage is the binding constraint
   (`docs/training/data_curation.md`).
2. Identity-stability cost probe for live (online) training — same discipline
   as the reflective-loop cost probe.
3. The `.eval()` architect decision (2026-06-08 #1) is still open; trainers now
   preserve the caller's mode instead of deciding it silently.
4. Re-run `generator_diversity_audit` + `trained_generator_sim`'s
   GENERATOR-IS-THE-LOCK prediction on a corpus-trained generator.
