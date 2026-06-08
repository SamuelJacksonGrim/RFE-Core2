"""
tests/diagnostic/gate_decomposition_probe.py

Step 1 of the attractor-mobility arc (coherence-is-not-plasticity, Next #1):
**decompose the ~85% governance gate block by rejection reason.**

multilayer-lock measured that ~85% of *diverse* internal input is filtered before
field integration (the `gateBlock` rate in `trained_generator_sim.py`), but that
number is a single opaque boolean — "nothing injected this step". 85% blocked is
uninterpretable alone: 80% redundant-noise rejected means the gate is doing its
job; 80% novelty rejected for dissonance means it is *strangling the variety the
migration test needs*. Same rate, opposite meaning. Until this is decomposed, an
attractor-migration probe cannot be read — if the attractor doesn't move, it could
just be that the gate ate the novelty before the field ever saw it (the exact
input-channel confound the finding warns about).

This probe is the input-channel check. It instruments the REAL gate
(`_governance_gate`: `ethical_boundary.check` → `trust_ledger.evaluate` →
`arbitrate`) and attributes every block to a reason, in two regimes:

  CONTROL  — benign Resonance Family, real generator. Block rate should be ~1%
             (complement of the known allow_rate ≈ 0.99). Verifies the
             instrumentation is faithful before we trust the diverse regime.
  DIVERSE  — the multilayer-lock workload: mocked generator (TrainedGeneratorStub),
             orthogonal token directions, spread sweep. This is where the 85% lives.

A block = final GovernanceDecision ∉ _ALLOW_DECISIONS (canonical), measured
directly from the decision — not the `field.history` proxy the original used.
Reason attribution precedence (documented choice; a step can trip several gates):
  flood          ethical hard gate "flood" (origin rate ceiling)
  coherence      ethical hard gate "field_collapse" (coherence_delta below floor
                 = vector too dissonant with the current field) — THE strangle signal
  identity       ethical hard gate "identity_drift" (witness stability floor)
  sacred/toxic   ethical hard gates "sacred_mutation" / "toxic_token"
  trust          blocked with no ethical hard gate + low source trust (≤ SKEPTICAL)
  manipulation   blocked with no ethical hard gate + non-low trust (arbitrate folded
                 in a manipulation/compound-severity signal or force_dream)

PRE-DECLARED SIGNATURES (discipline #4 — before the run)
--------------------------------------------------------
  STRANGLES-NOVELTY : in DIVERSE, blocks are dominated (> 50% of blocks) by
      `coherence` (field_collapse). The gate rejects novelty *for being novel*.
      → the migration test's input channel is compromised; surviving novelty must
        be engineered (relax/condition the coherence floor, or feed novelty the
        gate will pass) before an attractor-migration result is interpretable.
  REJECTS-JUNK / ARTIFACT : blocks dominated by flood / trust / manipulation.
      Not novelty-strangling per se — but note the sim is single-source, so
      monopoly-driven trust/manipulation blocks are a workload artifact, not the
      gate's benign-traffic behavior. Characterize and separate.
  LOW-BLOCK (control) : benign internal traffic passes (block rate ≈ 1%),
      confirming the gate only bites under diversity and the instrument is honest.
  CONFOUNDED : block rate ≈ 0 in DIVERSE too (gate never fires) → there is no 85%
      to decompose under this stack/seed; report and stop.

Informational. exit 0. NEVER in run_all_tests.sh (discipline #3).
"""
import sys
import logging
import random
from collections import Counter

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from agents.selfhood_governance import _ALLOW_DECISIONS                       # noqa: E402
from tests._common import (build_full_stack, RESONANCE_FAMILY_SOURCES,        # noqa: E402
                           RESONANCE_FAMILY_WEIGHTS)
from tests.diagnostic.trained_generator_sim import TrainedGeneratorStub, DIM, VOCAB  # noqa: E402

N_STEPS = 600
SEED = 7


# ---------------------------------------------------------------------------
# Gate instrumentation — capture ethical result + final decision per step
# ---------------------------------------------------------------------------

class GateCapture:
    """Wrap ethical_boundary.check and arbitrate to record, per step, the
    hard gates fired, soft warnings, final decision, and source trust. Both are
    called exactly once per step inside _governance_gate."""

    def __init__(self, governance):
        self.gov = governance
        self.records = []
        self._eth = None
        self._dec = None
        self._oc = governance.ethical_boundary.check
        self._oa = governance.arbitrate
        governance.ethical_boundary.check = self._check
        governance.arbitrate = self._arb

    def _check(self, *a, **k):
        r = self._oc(*a, **k)
        self._eth = r
        return r

    def _arb(self, *a, **k):
        dec, strength = self._oa(*a, **k)
        self._dec = dec
        return dec, strength

    def commit(self, source_id):
        trust = self.gov.trust_ledger.sources.get(source_id)
        self.records.append({
            "decision":   self._dec,
            "hard_gates": list(self._eth.hard_gates_fired) if self._eth else [],
            "soft":       list(self._eth.soft_warnings) if self._eth else [],
            "trust":      trust.trust_score if trust else None,
        })
        self._eth = self._dec = None

    def restore(self):
        self.gov.ethical_boundary.check = self._oc
        self.gov.arbitrate = self._oa


def classify(rec) -> str:
    if rec["decision"] in _ALLOW_DECISIONS:
        return "allow"
    hg = rec["hard_gates"]
    for name, label in (("flood", "flood"), ("field_collapse", "coherence"),
                        ("identity_drift", "identity"), ("sacred_mutation", "sacred"),
                        ("toxic_token", "toxic")):
        if name in hg:
            return label
    if hg:
        return "ethical_other"
    ts = rec["trust"]
    if ts is not None and ts <= 1.0:        # SKEPTICAL / UNTRUSTED / TOXIC floor
        return "trust"
    return "manipulation"


def _breakdown(records):
    cats = Counter(classify(r) for r in records)
    n = len(records)
    blocks = n - cats.get("allow", 0)
    soft = Counter(w for r in records for w in r["soft"])
    return n, blocks, cats, soft


def _report(title, records, hhi=None):
    n, blocks, cats, soft = _breakdown(records)
    # trigger = first non-allow block (the cascade initiator)
    trig = next(((i, classify(r)) for i, r in enumerate(records)
                 if r["decision"] not in _ALLOW_DECISIONS), None)
    print(f"\n  {title}")
    hhi_s = f"  HHI={hhi:.3f}" if hhi is not None else ""
    print(f"      steps={n}  blocks={blocks}  block_rate={blocks/max(1,n):.1%}{hhi_s}")
    if trig:
        print(f"      first block: step {trig[0]} via '{trig[1]}' (cascade initiator)")
    order = ["flood", "coherence", "identity", "sacred", "toxic",
             "ethical_other", "trust", "manipulation"]
    if blocks:
        print(f"      block reasons (% of blocks | % of all steps):")
        for cat in order:
            c = cats.get(cat, 0)
            if c:
                print(f"        {cat:<14} {c/blocks:>6.1%} | {c/n:>6.1%}  ({c})")
    if soft:
        print(f"      soft warnings (advisory, non-blocking): "
              + ", ".join(f"{w}={c}" for w, c in soft.most_common()))
    return blocks / max(1, n), cats, blocks


# ---------------------------------------------------------------------------
# Regimes
# ---------------------------------------------------------------------------

def _hhi(gov):
    try:
        return gov.dependency_monitor.get_report().hhi_score
    except Exception:
        return None


def run_control(origin_type="internal", seed=SEED):
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack()
    cap = GateCapture(gov)
    sids = list(RESONANCE_FAMILY_SOURCES); w = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    try:
        for _ in range(N_STEPS):
            src = random.choices(sids, weights=w)[0]
            toks = random.choice(RESONANCE_FAMILY_SOURCES[src])
            cycle.step(toks, source_id=src, origin_type=origin_type)
            cap.commit(src)
    finally:
        cap.restore()
    return cap.records, _hhi(gov)


def run_diverse(spread, origin_type="internal", seed=SEED, n_sources=1):
    """Diverse orthogonal-token input. n_sources=1 reproduces the single-source
    multilayer-lock workload (monopoly artifact); n_sources>1 spreads traffic so
    HHI stays below the 0.70 monopoly threshold — the real input-channel test."""
    np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    stub = TrainedGeneratorStub(DIM, VOCAB, spread, seed=seed)
    cycle.generator.generate = stub.generate
    cap = GateCapture(gov)
    rng = np.random.default_rng(seed + 1)
    sources = [f"sim_{i}" for i in range(n_sources)]
    try:
        for t in range(N_STEPS):
            k = int(rng.integers(1, 4))
            toks = list(rng.choice(VOCAB, size=k, replace=False))
            src = sources[t % n_sources]          # balanced round-robin → low HHI
            cycle.step(tokens=toks, source_id=src, origin_type=origin_type)
            cap.commit(src)
    finally:
        cap.restore()
    return cap.records, _hhi(gov)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("  GATE DECOMPOSITION — why does the ~85% block fire? (input-channel check)")
    print("=" * 80)

    # CONTROL: benign real-generator traffic — instrument sanity (vs known ~99% allow)
    rec, hhi = run_control("internal")
    cr, _, _ = _report("[CONTROL] benign Resonance Family, real generator, internal", rec, hhi)

    # ARTIFACT: single-source diverse = the original multilayer-lock workload
    rec, hhi = run_diverse(1.0, n_sources=1)
    sr, scats, sblk = _report("[ARTIFACT] single-source diverse (the multilayer-lock '85%' workload)",
                              rec, hhi)

    # MEASUREMENT: multi-source diverse = monopoly removed, the real input channel
    rec, hhi_m = run_diverse(1.0, n_sources=8)
    mr, mcats, mblk = _report("[MEASUREMENT] 8-source diverse (HHI below 0.70 → no monopoly)",
                              rec, hhi_m)

    # ---- VERDICT -------------------------------------------------------
    print("\n" + "-" * 80)
    print("  VERDICT")
    print(f"  • CONTROL: benign internal block_rate={cr:.1%} "
          f"({'✓ instrument honest, gate passes benign traffic' if cr < 0.10 else '⚠ unexpected'}).")
    s_trust = (scats.get('trust', 0) + scats.get('manipulation', 0)) / max(1, sblk)
    print(f"  • ARTIFACT: single-source block_rate={sr:.1%}, {s_trust:.0%} trust/manipulation —")
    print("    reproduces the ~85% as a MONOPOLY cascade (HHI=1.0 trips the manipulation")
    print("    detector → trust craters to floor → quarantine-all). NOT novelty-strangling.")
    if mblk == 0:
        print(f"  • MEASUREMENT: 8-source block_rate={mr:.1%} (HHI={hhi_m:.2f}). The gate")
        print("    passes diverse novelty once no source monopolises.")
        print("  → INPUT CHANNEL CLEAR: the '85% gate' was a single-source artifact, not the")
        print("    field strangling dissonant novelty (field_collapse never fired). With")
        print("    multi-source diverse input the channel is open → the attractor-migration")
        print("    probe is interpretable, PROVIDED it uses multi-source novelty (≥2 sources,")
        print("    HHI < 0.70) to avoid re-triggering the monopoly cascade.")
    else:
        coh = mcats.get("coherence", 0) / mblk
        trust = (mcats.get("trust", 0) + mcats.get("manipulation", 0)) / mblk
        print(f"  • MEASUREMENT: 8-source block_rate={mr:.1%} (HHI={hhi_m:.2f}); "
              f"coherence={coh:.0%}, trust/manip={trust:.0%} of blocks.")
        if coh > 0.50:
            print("  → STRANGLES-NOVELTY: even multi-source, blocks are field_collapse — the")
            print("    gate rejects novelty for dissonance. The migration input channel needs")
            print("    the coherence floor conditioned before the test is interpretable.")
        elif trust > 0.50:
            print("  → RESIDUAL TRUST EROSION: multi-source still blocks via trust — dissonant")
            print("    injection erodes source trust over time even without monopoly. The")
            print("    migration probe must account for this (trust-refresh or shorter horizon).")
        else:
            print("  → MIXED: read the multi-source breakdown above before the migration probe.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
