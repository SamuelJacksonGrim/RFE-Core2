"""
tests/doc_accuracy/verify_docs.py

Mechanical cross-checks between README.md / CLAUDE.md and the actual code.

The premise — surfaced after two README inaccuracies landed in main despite
careful review: documentation drift isn't a quality-of-attention problem,
it's a missing-protocol-step problem. The verification step never gets
queued in working memory unless a script forces it. This script forces it.

Each concrete claim in the docs (a threshold value, an enum member, a
directory listing, a default parameter) should be queryable — one
introspection or filesystem call away from being verifiable. If a claim
can't be queried, the doc is asserting something the code doesn't know,
and the script should at minimum flag it for human review.

Scope
-----
Greppable / introspectable claims are first-class:
  - File tree listings in README → verified against actual filesystem
  - Threshold defaults in classes → verified against __init__ defaults
  - Enum members → verified against actual Enum definitions
  - Sacred constants → verified against PHILOSOPHICAL_CONSTANTS dict
  - Rhythm energy bands → verified against ResonanceField.DEFAULT_THRESHOLDS
  - Watcher layer weights summing to 1.0 → verified against class defaults

Behavioral / prose claims are out of scope — by design. A claim like "bonds
form when X AND Y AND (P OR Q)" describes a code path, not a number. Those
need human review. The script does not pretend to verify them.

Exit codes
----------
  0  all checks passed
  1  one or more checks failed

Run
---
    python -m tests.doc_accuracy.verify_docs

Hooked into run_all_tests.sh as a "documentation accuracy" phase.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
README     = REPO_ROOT / "README.md"
CLAUDE_MD  = REPO_ROOT / "CLAUDE.md"
TESTS_DIR  = REPO_ROOT / "tests"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name:    str
    passed:  bool
    summary: str
    details: List[str]


def passed(name: str, summary: str) -> CheckResult:
    return CheckResult(name=name, passed=True, summary=summary, details=[])


def failed(name: str, summary: str, details: List[str]) -> CheckResult:
    return CheckResult(name=name, passed=False, summary=summary, details=details)


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


_README_TEXT    = _read(README)
_CLAUDE_MD_TEXT = _read(CLAUDE_MD)


# ===========================================================================
# CHECKS
# ===========================================================================

# ---------------------------------------------------------------------------
# 1. tests/* subdirectory trees in README match the actual filesystem.
#    This is the failure mode that put 'governance_decision_flow.py' and
#    'core_promotion_handshake.py' on the cutting room floor for weeks.
# ---------------------------------------------------------------------------

# README tree lines look like:
#     │   │   ├── governance_decision_flow.py   Every GovernanceDecision enum...
#     │   │   └── tier1_revision_baseline.py    Fresh run vs baseline JSON ranges
# Pull out the filename token (must end in .py).
_TREE_PY_FILE = re.compile(r"[├└─]──\s+([a-zA-Z_][a-zA-Z0-9_]*\.py)")


def _readme_listed_files_in_subdir(subdir_label: str) -> Optional[List[str]]:
    """
    Return the .py filenames the README lists under tests/<subdir_label>/,
    or None if the subdir section can't be located in the README.

    Parses the README's tests/ block, finds the line that opens the
    `<subdir_label>/` block, and collects .py filenames until the next
    same-or-shallower indented directory marker.
    """
    if not _README_TEXT:
        return None

    # Find the opening "├── <subdir_label>/" line
    open_re = re.compile(
        r"^[│ ]*├──\s+" + re.escape(subdir_label) + r"/\s*$",
        re.MULTILINE,
    )
    m = open_re.search(_README_TEXT)
    if not m:
        return None

    # Collect lines until the next sibling directory entry at the same level,
    # OR a closing of the tests block. Sibling = "│   ├── <name>/" — match
    # the leading column count of our opener to detect sibling depth.
    start = m.end()
    next_sibling = re.compile(r"^[│ ]*[├└]──\s+\S+/", re.MULTILINE)
    n = next_sibling.search(_README_TEXT, start)
    block = _README_TEXT[start : n.start() if n else len(_README_TEXT)]

    return _TREE_PY_FILE.findall(block)


def _actual_py_files(subdir: Path) -> List[str]:
    """List .py filenames in subdir, excluding __init__.py."""
    if not subdir.is_dir():
        return []
    return sorted(
        p.name for p in subdir.iterdir()
        if p.is_file() and p.suffix == ".py" and p.name != "__init__.py"
    )


def check_tests_tree_completeness() -> CheckResult:
    """
    For each tests/<subdir>/, every .py file on disk should appear in the
    README's project-structure tree.
    """
    name = "tests/* tree completeness"
    failures: List[str] = []

    for sub in ("smoke", "integration", "adversarial", "diagnostic"):
        listed = _readme_listed_files_in_subdir(sub)
        actual = _actual_py_files(TESTS_DIR / sub)
        if listed is None:
            failures.append(
                f"  README: could not locate the tests/{sub}/ block"
            )
            continue
        missing = sorted(set(actual) - set(listed))
        if missing:
            failures.append(
                f"  tests/{sub}/: README missing {missing} — "
                f"on disk: {actual}"
            )

    if failures:
        return failed(
            name,
            "README project-structure tree is missing files that exist on disk",
            failures,
        )
    return passed(name, "every .py in tests/* is listed in the README tree")


# ---------------------------------------------------------------------------
# 2. TrustLevel enum: docs and code agree on (member, value) pairs.
# ---------------------------------------------------------------------------

def check_trust_level_enum() -> CheckResult:
    name = "TrustLevel enum members + values"
    from agents.trust_ledger import TrustLevel

    failures: List[str] = []
    docs = (("CLAUDE.md", _CLAUDE_MD_TEXT), ("README.md", _README_TEXT))

    for level in TrustLevel:
        val_str = f"{level.value:.1f}"

        # Pass if AT LEAST ONE doc has the value within window of the name.
        # A doc that doesn't mention the name at all isn't a failure — only
        # one that mentions the name without the value near it would be, AND
        # only if no other doc satisfies the pairing.
        if not any(level.name in text for _, text in docs):
            failures.append(f"  TrustLevel.{level.name} not mentioned in either doc")
            continue

        ok = False
        for _, text in docs:
            if level.name in text:
                idx    = text.index(level.name)
                window = text[max(0, idx - 40) : idx + 80]
                if val_str in window:
                    ok = True
                    break
        if not ok:
            failures.append(
                f"  TrustLevel.{level.name} ({val_str}) appears in docs but value "
                f"{val_str} not found within window of any occurrence"
            )

    if failures:
        return failed(
            name,
            "TrustLevel enum values do not match doc text",
            failures,
        )
    return passed(name, "all TrustLevel members + values present in docs")


# ---------------------------------------------------------------------------
# 3. Philosophical constants: ANCHOR / RECURSION / HOMEOSTASIS in docs match
#    PHILOSOPHICAL_CONSTANTS dict.
# ---------------------------------------------------------------------------

def check_philosophical_constants() -> CheckResult:
    name = "Philosophical constants"
    from agents.governance_constants import PHILOSOPHICAL_CONSTANTS

    failures: List[str] = []
    for const_name, meta in PHILOSOPHICAL_CONSTANTS.items():
        token = meta["token"]
        for doc_name, text in (("README.md", _README_TEXT), ("CLAUDE.md", _CLAUDE_MD_TEXT)):
            if const_name not in text:
                failures.append(f"  {const_name} not mentioned in {doc_name}")
                continue
            # Within 80 chars after the name, expect the token.
            idx    = text.index(const_name)
            window = text[idx : idx + 200]
            if token not in window:
                failures.append(
                    f"  {const_name} in {doc_name} but token '{token}' "
                    f"not found in 200 chars after it"
                )

    if failures:
        return failed(
            name,
            "Philosophical constants don't match between docs and code",
            failures,
        )
    return passed(name, "ANCHOR / RECURSION / HOMEOSTASIS tokens match in both docs")


# ---------------------------------------------------------------------------
# 4. GovernanceDecision enum: every member appears in docs.
# ---------------------------------------------------------------------------

def check_governance_decision_enum() -> CheckResult:
    name = "GovernanceDecision enum coverage"
    from agents.selfhood_governance import GovernanceDecision

    failures: List[str] = []
    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT
    for member in GovernanceDecision:
        if member.name not in combined and member.value not in combined:
            failures.append(
                f"  GovernanceDecision.{member.name} ('{member.value}') "
                f"not mentioned in either doc"
            )

    if failures:
        return failed(
            name,
            "GovernanceDecision enum members missing from docs",
            failures,
        )
    return passed(name, "all GovernanceDecision members appear in docs")


# ---------------------------------------------------------------------------
# 5. ValuePolarity enum: every member appears in docs.
# ---------------------------------------------------------------------------

def check_value_polarity_enum() -> CheckResult:
    name = "ValuePolarity enum coverage"
    from agents.value_emergence import ValuePolarity

    failures: List[str] = []
    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT
    for member in ValuePolarity:
        if member.name not in combined and member.value not in combined:
            failures.append(f"  ValuePolarity.{member.name} not mentioned in either doc")

    if failures:
        return failed(name, "ValuePolarity members missing from docs", failures)
    return passed(name, "all ValuePolarity members appear in docs")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _init_default(cls, param: str):
    """Return the default value of `cls.__init__`'s `param`, or None if absent."""
    import inspect
    sig = inspect.signature(cls.__init__)
    p   = sig.parameters.get(param)
    return p.default if p is not None and p.default is not inspect.Parameter.empty else None


def _paired_claim(
    label:    str,
    pattern:  str,
    expected,
    text:     str,
) -> Optional[str]:
    """
    Search `text` for `pattern` (must have one capturing group for the value),
    parse the captured number to match the type of `expected`, and verify it
    equals `expected`.

    This is the "paired" form: a doc claim is verified only when a parameter
    name appears beside its value (e.g. `interaction_count ≥ 20`), not when
    the value happens to appear anywhere in the doc. Without pairing, the
    bare number `20` matches against dozens of irrelevant places (year
    fragments, indices, port numbers, etc.).

    Returns None if the claim is satisfied. Returns a human-readable failure
    string otherwise.
    """
    # Normalize unicode minus to ASCII for matching against doc text.
    normalized = text.replace("−", "-")
    matches = re.findall(pattern, normalized)
    if not matches:
        return f"  {label}: no doc claim matches pattern (expected {expected!r})"

    try:
        if isinstance(expected, bool):
            got = matches[0].lower() in ("true", "yes", "1")
        elif isinstance(expected, int):
            got = int(matches[0])
        else:
            got = float(matches[0])
    except (ValueError, TypeError):
        return f"  {label}: could not parse '{matches[0]}' as {type(expected).__name__}"

    if got != expected:
        return f"  {label}: docs say {got}, code default is {expected}"
    return None


# ---------------------------------------------------------------------------
# 6. RelationalBondManager formation thresholds match docs.
# ---------------------------------------------------------------------------

def check_bond_formation_thresholds() -> CheckResult:
    name = "RelationalBondManager formation thresholds"
    from agents.relational_bond_manager import RelationalBondManager, FLOOR_FACTOR, BORDERLINE_MARGIN

    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT

    paired = [
        # Each entry: (label, regex with one capture group, expected value)
        ("interaction_count threshold",
         r"interaction_count\s*[≥>=]+\s*(\d+)",
         _init_default(RelationalBondManager, "formation_interaction_threshold")),

        ("crystal_count threshold",
         r"crystal_count\s*[≥>=]+\s*(\d+)",
         _init_default(RelationalBondManager, "formation_crystal_threshold")),

        ("BORDERLINE_MARGIN",
         r"BORDERLINE_MARGIN\s*=?\s*`?([\d.]+)`?",
         BORDERLINE_MARGIN),

        # FLOOR_FACTOR shows up in docs as `bond_strength × 0.40` describing
        # the trust-floor multiplier.
        ("trust-floor multiplier (FLOOR_FACTOR)",
         r"bond_strength\s*[×*]\s*`?([\d.]+)`?",
         FLOOR_FACTOR),

        # Adaptive coherence floor — docs phrase it as "floor `0.01`"
        ("min_coherence_threshold (adaptive floor)",
         r"floor\s*`?([\d.]+)`?",
         _init_default(RelationalBondManager, "min_coherence_threshold")),

        # allow_rate alternate path — added in Tier 1 Revision
        ("allow_rate threshold",
         r"allow_rate\s*[≥>=]+\s*`?([\d.]+)`?",
         _init_default(RelationalBondManager, "allow_rate_threshold")),
    ]

    failures = [
        msg for (label, pat, exp) in paired
        if (msg := _paired_claim(label, pat, exp, combined)) is not None
    ]

    if failures:
        return failed(
            name,
            "Bond formation thresholds: paired claim mismatch",
            failures,
        )
    return passed(name, f"all {len(paired)} paired claims match code")


# ---------------------------------------------------------------------------
# 7. CrystalStore thresholds match docs.
# ---------------------------------------------------------------------------

def check_crystallization_thresholds() -> CheckResult:
    name = "CrystalStore thresholds"
    from substrate.memory_crystals import CrystalStore

    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT

    # Docs phrase these as `coherence ≥ 0.75`, `stability ≥ 0.60`, `relation ≥ 0.80`.
    paired = [
        ("coherence_threshold",
         r"coherence\s*[≥>=]+\s*`?([\d.]+)`?",
         _init_default(CrystalStore, "coherence_threshold")),
        ("stability_threshold",
         r"stability\s*[≥>=]+\s*`?([\d.]+)`?",
         _init_default(CrystalStore, "stability_threshold")),
        ("relation_threshold",
         r"relation\s*[≥>=]+\s*`?([\d.]+)`?",
         _init_default(CrystalStore, "relation_threshold")),
    ]

    failures = [
        msg for (label, pat, exp) in paired
        if (msg := _paired_claim(label, pat, exp, combined)) is not None
    ]

    if failures:
        return failed(name, "Crystallization thresholds: paired claim mismatch", failures)
    return passed(name, f"all {len(paired)} paired claims match code")


# ---------------------------------------------------------------------------
# 8. ManipulationResistanceEngine thresholds match docs.
# ---------------------------------------------------------------------------

def check_manipulation_detector_thresholds() -> CheckResult:
    name = "ManipulationResistanceEngine thresholds"
    from agents.manipulation_resistance import ManipulationResistanceEngine

    expected = {
        "drift_velocity_threshold":     _init_default(ManipulationResistanceEngine, "drift_velocity_threshold"),
        "drift_gap_threshold":          _init_default(ManipulationResistanceEngine, "drift_gap_threshold"),
        "gaslighting_cosine_threshold": _init_default(ManipulationResistanceEngine, "gaslighting_cosine_threshold"),
        "gaslighting_consecutive":      _init_default(ManipulationResistanceEngine, "gaslighting_consecutive"),
        "watcher_divergence_threshold": _init_default(ManipulationResistanceEngine, "watcher_divergence_threshold"),
        "trust_wash_drop_threshold":    _init_default(ManipulationResistanceEngine, "trust_wash_drop_threshold"),
        "trust_wash_history_req":       _init_default(ManipulationResistanceEngine, "trust_wash_history_req"),
        "hhi_critical":                 _init_default(ManipulationResistanceEngine, "hhi_critical"),
        "monopoly_threshold":           _init_default(ManipulationResistanceEngine, "monopoly_threshold"),
    }

    # Normalize unicode minus sign to ASCII before searching — docs use −
    # (U+2212) in places for typographic minus.
    combined = (_README_TEXT + "\n" + _CLAUDE_MD_TEXT).replace("−", "-")
    failures: List[str] = []

    # Each threshold value should appear at least once in the docs.
    # We accept multiple formats: e.g. 0.70 / 0.7, -0.20 / -0.2, 3.00 / 3.0
    def _value_present(v) -> bool:
        if isinstance(v, int):
            return f" {v} " in combined or f" {v}\n" in combined or f"`{v}`" in combined
        if isinstance(v, float):
            # Accept e.g. 0.20 / 0.2 / `0.2`
            forms = {f"{v:.2f}", f"{v:.1f}", str(v)}
            return any(f in combined for f in forms)
        return False

    for k, v in expected.items():
        if v is None:
            failures.append(f"  {k}: could not introspect default")
            continue
        if not _value_present(v):
            failures.append(f"  {k} = {v} not found in either doc")

    if failures:
        return failed(name, "Manipulation detector thresholds drift", failures)
    return passed(name, f"all {len(expected)} thresholds present in docs")


# ---------------------------------------------------------------------------
# 9. Rhythm energy thresholds match across rhythm_config.json, code, and docs.
# ---------------------------------------------------------------------------

def check_rhythm_thresholds() -> CheckResult:
    name = "Rhythm energy thresholds"
    from substrate.resonance_field import ResonanceField

    # Code source-of-truth
    code = ResonanceField.DEFAULT_THRESHOLDS  # {"stabilize": 0.5, "dream": 2.0, "reflect": 5.0}

    # JSON config source-of-truth
    json_path = REPO_ROOT / "agents" / "rhythm_config.json"
    cfg = json.loads(json_path.read_text())
    json_thresholds = {
        rhythm: meta.get("energy_threshold")
        for rhythm, meta in cfg["rhythms"].items()
    }

    failures: List[str] = []

    # Code ↔ JSON: stabilize/dream/reflect should align (explore is null in JSON)
    for k, v in code.items():
        if json_thresholds.get(k) != v:
            failures.append(
                f"  rhythm_config.json {k}={json_thresholds.get(k)} "
                f"vs code DEFAULT_THRESHOLDS {k}={v}"
            )

    # Docs: stabilize < 0.5, dream 0.5–2.0, reflect 2.0–5.0, explore ≥ 5.0
    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT
    for label, val in [("stabilize", code["stabilize"]),
                       ("dream",     code["dream"]),
                       ("reflect",   code["reflect"])]:
        if str(val) not in combined:
            failures.append(f"  rhythm threshold {label} = {val} not found in docs")

    if failures:
        return failed(name, "Rhythm threshold drift", failures)
    return passed(name, f"thresholds match across code/JSON/docs: {code}")


# ---------------------------------------------------------------------------
# 10. Watcher layer weights sum to 1.0 (architectural invariant).
# ---------------------------------------------------------------------------

def check_watcher_weights_sum() -> CheckResult:
    name = "Watcher layer weights sum to 1.0"
    from agents.watcher import Watcher

    alpha = _init_default(Watcher, "alpha")
    beta  = _init_default(Watcher, "beta")
    gamma = _init_default(Watcher, "gamma")
    total = alpha + beta + gamma

    if abs(total - 1.0) > 1e-6:
        return failed(
            name,
            f"alpha+beta+gamma must sum to 1.0 — got {total}",
            [f"  alpha={alpha} beta={beta} gamma={gamma} sum={total}"],
        )

    # Each weight should be mentioned somewhere in the docs.
    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT
    failures: List[str] = []
    for k, v in (("alpha", alpha), ("beta", beta), ("gamma", gamma)):
        # Accept 0.40 / 0.4 / `0.40` / `0.4`
        forms = {f"{v:.2f}", f"{v:.1f}", str(v)}
        if not any(f in combined for f in forms):
            failures.append(f"  Watcher.{k} default = {v} not present in docs")

    if failures:
        return failed(name, "Watcher weight values not present in docs", failures)
    return passed(name, f"alpha={alpha} beta={beta} gamma={gamma} sum=1.0")


# ===========================================================================
# Orchestrator
# ===========================================================================

CHECKS: List[Callable[[], CheckResult]] = [
    check_tests_tree_completeness,
    check_trust_level_enum,
    check_philosophical_constants,
    check_governance_decision_enum,
    check_value_polarity_enum,
    check_bond_formation_thresholds,
    check_crystallization_thresholds,
    check_manipulation_detector_thresholds,
    check_rhythm_thresholds,
    check_watcher_weights_sum,
]


def main() -> int:
    print("=" * 72)
    print("  DOC ACCURACY: README.md + CLAUDE.md vs code")
    print("=" * 72)
    print()

    results: List[CheckResult] = []
    for check in CHECKS:
        try:
            results.append(check())
        except Exception as exc:
            results.append(failed(
                name    = check.__name__,
                summary = f"check raised {type(exc).__name__}",
                details = [f"  {exc}"],
            ))

    passed_count = sum(1 for r in results if r.passed)
    failed_count = len(results) - passed_count

    for r in results:
        mark = "✓" if r.passed else "✗"
        print(f"  {mark} {r.name:<48} {r.summary}")
        for line in r.details:
            print(line)

    print()
    print("─" * 72)
    print(f"  passed: {passed_count}    failed: {failed_count}")
    print("─" * 72)

    if failed_count:
        print()
        print("Behavioral / prose claims are NOT verified by this script —")
        print("the catch surface is mechanical (paths, defaults, enum members,")
        print("threshold values). For prose claims, read the diff against code.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
