"""
tools/ignition/identifiability.py — do RFE's observables track structure, or
just geometry? (Cm vs I vs metastability, one controlled injection loop.)

GPT's refinement: the real question isn't "does the metric separate aligned from
orthogonal" — it's "does it track GEOMETRY, or CHANGE in geometry." So the battery
includes a clustered-but-rotated regime (low within-window dispersion, HIGH drift)
and a low-rank regime. A metric that only reads static geometry will miss the
rotation; one that reads change will catch it.

Ground-truth descriptors (treated as higher-fidelity PROXIES, not absolute truth,
per GPT): within-window mean pairwise cosine (dispersion) and half-to-half
centroid drift (change). Each of the three signals is then scored on whether it
moves with dispersion, with drift, or with neither.

    python -m tools.ignition.identifiability
"""
from __future__ import annotations

import sys
sys.path.insert(0, ".")

import numpy as np
from substrate.resonance_field import ResonanceField
from agents.watcher import Watcher
from cognition.stream_metastability import StreamMetastabilityMonitor

DIM, N = 128, 90


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def _stream(regime, rng, d, anchor):
    """Yield N unit vectors for the named regime."""
    if regime == "aligned":
        for _ in range(N):
            yield _unit(d + 0.08 * rng.standard_normal(DIM))
    elif regime == "orthogonal":
        for _ in range(N):
            yield _unit(rng.standard_normal(DIM))
    elif regime == "clustered_rotated":
        # tight cluster (low dispersion) whose center rotates across the run (high drift)
        basis = _unit(rng.standard_normal(DIM))
        for i in range(N):
            theta = 2.0 * np.pi * i / N
            center = _unit(np.cos(theta) * d + np.sin(theta) * basis)
            yield _unit(center + 0.04 * rng.standard_normal(DIM))
    elif regime == "low_rank":
        B = np.linalg.qr(rng.standard_normal((DIM, 3)))[0]      # 3-dim subspace
        for _ in range(N):
            yield _unit(B @ (rng.standard_normal(3) * np.array([1.0, 0.4, 0.15])))


def run(regime):
    rng = np.random.default_rng(0)
    d = _unit(rng.standard_normal(DIM))
    anchor = _unit(np.random.default_rng(99).standard_normal(DIM))   # fixed identity
    field = ResonanceField(dim=DIM)
    watcher = Watcher(dim=DIM, field=field)
    mon = StreamMetastabilityMonitor(window=128, interval=16)

    inj, cm, I = [], [], []
    for v in _stream(regime, rng, d, anchor):
        field.inject(v);
        I.append(float(watcher.evaluate(v, anchor, field.resonate()).composite))
        field.decay()
        mon.observe(v)
        cm.append(field.observe().internal_coherence)
        inj.append(v)

    arr = np.array(inj)
    last = arr[-32:]
    gram = last @ last.T
    iu = np.triu_indices(len(last), 1)
    dispersion = 1.0 - float(gram[iu].mean())              # 0 aligned .. 1 orthogonal
    h = len(arr) // 2
    c1, c2 = _unit(arr[:h].mean(0)), _unit(arr[h:].mean(0))
    drift = 1.0 - float(np.dot(c1, c2))                    # 0 static .. 2 reversed
    meta = mon.compute_now()
    return (float(np.mean(cm[-25:])), float(np.mean(I[-25:])),
            float(meta.metastability), meta.regime_state, dispersion, drift)


def main() -> int:
    print(f"{'regime':18}| Cm    | I     | meta  state        | disp(truth) drift(truth)")
    print("-" * 84)
    rows = {}
    for r in ("aligned", "orthogonal", "clustered_rotated", "low_rank"):
        cm, I, meta, st, disp, drift = rows[r] = run(r)
        print(f"{r:18}| {cm:.3f} | {I:.3f} | {meta:.3f} {st:12}| {disp:.3f}       {drift:.3f}")
    print("-" * 84)
    # geometry vs change: does the signal move when dispersion changes? when drift changes?
    def swing(idx, a, b):
        return abs(rows[a][idx] - rows[b][idx])
    print("  dispersion sensitivity (aligned↔orthogonal):"
          f"  Cm {swing(0,'aligned','orthogonal'):.2f}  I {swing(1,'aligned','orthogonal'):.2f}"
          f"  meta {swing(2,'aligned','orthogonal'):.2f}")
    print("  CHANGE sensitivity   (aligned↔clustered_rotated, ~same dispersion, big drift):"
          f"  Cm {swing(0,'aligned','clustered_rotated'):.2f}  I {swing(1,'aligned','clustered_rotated'):.2f}"
          f"  meta {swing(2,'aligned','clustered_rotated'):.2f}")
    print("\n  A signal that moves on CHANGE but not just dispersion is tracking dynamics,")
    print("  not static geometry. (Proxies, not ground truth — per GPT's caveat.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
