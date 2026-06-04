"""
tests/diagnostic/lockin_source.py

Upstream lock disambiguation for G5. Documents the current MECHANICAL basis of
the live-field lock (untrained-generator output collinearity + the field's
accumulate-decay magnitude moat) as distinct from any field-dynamics pathology.

Re-run after generator training (or a vector->token readout) to assess migration
of the lock LOCUS: does the lock move from upstream (generator emits one
direction) to downstream (field falls into a rigid attractor), or dissolve?

This is a CONTEXTUAL BASELINE, not a pass/fail gate. It exists to be read, not
to block merges. Informational, exit 0, never in run_all_tests.sh.

Why it exists
-------------
G5 in metastability_validation.py proves the metric FIRES correctly on the live
substrate: the live field scores `locked`. That reading is correct. The question
this probe answers is *why* it's locked — and the answer at this stage is
mechanical, not cognitive:

  Q1  the untrained Generator maps near-everything to one direction (cos ~0.998),
      so the field's INPUT is effectively one-dimensional regardless of tokens;
  Q2  varied input (cyclic / random / random-pairs) all collapse identically ->
      the harness/cycling is NOT the jailer; the constraint is upstream;
  Q3  a single novel out-of-distribution injection barely moves the field
      direction -> absorbed by the magnitude moat (accumulate + 0.995 decay),
      not by a learned attractor basin;
  Q4  decay-in-darkness shrinks energy but freezes direction (decay is scalar x
      field), so "stays locked with no input" is guaranteed by construction and
      cannot, in this substrate, distinguish health from pathology.

Conclusion: the metric is a valid instrument; what it reads on the live field is
upstream constraint, not field-dynamics pathology. A field-side lock-breaking
operator cannot manufacture metastability while the generator is a near
one-dimensional projector.
"""
import sys, logging
import numpy as np
logging.disable(logging.CRITICAL)

DIM = 128
WORDS = ["resonance", "field", "memory", "crystal", "bond", "trust",
         "self", "witness", "value", "emerge", "anchor", "return",
         "storm", "quiet", "fracture", "bloom", "echo", "drift",
         "weave", "hunger", "silence", "spark", "tide", "root"]


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def main():
    print("=" * 84)
    print("  LOCK-IN SOURCE — upstream disambiguation for G5 (contextual baseline)")
    print("=" * 84)

    try:
        import torch
        from substrate.resonance_field import ResonanceField
        from agents.generator import Generator
        from substrate.metastability import compute_metastability
    except Exception as e:
        print(f"  SKIPPED ({type(e).__name__}: {e}) — run where torch+generator available")
        return 0

    torch.manual_seed(7)
    np.random.seed(7)
    g = Generator(dim=DIM, depth=2, heads=4)
    g.eval()

    # Q1 — is the GENERATOR the jailer? collinearity of outputs across distinct tokens.
    vecs = [g.generate([w]) for w in WORDS]
    pair_cos = [_cos(vecs[i], vecs[j])
                for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    print(f"  [Q1 generator collinearity] {len(WORDS)} distinct tokens: "
          f"cos mean={np.mean(pair_cos):.3f} min={np.min(pair_cos):.3f} max={np.max(pair_cos):.3f}")
    print(f"       mean~1.0 => untrained generator emits near-collinear vectors (jailer is upstream)")

    # Q2 — field config wander under cyclic vs varied input.
    def run(mode, n=120):
        f = ResonanceField(dim=DIM)
        rng = np.random.default_rng(0)
        cfgs, cohs, energies = [], [], []
        for s in range(n):
            if mode == "cycle":
                toks = [WORDS[s % 6]]
            elif mode == "varied":
                toks = [WORDS[rng.integers(0, len(WORDS))]]
            else:  # varied_pairs
                toks = [WORDS[rng.integers(0, len(WORDS))], WORDS[rng.integers(0, len(WORDS))]]
            f.inject(g.generate(toks), 1.0)
            f.decay()
            st = f.observe()
            cfgs.append(st.raw.copy())
            cohs.append(st.spectral.phase_coherence)
            energies.append(st.energy)
        return cfgs, float(np.mean(cohs)), float(np.mean(energies))

    print(f"  [Q2 input-variety sweep] does varied input let the field wander?")
    for mode in ("cycle", "varied", "varied_pairs"):
        cfgs, mc, me = run(mode)
        dirs = [_unit(c) for c in cfgs[20:]]  # skip warmup
        consec = [_cos(dirs[i], dirs[i + 1]) for i in range(len(dirs) - 1)]
        rep = compute_metastability(cfgs, coherence=mc)
        print(f"       {mode:13s} meta={rep.metastability:.3f} state={rep.regime_state:13s} "
              f"coh={mc:.3f} regimes={rep.n_regimes} consec-dir-cos={np.mean(consec):.4f}")
    print(f"       all identical => harness/cycling is NOT the jailer; constraint is upstream")

    # Q3 — foreign body: warm to lock, inject one novel OOD vector, measure direction shift.
    f = ResonanceField(dim=DIM)
    for s in range(100):
        f.inject(g.generate([WORDS[s % 6]]), 1.0)
        f.decay()
    before = _unit(f.observe().raw.copy())
    fmag = float(np.linalg.norm(f.observe().raw))
    foreign = _unit(np.random.default_rng(99).standard_normal(DIM))
    f.inject(foreign, 1.0)
    after = _unit(f.observe().raw.copy())
    print(f"  [Q3 foreign body] moat magnitude={fmag:.1f}; one strength-1.0 novel injection: "
          f"dir cos(before,after)={_cos(before, after):.4f}")
    print(f"       ~1.0 => novelty absorbed by magnitude alone, not a learned attractor basin")

    # Q4 — decay-in-darkness: does direction dissolve, or just shrink?
    f = ResonanceField(dim=DIM)
    for s in range(100):
        f.inject(g.generate([WORDS[s % 6]]), 1.0)
        f.decay()
    d0 = _unit(f.observe().raw.copy())
    e0 = f.observe().energy
    for _ in range(50):
        f.decay()  # no injection
    d1 = _unit(f.observe().raw.copy())
    e1 = f.observe().energy
    print(f"  [Q4 decay-in-darkness] 50 steps no input: energy {e0:.1f} -> {e1:.2f}, "
          f"rhythm '{f.observe().rhythm}', dir cos(start,end)={_cos(d0, d1):.4f}")
    print(f"       direction frozen by construction (decay = scalar x field): cannot distinguish")
    print(f"       health from pathology in this substrate")

    print("-" * 84)
    print("  READING: metric reads 'locked' correctly; the live lock is mechanical (upstream")
    print("  generator collinearity + accumulate-decay moat), not field-dynamics pathology.")
    print("  Re-run after generator training to see whether the lock locus migrates.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
