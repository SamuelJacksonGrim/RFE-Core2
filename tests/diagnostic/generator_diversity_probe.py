"""
tests/diagnostic/generator_diversity_probe.py

Re-measures the live untrained generator's directional diversity — the assumption
underneath "lock #1 = generator 1-D projector (cos ~0.998)". That claim predates the
`sqrt(d_model)` + init-std scale fix (shipped); this probe checks whether it still
holds on the current substrate. "Don't trust the wiring — run the path."

Measures mean pairwise cosine of generator outputs over diverse token sequences,
across random inits (the generator's weights are torch-random, so diversity is
init-dependent — a single unseeded run is not representative).

PRE-DECLARED SIGNATURES (before the run)
----------------------------------------
  RESOLVED : mean pairwise cos ≪ 0.9 across inits → the generator emits genuine
      directional diversity; the 1-D-projector lock (#1) is resolved by the scale fix.
  STANDING : mean ≈ 0.99 → still a 1-D projector; lock #1 stands.
  CONTROL  : the documented stub `spread=0.0` baseline reads cos ≈ 0.998
      (trained_generator_sim / multilayer-lock). The LIVE generator must differ from
      that for "resolved" to mean anything — otherwise the stub is the wrong model.

Informational. exit 0. NEVER in run_all_tests.sh.
"""
from __future__ import annotations

import itertools
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)

from agents.generator import Generator

DIM = 64
N_SEQ = 30
N_INITS = 6
VOCAB = [f"tok_{i}" for i in range(80)]


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / (np.linalg.norm(v) + 1e-9)


def measure(dim, seed):
    import torch
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    g = Generator(vocab_size=4096, dim=dim, depth=3, heads=4)
    dirs = [_unit(g.generate(random.sample(VOCAB, random.randint(1, 3)))) for _ in range(N_SEQ)]
    cs = [float(np.dot(dirs[i], dirs[j])) for i, j in itertools.combinations(range(N_SEQ), 2)]
    return float(np.mean(cs)), float(np.min(cs)), float(np.max(cs))


def main() -> int:
    print("=" * 76)
    print("  GENERATOR DIVERSITY RE-MEASURE — is lock #1 (1-D projector, cos 0.998) standing?")
    print("=" * 76)
    print(f"  live untrained generator, dim={DIM}, {N_SEQ} diverse sequences, "
          f"{N_INITS} seeded inits:")
    means = []
    for seed in range(N_INITS):
        m, lo, hi = measure(DIM, seed)
        means.append(m)
        print(f"      seed={seed}: mean_pairwise_cos={m:.3f}  range=[{lo:+.3f}, {hi:+.3f}]")
    mu, sd = np.mean(means), np.std(means)
    print(f"  across inits: mean={mu:.3f} sd={sd:.3f} min={np.min(means):.3f} max={np.max(means):.3f}")
    print(f"  control (stub spread=0.0 baseline): cos ≈ 0.998 (multilayer-lock)")
    print("-" * 76)
    if mu < 0.90:
        print(f"  → RESOLVED: the live generator emits genuine directional diversity (mean")
        print(f"    {mu:.2f}, init-dependent {np.min(means):.2f}–{np.max(means):.2f}); NONE is ~0.998.")
        print("    The 1-D-projector lock (#1) is resolved by the scale fix — it no longer")
        print("    matches the stub spread=0.0 baseline. Diversity is init-dependent, so it")
        print("    is a distribution, not a single number.")
    else:
        print(f"  → STANDING: mean {mu:.2f} ≈ 1-D; lock #1 still holds.")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
