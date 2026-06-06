"""
tests/diagnostic/trained_generator_sim.py

Does the live field escape the 0.998 pin if the generator stops being a
one-dimensional projector?

lockin_source.py proved the live lock is UPSTREAM: the untrained Generator maps
near-everything to ~one direction (cos ~0.998), so the field's input is
effectively 1-D regardless of tokens. It did NOT prove the field dynamics can or
cannot hold low coherence GIVEN diverse input — it only tested a single novel
injection (absorbed by the magnitude moat).

This diagnostic substitutes the ONE unready component — the generator — with a
stand-in that has a trained generator's key property (same token -> same
direction, distinct tokens -> distinct directions, real spread), then runs the
FULL LIVE STEP LOOP on top: governance gate, coherence_impact probe, injection,
emit_feedback, crystallization, reaper, decay, emotional gradient. Only the
generator is mocked; everything downstream is real.

PRE-DECLARED READS (discipline #4 — state both before the run)
--------------------------------------------------------------
  GENERATOR-IS-THE-LOCK (field dynamics healthy):
      under diverse input the field DROPS off the ~0.998 pin and occupies a
      lower / variable coherence band; monitor reads metastable|cycling|
      dissolving rather than locked. => training the generator unlocks it; no
      field-side fix needed for THIS lock.
  SECOND-LOCKER (magnitude moat is independently rigid):
      field STILL pins ~0.99+ even under maximal diverse input; monitor still
      reads locked. => accumulate-decay moat is a second, generator-independent
      lock; Fix 2 (paper-boat, field-side) has a real job.

ASYMMETRY (read honestly): random orthogonal vectors are MAXIMAL diversity —
more spread than a real trained generator (which clusters semantically-near
concepts). So:
  - STILL-LOCKED under max diversity = STRONG evidence of a second locker.
  - ESCAPES under max diversity = necessary but NOT sufficient (best case; a
    real clustered generator might still partially lock).

Informational. exit 0. NEVER in run_all_tests.sh (discipline #3).
"""
import sys
import logging
import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack                       # noqa: E402
from cognition.stream_metastability import StreamMetastabilityMonitor  # noqa: E402

DIM = 64
N_STEPS = 600
VOCAB = [f"sym_{i:02d}" for i in range(40)]   # 40 distinct concepts


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


class TrainedGeneratorStub:
    """Deterministic token->direction map = a trained generator's key property.

    `spread` in [0,1] interpolates between the UNTRAINED regime (all tokens ->
    ~one direction, reproducing lockin_source.py's ~0.998) and a fully TRAINED
    regime (each token its own orthogonal-ish direction). Lets us sweep the
    SAME live stack from 1-D projector to diverse generator and watch the field.
    """
    def __init__(self, dim, vocab, spread, seed=7):
        rng = np.random.default_rng(seed)
        shared = _unit(rng.standard_normal(dim))           # the untrained axis
        self._map = {}
        for tok in vocab:
            own = _unit(rng.standard_normal(dim))           # token's own direction
            v = spread * own + (1.0 - spread) * shared
            self._map[tok] = _unit(v)
        self._shared = shared
        self.dim = dim

    def generate(self, tokens, token_class=None):
        if not tokens:
            return self._shared.copy()
        # mean of token directions (matches "encode a sequence -> one vector")
        vs = [self._map.get(t, self._shared) for t in tokens]
        return _unit(np.mean(vs, axis=0))


def run_at_spread(spread, n_steps=N_STEPS, seed=7):
    generator, cycle, governance, value_engine = build_full_stack(dim=DIM)
    field = cycle.field

    # Substitute ONLY the generator's output mapping; keep its registry/maintenance
    stub = TrainedGeneratorStub(DIM, VOCAB, spread, seed=seed)
    cycle.generator.generate = stub.generate   # the one mock; all else live

    rng = np.random.default_rng(seed + 1)
    mon = StreamMetastabilityMonitor(window=96, interval=16, min_samples=16)

    coh_series, gate_blocks, injected_dirs = [], 0, []
    for _ in range(n_steps):
        # diverse token sequences: vary length + membership each step
        k = int(rng.integers(1, 4))
        toks = list(rng.choice(VOCAB, size=k, replace=False))
        try:
            before = len(field.history)
            cycle.step(tokens=toks, source_id="sim", origin_type="internal")
            after = len(field.history)
            if after == before:        # nothing injected => gate blocked it
                gate_blocks += 1
            elif len(field.history) > 0:
                injected_dirs.append(np.asarray(field.history[-1]))
                mon.observe(np.asarray(field.history[-1]))
        except Exception as e:
            print(f"  [step error @ spread={spread}: {type(e).__name__}: {e}]")
            break
        coh_series.append(field._phase_coherence())

    coh = np.array(coh_series)
    rep = mon.compute_now()

    # input-diversity sanity: mean pairwise cosine of what actually hit the field
    if len(injected_dirs) >= 2:
        U = [_unit(v) for v in injected_dirs[-96:]]
        sims = [float(np.dot(U[i], U[j]))
                for i in range(len(U)) for j in range(i + 1, min(i + 8, len(U)))]
        input_cos = float(np.mean(sims)) if sims else float("nan")
    else:
        input_cos = float("nan")

    return {
        "spread": spread,
        "coh_mean": float(coh.mean()),
        "coh_std": float(coh.std()),
        "coh_min": float(coh.min()),
        "coh_last": float(coh[-1]),
        "regime": rep.regime_state,
        "metastability": rep.metastability,
        "gate_block_rate": gate_blocks / max(1, n_steps),
        "input_cos": input_cos,
    }


def main():
    print("=" * 78)
    print("  TRAINED-GENERATOR SIM — does the field escape the pin under diverse input?")
    print("=" * 78)
    print("  spread 0.0 = untrained 1-D projector (should reproduce ~0.998 lock)")
    print("  spread 1.0 = fully diverse generator (each token its own direction)")
    print("  PRE-DECLARED: escapes pin+monitor!=locked => generator IS the lock;")
    print("                still ~0.99 locked under max spread => 2nd moat-locker.")
    print("-" * 78)
    print(f"  {'spread':>6} | {'inputCos':>8} | {'cohMean':>7} {'cohStd':>6} "
          f"{'cohMin':>6} {'cohLast':>7} | {'regime':<13} | {'meta':>5} | {'gateBlk':>7}")
    print("-" * 78)

    results = []
    for spread in [0.0, 0.25, 0.5, 0.75, 1.0]:
        r = run_at_spread(spread)
        results.append(r)
        print(f"  {r['spread']:>6.2f} | {r['input_cos']:>8.3f} | "
              f"{r['coh_mean']:>7.3f} {r['coh_std']:>6.3f} {r['coh_min']:>6.3f} "
              f"{r['coh_last']:>7.3f} | {r['regime']:<13} | "
              f"{r['metastability']:>5.2f} | {r['gate_block_rate']:>7.2%}")

    print("-" * 78)
    # sanity: spread 0 should reproduce the known lock
    r0 = results[0]
    r1 = results[-1]
    print("SANITY (spread 0.0): expect high coherence + locked (matches lockin_source.py)")
    print(f"   -> coh_mean={r0['coh_mean']:.3f}, regime={r0['regime']}, "
          f"inputCos={r0['input_cos']:.3f}  "
          f"{'OK' if r0['coh_mean'] > 0.9 else 'UNEXPECTED — stub not reproducing lock'}")
    print()
    print("VERDICT (spread 1.0, max diversity):")
    escaped = r1["coh_mean"] < 0.9 or r1["regime"] != "locked"
    if escaped:
        print(f"   field MOVED OFF pin (coh_mean={r1['coh_mean']:.3f}, "
              f"regime={r1['regime']}, meta={r1['metastability']:.2f}).")
        print("   => GENERATOR IS THE LOCK. Field dynamics hold variety; training")
        print("      the generator would unlock metastability. (Necessary, not")
        print("      sufficient — real clustered generator may differ.)")
    else:
        print(f"   field STILL LOCKED (coh_mean={r1['coh_mean']:.3f}, "
              f"regime={r1['regime']}) under MAX diversity (inputCos={r1['input_cos']:.3f}).")
        print("   => STRONG evidence of a SECOND, generator-independent locker:")
        print("      the accumulate-decay magnitude moat. Fix 2 (paper-boat) has")
        print("      a real, field-side job that generator training will NOT fix.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
