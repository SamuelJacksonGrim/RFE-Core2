"""
tools/ignition/cm_check.py — identifiability test for field coherence (Cm).

Is ResonanceField.internal_coherence a real read of internal organization, or a
saturated angular statistic that mostly reflects "the field tracks its own recent
inputs"? Inject an ALIGNED stream vs an ORTHOGONAL stream and compare Cm against a
full-range ground-truth separability metric (mean pairwise cosine of injections).

    python -m tools.ignition.cm_check

If Cm barely moves while the pairwise cosine swings fully, Cm is (operationally)
non-identifying — use the separability metric instead. See
docs/findings/2026-06-15-cm-identifiability.md.
"""
from __future__ import annotations

import sys
sys.path.insert(0, ".")

import numpy as np
from substrate.resonance_field import ResonanceField


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def run(mode: str, dim: int = 128, n: int = 80, seed: int = 0):
    rng = np.random.default_rng(seed)
    field = ResonanceField(dim=dim)
    d = _unit(rng.standard_normal(dim))         # the aligned direction
    injected, cohs = [], []
    for _ in range(n):
        v = (_unit(d + 0.08 * rng.standard_normal(dim)) if mode == "aligned"
             else _unit(rng.standard_normal(dim)))
        field.inject(v)
        field.decay()
        injected.append(v)
        cohs.append(field.observe().internal_coherence)

    last = np.array(injected[-32:])
    gram = last @ last.T
    iu = np.triu_indices(len(last), 1)
    mean_pair_cos = float(gram[iu].mean())       # ground-truth separability, full [-1,1]
    s = np.linalg.svd(last, compute_uv=False)
    p = s / s.sum()
    eff_rank = float(np.exp(-(p * np.log(p + 1e-12)).sum()))
    return float(np.mean(cohs[-25:])), mean_pair_cos, eff_rank


def main() -> int:
    print(f"{'regime':11}| field Cm | TRUE mean pairwise cos | eff_rank")
    out = {}
    for mode in ("aligned", "orthogonal"):
        out[mode] = run(mode)
        cm, mpc, er = out[mode]
        print(f"{mode:11}|  {cm:.3f}  |        {mpc:+.3f}          |  {er:.1f}")
    d_cm  = abs(out["aligned"][0] - out["orthogonal"][0])
    d_mpc = abs(out["aligned"][1] - out["orthogonal"][1])
    print(f"\n  Cm swing = {d_cm:.3f}   ground-truth swing = {d_mpc:.3f}")
    print(f"  => Cm compresses a {d_mpc:.2f} structural change into {d_cm:.2f}; floor ~0.87 even orthogonal.")
    print(f"     Operationally non-identifying in RFE's aligned regime; prefer pairwise-cos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
