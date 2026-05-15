#!/usr/bin/env bash
#
# run_all_tests.sh — Run every pass/fail test in tests/ and report results.
#
# Skips tests/diagnostic/ since those are informational, not pass/fail.
# Exits 0 if all tests pass, non-zero if any fail.
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

declare -a passed
declare -a failed

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

echo
echo -e "${BOLD}INTEGRATION TESTS${RESET}"
run_test "tests.integration.tier1_revision_baseline"
run_test "tests.integration.governance_decision_flow"
run_test "tests.integration.core_promotion_handshake"

echo
echo -e "${BOLD}ADVERSARIAL PROBES${RESET}"
run_test "tests.adversarial.sacred_shield"
run_test "tests.adversarial.flood_calibration"
run_test "tests.adversarial.manipulation_cascade"
run_test "tests.adversarial.identity_drift"

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
echo "Diagnostic tools are informational (not run by this script). To run them:"
echo "  python3 -m tests.diagnostic.decision_histogram"
echo "  python3 -m tests.diagnostic.gate_firing_audit"
echo "  python3 -m tests.diagnostic.trust_trajectory"
echo "  python3 -m tests.diagnostic.value_polarity_flow"

exit 0
