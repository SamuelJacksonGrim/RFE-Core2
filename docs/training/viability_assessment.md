# Training viability assessment

- **Date:** 2026-06-11
- **Question:** can RFE-Core2's generator be trained, with what's in the repo,
  to present the real (deterministic) diversity that the lock-in findings say
  is the upstream prerequisite for everything downstream — including Tier 5?
- **Verdict: VIABLE.** Mechanism proven live
  (`docs/findings/2026-06-11-trainer-gradient-path.md`); the binding
  constraint is corpus coverage, not infrastructure or theory.

## 1. Why training is the lever (the documented chain)

1. The field pins ~0.998 coherence; the **reflective loop** (cycle step 6) is
   the ablation-proven lock — identity-coherence and rigidity are the same
   mechanism (`2026-06-07-reconstruction-ablation.md`).
2. The designed remedy (Fix 2, the `gnov`-gated loop-loosening governor) is
   **deferred as premature**: the generator presents low-rank input, so
   loosening the loop would mostly admit dropout noise (`ROADMAP.md`).
3. The 2026-06-08 audit quantified it: at the live config (dim 64) the
   **deterministic** generator has effective rank ~1.6 (80% of variance in one
   axis, mean cos 0.79); the live system never calls `.eval()`, so ~half its
   apparent diversity is per-call dropout noise; with dropout off the injected
   expression collapses to ~1 regime
   (`2026-06-08-generator-dropout-diversity.md`).
4. Therefore: *"Generator diversity — training, raising dim, and the
   eval-decision — is the more upstream lever."* (`ROADMAP.md`, current
   understanding.) Tier 5's concrete mechanism waits on this.

## 2. What exists

### The model is trainable

`agents/generator.py` — embedding (vocab 8192 default, live tests use 4096) →
sinusoidal positional encoding → pre-LN TransformerEncoder (depth 3, heads 4
at the canonical config) → masked mean-pool → MLP projection → L2 normalize.
Dim 64 live. All standard `nn.Module` parameters; `compact_embeddings()`
already migrates Adam/SGD optimizer state, so the codebase anticipated an
optimizer existing. Inference goes through `@torch.no_grad()`
`generate()`/`encode_batch()`. `torch>=2.0` is already in `requirements.txt`;
at these sizes (~10⁵–10⁶ params) CPU training is sufficient — no new
dependencies, no GPU orchestration needed.

`cognition/recursive_attention.py` is also untrained (runs under `no_grad`,
behaves as a near-uniform mean-pooler; the `diversity_blend` knob compensates).
Training it is **out of scope** for this plan: the generator is the upstream
lever, and the de-collapse blend already neutralizes the attention collapse.
Revisit only after a trained generator changes what flows into it.

### The trainers (status after the 2026-06-11 repair)

| Trainer | Objective | Use | Status |
|---|---|---|---|
| `training/rhythm_pretraining.py` | supervised contrastive over rhythm labels (same-rhythm together, cross-rhythm apart) | **offline**, before the loop | gradient path repaired; degenerate-batch crash fixed; **works** (effect probe) |
| `training/contrastive_alignment.py` | InfoNCE; positives = same attractor/rhythm, negatives = cross-rhythm | **online**, collect() during the loop, train() periodically | was the only working one; unbounded dead indices removed |
| `training/self_distillation.py` | cosine pull toward own high-coherence outputs (coherence ≥ 0.80 = teacher) | **online** | gradient path repaired; **works** (path check) |

Repair details (all empirically verified by
`tests/diagnostic/training/trainer_gradient_path_check.py`):

- Self-distillation and rhythm pretraining built their loss on
  `encode_batch()` output — `@torch.no_grad()`, numpy — so `backward()` raised
  and **no training had ever been possible** through them. All trainers now
  route through the shared grad-enabled `training/encode.py::encode_grad()`.
- All trainers ended with an unconditional `generator.eval()`, silently
  resolving the open live-dropout architect decision as a side effect. They
  now restore the caller's mode.
- `RhythmPretrainer` crashed on any batch without a same-label pair
  (graph-less zero loss); degenerate batches are now skipped.
- Contrastive `collect()` kept two unbounded, stale-index dicts that nothing
  read (bounded-structures guardrail); removed.

### The instruments

- `tests/diagnostic/training/generator_diversity_audit.py` — the measurement standard
  (eval-mode eff_rank / mean cos / determinism control).
- `tests/diagnostic/training/rhythm_pretrain_effect_probe.py` — before/after training
  effect, with generalization + determinism controls.
- `tests/diagnostic/training/trained_generator_sim.py` — pre-declared
  GENERATOR-IS-THE-LOCK vs SECOND-LOCKER predictions for what a diverse
  generator does to the field; built for mocks, ready to be confirmed on a
  genuinely trained generator.
- `tests/diagnostic/audit/identity_stability_baseline.py` +
  `reflective_loop_cost_probe.py` — the identity-cost harness the live
  training phase must ride.
- `tests/baselines/*.json` + smoke/integration gate — regression rails.

## 3. The first empirical result

`rhythm_pretrain_effect_probe`, canonical dim-64 generator, 40 epochs on the
20 built-in seed sequences, **all metrics eval-mode** (determinism control
1.000 throughout):

| battery | | mean cos | eff_rank | rhythm-NN acc |
|---|---|---:|---:|---:|
| trained distribution (20 seqs) | before | 0.855 | 1.3 | 0.25 (chance) |
| | after | 0.210 | 3.1 | 1.00 |
| disjoint 120-token vocab | before/after | 0.811 | 1.5 | — |

Read: **TRAINS + NARROW** (both pre-declared). The mechanism restructures the
deterministic geometry exactly as needed — and only where the corpus reaches.
Twenty toy sequences cannot restructure a vocabulary; a curated corpus can
(`data_curation.md`).

## 4. What's missing (the actual work)

1. **A curated corpus.** The repo contains ~36 short token sequences total
   (20 rhythm seeds + 16 Resonance Family sequences). No on-disk dataset, no
   loader. This is the critical path — see `data_curation.md`.
2. **The `.eval()` architect decision** (open since 2026-06-08). Training
   sharpens it: once deterministic structure exists, dropout-as-diversity
   loses its only justification, but the decision is the architect's. The
   trainers no longer pre-empt it.
3. **Identity-stability cost reading.** Training the live generator changes
   what the witness/anchors see. No probe has measured what online training
   costs identity stability; the plan gates on it (`training_plan.md`,
   Phase 2).
4. **Loop integration glue** for the online trainers (a `collect()` call site
   at the post-watcher step and a periodic `train()` — design in
   `training_plan.md`; **not** built until offline phases pass their gates).

## 5. Stale framings corrected by this assessment

- `run_contrastive_bootstrap.py`'s header ("contrastive is SHELVED ...
  refinement, not a rescue") predates the 2026-06-08 audit, which showed the
  "already diverse" reading was dropout-inflated. The header is kept as
  history; the 2026-06-08 + 2026-06-11 findings supersede it.
- "The trainers exist, so training was always available" — false until
  2026-06-11: two of three crashed on the first gradient step, and nothing in
  the loop calls any of them. The system has never yet learned from
  experience.
