"""
training/run_contrastive_bootstrap.py

Runnable harness that exercises ContrastiveAlignmentTrainer end-to-end (proves it
now backprops after the no_grad forward fix) and measures generator angular spread
before/after a contrastive round.

STATUS: contrastive is SHELVED. Round-one collinearity (cos ~0.998) turned out to
be an embedding/positional SCALE bug in the Generator, not a training gap — fixed
directly in agents/generator.py (sqrt(d_model) scale + init std). With that fix
the untrained generator already emits diverse vectors (cos ~0.62), so contrastive
is a later refinement, not a rescue. This harness is the round-two tool for if/when
we return to it; on the unfixed generator it documents the InfoNCE collapse to
loss=log(K) (the trivial all-equal fixed point) that motivated looking upstream.

Round one used a TOKEN-IDENTITY BOOTSTRAP: the trainer groups positives/negatives
by `rhythm` OR `attractor_id` (both field-derived and degenerate on a locked
field), so we feed the literal token through the `rhythm` field — "same rhythm" ==
"same token". No edit to the trainer's grouping logic; synthetic labels only.

Informational, exit 0. Not a CI gate. Run where torch is available.
"""
import sys, logging
import numpy as np
logging.disable(logging.CRITICAL)

DIM = 128
# Test set of distinct tokens for the collinearity / spread measurement.
WORDS = ["resonance", "field", "memory", "crystal", "bond", "trust",
         "self", "witness", "value", "emerge", "anchor", "return",
         "storm", "quiet", "fracture", "bloom", "echo", "drift",
         "weave", "hunger", "silence", "spark", "tide", "root"]


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def pairwise_cos(generator):
    """Mean/min/max pairwise cosine across the WORDS test set (rotation-invariant)."""
    vecs = [generator.generate([w]) for w in WORDS]
    pc = [_cos(vecs[i], vecs[j])
          for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    return float(np.mean(pc)), float(np.min(pc)), float(np.max(pc)), vecs


def field_wander(generator, compute_metastability, n=120):
    """Q2: drive the field with varied input, measure config-space wander."""
    from substrate.resonance_field import ResonanceField
    f = ResonanceField(dim=DIM)
    rng = np.random.default_rng(0)
    cfgs, cohs = [], []
    for _ in range(n):
        toks = [WORDS[rng.integers(0, len(WORDS))]]
        f.inject(generator.generate(toks), 1.0)
        f.decay()
        st = f.observe()
        cfgs.append(st.raw.copy())
        cohs.append(st.spectral.phase_coherence)
    dirs = [_unit(c) for c in cfgs[20:]]
    consec = float(np.mean([_cos(dirs[i], dirs[i + 1]) for i in range(len(dirs) - 1)]))
    rep = compute_metastability(cfgs, coherence=float(np.mean(cohs)))
    return consec, rep.n_regimes, rep.metastability, rep.regime_state


# Neutral filler tokens, disjoint from the WORDS test set — used only to give
# positives genuine context variation (an invariance to learn) without polluting
# the identity measurement.
FILLERS = ["a", "the", "of", "in", "and", "to", "is", "it"]


def build_bootstrap_samples(copies_per_token=8):
    """
    Token-identity labels: `rhythm` carries the anchor token so it becomes the
    grouping key. Positives for token w are w in DIFFERENT filler contexts, so the
    model must learn a w-specific invariance rather than collapsing to a constant.
    """
    rng = np.random.default_rng(1)
    samples = []
    for w in WORDS:
        for _ in range(copies_per_token):
            ctx = list(rng.choice(FILLERS, size=int(rng.integers(1, 3)), replace=False))
            toks = [w] + ctx                      # anchor token + varied filler context
            samples.append(dict(tokens=toks, rhythm=w, coherence=1.0, attractor_id=None))
    return samples


def heatmap_str(vecs, labels, k=10):
    """Compact pairwise-cosine matrix for the first k tokens (spread vs rotation read)."""
    lines = ["    " + " ".join(f"{l[:4]:>4s}" for l in labels[:k])]
    for i in range(k):
        row = " ".join(f"{_cos(vecs[i], vecs[j]):>4.2f}" for j in range(k))
        lines.append(f"{labels[i][:4]:>4s} {row}")
    return "\n".join(lines)


def main():
    print("=" * 84)
    print("  CONTRASTIVE BOOTSTRAP — round one (token-identity labels), generator angular spread")
    print("=" * 84)
    try:
        import torch
        from agents.generator import Generator
        from substrate.metastability import compute_metastability
        from training.contrastive_alignment import ContrastiveAlignmentTrainer
    except Exception as e:
        print(f"  SKIPPED ({type(e).__name__}: {e}) — run where torch+generator available")
        return 0

    torch.manual_seed(7)
    np.random.seed(7)
    g = Generator(dim=DIM, depth=2, heads=4)
    g.eval()

    # ---- PRE ----
    pre_mean, pre_min, pre_max, pre_vecs = pairwise_cos(g)
    pre_consec, pre_reg, pre_meta, pre_state = field_wander(g, compute_metastability)
    print(f"  PRE   Q1 pairwise-cos  mean={pre_mean:.3f} min={pre_min:.3f} max={pre_max:.3f}")
    print(f"        Q2 consec-dir-cos={pre_consec:.4f}  n_regimes={pre_reg}  "
          f"meta={pre_meta:.3f}  state={pre_state}")

    # ---- TRAIN (token-identity bootstrap; no trainer logic edits) ----
    # n_positives=1 -> textbook InfoNCE (avoids the 2nd-positive-as-distractor
    # mislabel). Higher LR than the trainer default (5e-5) to actually leave the
    # collapsed basin within a short bootstrap run.
    opt = torch.optim.AdamW(g.parameters(), lr=1e-3, weight_decay=1e-5)
    trainer = ContrastiveAlignmentTrainer(
        g, optimizer=opt, batch_size=8, n_positives=1, n_negatives=12,
        min_coherence=0.40, temperature=0.1, max_steps_per_call=4,
    )
    for s in build_bootstrap_samples(copies_per_token=8):
        trainer.collect(vec=g.generate(s["tokens"]), **s)
    print(f"  ---- buffer={trainer.buffer_size} samples; training token-identity labels ----")

    rounds = 120
    last = None
    for r in range(rounds):
        rep = trainer.train()
        if rep is None:
            print("  ABORT: buffer below min_required — increase copies_per_token")
            return 0
        last = rep
        if r % 10 == 0 or r == rounds - 1:
            print(f"    round {r:2d}: loss={rep.mean_loss:.4f}  acc={rep.mean_acc:.3f}  "
                  f"total_steps={trainer._total_steps}")

    g.eval()

    # ---- POST ----
    post_mean, post_min, post_max, post_vecs = pairwise_cos(g)
    post_consec, post_reg, post_meta, post_state = field_wander(g, compute_metastability)
    print(f"  POST  Q1 pairwise-cos  mean={post_mean:.3f} min={post_min:.3f} max={post_max:.3f}")
    print(f"        Q2 consec-dir-cos={post_consec:.4f}  n_regimes={post_reg}  "
          f"meta={post_meta:.3f}  state={post_state}")

    print("-" * 84)
    print("  POST pairwise-cos heatmap (first 10 tokens; rotation-invariant — low off-diagonal = real spread):")
    print(heatmap_str(post_vecs, WORDS, k=10))

    # ---- GATE ----
    g1 = post_mean < 0.90
    g2 = (post_consec < 1.0) and (post_reg > 1)
    print("-" * 84)
    print(f"  GATE  Q1 mean pairwise cos {pre_mean:.3f} -> {post_mean:.3f}  "
          f"(< 0.90 ? {'PASS' if g1 else 'FAIL'})")
    print(f"        Q2 wander: consec {pre_consec:.4f}->{post_consec:.4f}, "
          f"regimes {pre_reg}->{post_reg}  ({'PASS' if g2 else 'FAIL'})")
    print(f"  VERDICT: {'BOOTSTRAP BROKE COLLINEARITY — round two (field-derived) is runnable' if (g1 and g2) else 'collinearity not broken — tune (copies/steps/temperature)'}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
