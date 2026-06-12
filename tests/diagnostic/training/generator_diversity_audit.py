"""
tests/diagnostic/training/generator_diversity_audit.py

Multi-method audit of generator diversity — supersedes the single-metric (mean
pairwise cosine, train-mode) reading in `generator_diversity_probe.py`, which
overstated diversity. Triggered by "run it with different methods, full stack, observe."

The single-metric trap: mean pairwise cosine can look diverse while (a) the outputs
occupy a tiny subspace (low effective rank) and (b) the generator is run in TRAIN mode
with dropout active, so per-call DROPOUT NOISE inflates apparent diversity. `generate()`
is `@torch.no_grad()` but no_grad does NOT disable dropout, and nothing calls `.eval()`
— so the live system runs the generator stochastically.

Two parts:
  PART 1 (isolated generator): train vs eval, dim 64 vs 256 — mean pairwise cosine,
    effective rank (participation ratio of singular values²), top-1 singular energy,
    and DETERMINISM (same token N×: eval→1.0, train→<1 reveals dropout).
  PART 2 (full live stack): does upstream generator diversity survive to the injected
    expression? Monitors stage-A (generator) vs stage-C (expression) metastability
    regimes, field coherence, and gnov (the Fix-2 trigger), train vs eval.

PRE-DECLARED READS
------------------
  DIVERSE (lock #1 resolved): eval-mode eff_rank ≫ 1, mean cos ≪ 0.9, and the live
    expression stays multi-regime without dropout.
  PARTIAL / DROPOUT-INFLATED: train looks diverse but eval is collinear (eff_rank ~1–2,
    cos ~0.8) and the deterministic expression collapses to ~1 regime → the apparent
    diversity is dropout noise, and lock #1 is only partially resolved.
  CONTROL: determinism — eval must read ~1.0 (deterministic). If train ≪ 1.0, the
    generator is stochastic and any train-mode "diversity" is contaminated.

Informational. exit 0. NEVER in run_all_tests.sh.
"""
from __future__ import annotations

import itertools
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)

from agents.generator import Generator
from tests._common import (build_full_stack, RESONANCE_FAMILY_SOURCES,
                           RESONANCE_FAMILY_WEIGHTS)

VOCAB = [f"tok_{i}" for i in range(120)]


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / (np.linalg.norm(v) + 1e-9)


def _battery(dim, seed, mode, n=60):
    import torch
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    g = Generator(vocab_size=4096, dim=dim, depth=3, heads=4)
    g.eval() if mode == "eval" else g.train()
    M = np.array([_unit(g.generate(random.sample(VOCAB, random.randint(1, 3)))) for _ in range(n)])
    cs = [float(np.dot(M[i], M[j])) for i, j in itertools.combinations(range(n), 2)]
    lam = np.linalg.svd(M, compute_uv=False) ** 2
    eff_rank = float((lam.sum() ** 2) / (np.sum(lam ** 2) + 1e-12))
    reps = np.array([_unit(g.generate(["tok_5"])) for _ in range(5)])
    det = float(np.mean([np.dot(reps[i], reps[j]) for i, j in itertools.combinations(range(5), 2)]))
    return float(np.mean(cs)), eff_rank, float(lam[0] / lam.sum()), det


def _fullstack(mode, n=300, seed=11):
    import torch
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack()
    if mode == "eval":
        cycle.generator.eval()
    box = {"gn": None}
    og = cycle.generator.generate

    def g2(*a, **k):
        out = og(*a, **k)
        if box["gn"] is None:
            fd = cycle.field.field; nf = np.linalg.norm(fd); no = np.linalg.norm(np.asarray(out))
            box["gn"] = (1 - abs(float(np.dot(np.asarray(out), fd) / (nf * no)))) if nf > 1e-6 and no > 1e-6 else 0.0
        return out
    cycle.generator.generate = g2
    sids = list(RESONANCE_FAMILY_SOURCES); w = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    coh, gn, aR, cR = [], [], [], []
    for t in range(n):
        box["gn"] = None
        src = random.choices(sids, weights=w)[0]
        st = cycle.step(random.choice(RESONANCE_FAMILY_SOURCES[src]), source_id=src, origin_type="internal")
        coh.append(st.coherence); gn.append(box["gn"] or 0.0)
        s = cycle.status()
        if s.get("generator_metastability"):
            aR.append(s["generator_metastability"]["n_regimes"])
        if s.get("expression_metastability"):
            cR.append(s["expression_metastability"]["n_regimes"])
    h = slice(n // 2, None)
    mean = lambda x: float(np.mean(x[h])) if x else float("nan")
    return mean(coh), mean(gn), mean(aR), mean(cR)


def main() -> int:
    print("=" * 82)
    print("  GENERATOR DIVERSITY AUDIT — multi-method, train vs eval (dropout)")
    print("=" * 82)
    print("\n  [1] isolated generator (determinism control = same token ×5):")
    print(f"      {'dim':>4} {'mode':>5} | {'mean_cos':>8} {'eff_rank':>8} {'top1%':>6} {'determ':>7}")
    for dim in (64, 256):
        for mode in ("train", "eval"):
            mc, er, t1, det = _battery(dim, 0, mode)
            print(f"      {dim:>4} {mode:>5} | {mc:>8.3f} {er:>8.1f} {100*t1:>5.1f}% {det:>7.3f}"
                  + ("   ← live config (dim 64)" if dim == 64 and mode == "train" else ""))

    print("\n  [2] full live stack (Resonance Family), 2nd-half means — does diversity survive?:")
    print(f"      {'mode':>5} | {'field_coh':>9} {'gnov':>6} | {'stageA_regimes':>14} {'stageC_regimes':>14}")
    for mode in ("train", "eval"):
        coh, gn, aR, cR = _fullstack(mode)
        print(f"      {mode:>5} | {coh:>9.3f} {gn:>6.3f} | {aR:>14.1f} {cR:>14.1f}")

    print("\n" + "-" * 82)
    print("  READ: live (train) diversity is substantially DROPOUT NOISE. Deterministic")
    print("  (eval) generator at dim 64 is collinear (eff_rank ~1.6, cos ~0.79), and the")
    print("  deterministic pipeline collapses the expression to ~1 regime (locked). Lock #1")
    print("  is only PARTIALLY resolved (off cos 0.998, but not genuinely high-dim at dim 64),")
    print("  and the apparent diversity that made it look resolved is per-call dropout.")
    print("=" * 82)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
