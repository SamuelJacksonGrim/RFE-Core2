#!/usr/bin/env bash
#
# run_all_tests.sh — Run every pass/fail test in tests/ and report results.
#
# Covers smoke, integration, adversarial, the Tier 4 physics validators
# (regression guards in tests/diagnostic/ that return real pass/fail exit
# codes), and documentation accuracy. Skips the purely informational
# diagnostics/probes (they always exit 0 and report rather than gate).
# Exits 0 only if all pass, non-zero if any fail.
#
# Run from repo root:
#   ./run_all_tests.sh
#   bash run_all_tests.sh
#
# Make executable (one time):
#   chmod +x run_all_tests.sh

set -u

# Move to script directory so paths resolve consistently
cd "$(dirname "$0")"

# Explicit empty-array assignment (not bare `declare -a`) so `${#failed[@]}`
# is safe under `set -u` even when no test has failed — a bare declare leaves
# the array unset on some bash builds and trips "unbound variable" on a clean run.
passed=()
failed=()

# Colors only if terminal supports them
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    GREEN=''
    RED=''
    BLUE=''
    BOLD=''
    RESET=''
fi

run_test() {
    local name="$1"
    echo
    echo -e "${BOLD}${BLUE}── $name ──${RESET}"
    if python3 -m "$name"; then
        passed+=("$name")
        echo -e "${GREEN}✓ PASSED${RESET}: $name"
    else
        failed+=("$name")
        echo -e "${RED}✗ FAILED${RESET}: $name"
    fi
}

echo -e "${BOLD}════════════════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  RFE-Core2 — Full Test Suite${RESET}"
echo -e "${BOLD}════════════════════════════════════════════════════════════════${RESET}"

echo
echo -e "${BOLD}SMOKE TESTS${RESET}"
run_test "tests.smoke.full_stack_minimal"
run_test "tests.smoke.single_source_100step"
run_test "tests.smoke.multi_source_500step"
run_test "tests.smoke.stream_recorder_smoke"

echo
echo -e "${BOLD}INTEGRATION TESTS${RESET}"
run_test "tests.integration.tier1_revision_baseline"
run_test "tests.integration.governance_decision_flow"
run_test "tests.integration.core_promotion_handshake"
run_test "tests.integration.checkpoint_registry_identity"
run_test "tests.integration.config_loading_neutrality"
run_test "tests.integration.bond_ddm_invariants"

echo
echo -e "${BOLD}ADVERSARIAL PROBES${RESET}"
run_test "tests.adversarial.sacred_shield"
run_test "tests.adversarial.flood_calibration"
run_test "tests.adversarial.manipulation_cascade"
run_test "tests.adversarial.identity_drift"

echo
echo -e "${BOLD}PHYSICS VALIDATORS (regression guards)${RESET}"
run_test "tests.diagnostic.tier4.dilation_response_curve"
run_test "tests.diagnostic.tier4.rhythm_dilation_curve"

echo
echo -e "${BOLD}CORPUS INTEGRITY${RESET}"
run_test "tests.diagnostic.training.corpus_integrity_check"

echo
echo -e "${BOLD}DOCUMENTATION ACCURACY${RESET}"
run_test "tests.doc_accuracy.verify_docs"

# Summary
echo
echo -e "${BOLD}════════════════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  SUMMARY${RESET}"
echo -e "${BOLD}════════════════════════════════════════════════════════════════${RESET}"
echo
echo -e "${GREEN}Passed: ${#passed[@]}${RESET}"
echo -e "${RED}Failed: ${#failed[@]}${RESET}"

if [ ${#failed[@]} -gt 0 ]; then
    echo
    echo "Failures:"
    for name in "${failed[@]}"; do
        echo "  ✗ $name"
    done
    exit 1
fi

echo
echo "Informational diagnostics (not gated — always exit 0; run manually):"
echo "  python3 -m tests.diagnostic.core_arc_no_cascade_probe   (minutes; 3 seeds × 1500 steps; exit-coded — F8 CORE arc + no-cascade)"
echo "  python3 -m tests.diagnostic.tier4.affective_state_probe 500"
echo "  python3 -m tests.diagnostic.tier4.rhythm_inertness_probe 500"
echo "  python3 -m tests.diagnostic.audit.decision_histogram"
echo "  python3 -m tests.diagnostic.audit.gate_firing_audit"
echo "  python3 -m tests.diagnostic.audit.trust_trajectory"
echo "  python3 -m tests.diagnostic.audit.value_polarity_flow"
echo "  python3 -m tests.diagnostic.training.corpus_pretrain_g1_probe 8   (minutes; trains)"
echo "  python3 -m tests.diagnostic.training.corpus_boot_phase2_probe 8 500   (minutes; trains + live stack)"
echo "  python3 -m tests.diagnostic.lockin.secondlocker_field_map_probe 500   (~45 min; 30-cell matrix, trains per seed)"

exit 0
