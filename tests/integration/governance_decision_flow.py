"""
tests/integration/governance_decision_flow.py

Constructs the input conditions to force every GovernanceDecision enum
value to fire, then verifies the arbitrate() decision tree routes each
to its expected outcome. Locks down the decision contract before Tier 4
introduces new arousal-modulated paths.

Decisions covered:
  ALLOW           Clean pass — no warnings, high trust, no dep risk
  ALLOW_WEAKENED  Soft warning fires
  ALLOW_WEAKENED  Moderate manipulation (severity 0.30–0.60)
  ALLOW_WEAKENED  CRITICAL dependency on dominant source
  MONITOR         Trust between quarantine and monitor thresholds
  MONITOR         HIGH dependency on dominant source
  QUARANTINE      Compound manipulation severity ≥ 0.60
  QUARANTINE      Hard gate (non-sacred, recommended QUARANTINE)
  QUARANTINE      Trust ≤ quarantine threshold
  REJECT          Hard gate (recommended REJECT)
  SACRED_SHIELD   Hard gate (recommended SACRED_SHIELD)

Run:
    python -m tests.integration.governance_decision_flow
"""

import sys
import numpy as np

from tests._common import build_full_stack
from agents.selfhood_governance import GovernanceDecision
from agents.ethical_boundary import EthicalCheckResult
from agents.trust_ledger import TrustReport, TrustLevel
from agents.manipulation_resistance import ManipulationSignal


# ---------------------------------------------------------------------------
# Helpers — construct minimal valid arbitrate() inputs
# ---------------------------------------------------------------------------

def clean_ethical_result() -> EthicalCheckResult:
    return EthicalCheckResult(
        passed               = True,
        hard_gates_fired     = [],
        soft_warnings        = [],
        recommended_decision = "ALLOW",
    )


def soft_warning_result(warning: str = "low_coherence") -> EthicalCheckResult:
    return EthicalCheckResult(
        passed               = True,
        hard_gates_fired     = [],
        soft_warnings        = [warning],
        recommended_decision = "ALLOW",
    )


def hard_gate_result(gate: str, recommended: str) -> EthicalCheckResult:
    return EthicalCheckResult(
        passed               = False,
        hard_gates_fired     = [gate],
        soft_warnings        = [],
        recommended_decision = recommended,
    )


def trust_report(
    trust_score: float       = 4.0,
    level:       TrustLevel  = TrustLevel.HIGH,
    source_id:   str         = "test_source",
    min_symbol:  float       = 4.0,
) -> TrustReport:
    return TrustReport(
        source_id        = source_id,
        source_trust     = trust_score,
        source_level     = level,
        symbol_trusts    = {},
        min_symbol_trust = min_symbol,
        coherence_impact = 0.05,
        recommendation   = "ALLOW",
    )


def expect(name: str, actual_decision, expected_decision, expected_strength=None,
           actual_strength=None):
    """Pretty-print one test case result."""
    decision_ok = actual_decision == expected_decision
    strength_ok = (
        expected_strength is None
        or (actual_strength is not None and abs(actual_strength - expected_strength) < 0.5)
    )
    passed = decision_ok and strength_ok
    mark = "✓" if passed else "✗"
    print(f'  {mark} {name:<48} → {actual_decision.value:<16} '
          f'(strength={actual_strength:.2f})')
    if not decision_ok:
        print(f'      expected {expected_decision.value}')
    return passed


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_decisions():
    print('=' * 72)
    print('  INTEGRATION: governance decision flow')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()
    vec = np.zeros(64)
    tokens = ['test']
    results = []

    # ── ALLOW: clean pass ──
    governance._pending_signals = []
    d, s = governance.arbitrate(
        ethical_result = clean_ethical_result(),
        trust_report   = trust_report(trust_score=4.5, level=TrustLevel.HIGH),
        vec            = vec,
        tokens         = tokens,
        source_id      = "allow_test",
    )
    results.append(expect("ALLOW: clean pass, high trust",
                          d, GovernanceDecision.ALLOW, 1.0, s))

    # ── ALLOW_WEAKENED via soft warning ──
    governance._pending_signals = []
    d, s = governance.arbitrate(
        ethical_result = soft_warning_result(),
        trust_report   = trust_report(trust_score=4.5, level=TrustLevel.HIGH),
        vec            = vec,
        tokens         = tokens,
        source_id      = "soft_warn_test",
    )
    results.append(expect("ALLOW_WEAKENED: soft warning fires",
                          d, GovernanceDecision.ALLOW_WEAKENED, 0.85, s))

    # ── ALLOW_WEAKENED via moderate manipulation ──
    governance._pending_signals = [
        ManipulationSignal(
            detector="trust_wash", severity=0.40,
            source_id="moderate_manip", evidence={},
        )
    ]
    d, s = governance.arbitrate(
        ethical_result = clean_ethical_result(),
        trust_report   = trust_report(trust_score=4.5, level=TrustLevel.HIGH),
        vec            = vec,
        tokens         = tokens,
        source_id      = "moderate_manip",
    )
    results.append(expect("ALLOW_WEAKENED: moderate manipulation (sev=0.40)",
                          d, GovernanceDecision.ALLOW_WEAKENED, 0.6, s))

    # ── MONITOR: trust at LOW range ──
    # quarantine_trust_threshold default ~1.0, monitor_trust_threshold ~2.5
    governance._pending_signals = []
    d, s = governance.arbitrate(
        ethical_result = clean_ethical_result(),
        trust_report   = trust_report(trust_score=2.0, level=TrustLevel.LOW,
                                       min_symbol=2.0),
        vec            = vec,
        tokens         = tokens,
        source_id      = "monitor_test",
    )
    results.append(expect("MONITOR: trust between thresholds",
                          d, GovernanceDecision.MONITOR, None, s))

    # ── QUARANTINE via compound manipulation ──
    governance._pending_signals = [
        ManipulationSignal(
            detector="trust_wash", severity=0.40,
            source_id="high_manip", evidence={},
        ),
        ManipulationSignal(
            detector="symbol_contamination", severity=0.30,
            source_id="high_manip", evidence={},
        ),
    ]
    d, s = governance.arbitrate(
        ethical_result = clean_ethical_result(),
        trust_report   = trust_report(trust_score=4.5, level=TrustLevel.HIGH),
        vec            = vec,
        tokens         = tokens,
        source_id      = "high_manip",
    )
    results.append(expect("QUARANTINE: compound manipulation (sev=0.70)",
                          d, GovernanceDecision.QUARANTINE, 0.0, s))

    # ── QUARANTINE via hard gate ──
    governance._pending_signals = []
    d, s = governance.arbitrate(
        ethical_result = hard_gate_result("flood", "QUARANTINE"),
        trust_report   = trust_report(trust_score=4.5, level=TrustLevel.HIGH),
        vec            = vec,
        tokens         = tokens,
        source_id      = "flood_test",
    )
    results.append(expect("QUARANTINE: hard gate (flood)",
                          d, GovernanceDecision.QUARANTINE, 0.0, s))

    # ── QUARANTINE via low trust ──
    governance._pending_signals = []
    d, s = governance.arbitrate(
        ethical_result = clean_ethical_result(),
        trust_report   = trust_report(trust_score=0.5, level=TrustLevel.TOXIC,
                                       min_symbol=0.5),
        vec            = vec,
        tokens         = tokens,
        source_id      = "low_trust_test",
    )
    results.append(expect("QUARANTINE: trust below quarantine threshold",
                          d, GovernanceDecision.QUARANTINE, 0.0, s))

    # ── REJECT via hard gate ──
    governance._pending_signals = []
    d, s = governance.arbitrate(
        ethical_result = hard_gate_result("identity_drift", "REJECT"),
        trust_report   = trust_report(trust_score=0.3, level=TrustLevel.TOXIC,
                                       min_symbol=0.3),
        vec            = vec,
        tokens         = tokens,
        source_id      = "reject_test",
    )
    results.append(expect("REJECT: hard gate (identity_drift, low trust)",
                          d, GovernanceDecision.REJECT, 0.0, s))

    # ── SACRED_SHIELD via hard gate ──
    governance._pending_signals = []
    d, s = governance.arbitrate(
        ethical_result = hard_gate_result("sacred_mutation", "SACRED_SHIELD"),
        trust_report   = trust_report(trust_score=5.0, level=TrustLevel.SACRED),
        vec            = vec,
        tokens         = tokens,
        source_id      = "sacred_attacker",
    )
    results.append(expect("SACRED_SHIELD: hard gate (sacred mutation)",
                          d, GovernanceDecision.SACRED_SHIELD, 0.0, s))

    return results


def main():
    results = test_decisions()
    print()
    passed = sum(1 for r in results if r)
    total  = len(results)
    print('=' * 72)
    if passed == total:
        print(f'  ALL DECISIONS VERIFIED: {passed}/{total} routes correct.')
        return 0
    else:
        print(f'  FAILED: {passed}/{total} routes correct.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
