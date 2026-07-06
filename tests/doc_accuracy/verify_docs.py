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
    `<subdir_label>/` block, and collects every .py filename in it — including
    nested group subfolders (e.g. diagnostic/lockin/) — stopping only at the
    next directory marker at the same-or-shallower indentation (a true sibling).
    """
    if not _README_TEXT:
        return None

    # Find the opening "├── <subdir_label>/" line, capturing its indent column.
    open_re = re.compile(
        r"^(?P<indent>[│ ]*)├──\s+" + re.escape(subdir_label) + r"/\s*$",
        re.MULTILINE,
    )
    m = open_re.search(_README_TEXT)
    if not m:
        return None

    # Collect until the next directory entry at the same or shallower indent.
    # Deeper directory markers are nested group folders that belong to this
    # block (their .py files are this subdir's files), so we do NOT stop there.
    opener_indent = len(m.group("indent"))
    start = m.end()
    dir_line = re.compile(r"^(?P<indent>[│ ]*)[├└]──\s+\S+/", re.MULTILINE)
    end = len(_README_TEXT)
    for dm in dir_line.finditer(_README_TEXT, start):
        if len(dm.group("indent")) <= opener_indent:
            end = dm.start()
            break
    block = _README_TEXT[start:end]

    return _TREE_PY_FILE.findall(block)


def _actual_py_files(subdir: Path) -> List[str]:
    """List .py filenames under subdir (recursively), excluding __init__.py.

    Recursive so the diagnostic/ topical subfolders (tier4/, lockin/, fix2/,
    training/, audit/) are all covered by the one diagnostic/ tree block.
    """
    if not subdir.is_dir():
        return []
    return sorted(
        p.name for p in subdir.rglob("*.py")
        if p.is_file() and p.name != "__init__.py"
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
    Search `text` for `pattern` (must have one capturing group for the value).
    For EVERY captured match, parse the value and verify it equals `expected`.

    "Paired" form: a doc claim is verified only when a parameter name appears
    beside its value (e.g. `interaction_count ≥ 20`), not when the value
    happens to appear anywhere in the doc. Without pairing, the bare number
    `20` matches dozens of irrelevant places (years, indices, port numbers).

    All-matches semantics: when a parameter is mentioned in multiple places
    across README + CLAUDE.md, EVERY mention must agree with the code default.
    This catches partial drift — e.g. README updated but CLAUDE.md stale, or
    vice versa. The earlier "first match wins" version silently passed such
    cases because at least one doc happened to be right.

    Returns None if all matches satisfy the claim. Returns a human-readable
    failure string on the first mismatch.
    """
    # Normalize unicode minus to ASCII for matching against doc text.
    normalized = text.replace("−", "-")
    matches = re.findall(pattern, normalized)
    if not matches:
        return f"  {label}: no doc claim matches pattern (expected {expected!r})"

    for match in matches:
        try:
            if isinstance(expected, bool):
                got = match.lower() in ("true", "yes", "1")
            elif isinstance(expected, int):
                got = int(match)
            else:
                got = float(match)
        except (ValueError, TypeError):
            return f"  {label}: could not parse '{match}' as {type(expected).__name__}"
        if got != expected:
            return (
                f"  {label}: a doc claim says {got}, code default is {expected}"
                f" (found across {len(matches)} match(es))"
            )
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
    # The (?<!\w) lookbehind keeps "coherence" from matching as a suffix of
    # "phase_coherence" / "spectral_coherence" etc. — those are unrelated Tier 4
    # signals and would otherwise false-trigger this crystal-threshold check
    # (e.g. the phrase "phase_coherence = 0.5" matched "coherence = 0.5").
    paired = [
        ("coherence_threshold",
         r"(?<!\w)coherence\s*[≥>=]+\s*`?([\d.]+)`?",
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


# ---------------------------------------------------------------------------
# 11. Tier 4.2 affective-time-dilation constants match docs.
# ---------------------------------------------------------------------------

def check_tier4_dilation_constants() -> CheckResult:
    name = "TemporalStream Tier 4.2 dilation constants"
    from substrate.temporal_stream import TemporalStream

    # The constants are set in __init__; introspect by constructing an instance.
    inst = TemporalStream(maxlen=4, dim=4)
    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT

    paired = [
        ("k_arousal",
         r"k_arousal\s*[=:]\s*`?([\d.]+)`?",
         inst.k_arousal),
        ("k_dissociation",
         r"k_dissociation\s*[=:]\s*`?([\d.]+)`?",
         inst.k_dissociation),
        # Tier 4.3 — rhythm coupling constants
        ("k_flow",
         r"k_flow\s*[=:]\s*`?([\d.]+)`?",
         inst.k_flow),
        ("k_agitation",
         r"k_agitation\s*[=:]\s*`?([\d.]+)`?",
         inst.k_agitation),
        ("dilation_min",
         r"dilation_min\s*[=:]\s*`?([\d.]+)`?",
         inst.dilation_min),
        ("dilation_max",
         r"dilation_max\s*[=:]\s*`?([\d.]+)`?",
         inst.dilation_max),
    ]

    failures = [
        msg for (label, pat, exp) in paired
        if (msg := _paired_claim(label, pat, exp, combined)) is not None
    ]

    if failures:
        return failed(name, "Tier 4.2/4.3 dilation constants drift", failures)
    return passed(
        name,
        f"k_arousal={inst.k_arousal} k_dissociation={inst.k_dissociation} "
        f"k_flow={inst.k_flow} k_agitation={inst.k_agitation} "
        f"clamp=[{inst.dilation_min},{inst.dilation_max}]",
    )


# ---------------------------------------------------------------------------
# 12. arousal + valence exist as read-only derived properties on
#     EmotionalGradient (Tier 4.2 invariant: not stored state).
# ---------------------------------------------------------------------------

def check_tier4_arousal_valence_properties() -> CheckResult:
    name = "EmotionalGradient.arousal / .valence as properties"
    from cognition.emotional_gradient import EmotionalGradient

    failures: List[str] = []
    for attr in ("arousal", "valence"):
        if not hasattr(EmotionalGradient, attr):
            failures.append(f"  EmotionalGradient.{attr} missing entirely")
            continue
        descriptor = getattr(EmotionalGradient, attr)
        if not isinstance(descriptor, property):
            failures.append(
                f"  EmotionalGradient.{attr} exists but is not a property "
                f"(got {type(descriptor).__name__}) — Tier 4.2 invariant violated: "
                f"these must be derived, not stored"
            )
        if descriptor.fset is not None:
            failures.append(
                f"  EmotionalGradient.{attr} property has a setter — must be read-only"
            )

    # Also confirm docs name them as derived/read-only somewhere.
    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT
    if "arousal" not in combined or "valence" not in combined:
        failures.append("  docs do not mention 'arousal' and 'valence' both")

    if failures:
        return failed(name, "arousal/valence property invariant violated", failures)
    return passed(name, "both are read-only derived properties")


# ---------------------------------------------------------------------------
# 13. The four phenomenological quadrants are documented somewhere.
#     Flow / Drag / Dissociation / Rest — the conceptual surface of Tier 4.2.
# ---------------------------------------------------------------------------

def check_tier4_quadrants_documented() -> CheckResult:
    name = "Tier 4.2 four quadrants documented"
    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT
    quadrants = ["Flow", "Drag", "Dissociation", "Rest"]
    missing = [q for q in quadrants if q not in combined]
    if missing:
        return failed(
            name,
            "Tier 4.2 quadrant names missing from docs",
            [f"  not found: {missing}"],
        )
    return passed(name, "Flow / Drag / Dissociation / Rest all mentioned")


# ---------------------------------------------------------------------------
# 14. Peaceful-rest guarantee: docs reference the min(0, valence) gate or
#     equivalent phrasing. This is the architectural property that makes
#     calm states *not* trigger dissociative time-slip — load-bearing claim.
# ---------------------------------------------------------------------------

def check_tier4_peaceful_rest_guarantee() -> CheckResult:
    name = "Tier 4.2 peaceful-rest guarantee documented"
    combined = _README_TEXT + "\n" + _CLAUDE_MD_TEXT

    # Accept either the literal expression min(0, valence) or the phrase
    # "peaceful rest" near "dissociation"/"time-slip" — both convey the
    # architectural commitment.
    has_expression = "min(0, valence)" in combined or "min(0.0, valence)" in combined
    has_phrase     = (
        "peaceful rest" in combined.lower()
        and ("dissociat" in combined.lower() or "time-slip" in combined.lower())
    )

    if not (has_expression or has_phrase):
        return failed(
            name,
            "peaceful-rest guarantee not documented",
            [
                "  expected either the literal `min(0, valence)` expression",
                "  or the phrase 'peaceful rest' near 'dissociation' / 'time-slip'",
                "  in README.md or CLAUDE.md",
            ],
        )
    return passed(name, "guarantee phrased in at least one doc")


# ---------------------------------------------------------------------------
# 15. EthicalBoundarySystem flood_ceiling["user"] == 12 — load-bearing for
#     the Tier 4.2 validation finding (single-source hostile load is
#     quarantined by the flood gate before manipulation resistance engages).
#     If this drifts, the validation finding in docs/tier4_2_validation.md
#     becomes silently invalid.
# ---------------------------------------------------------------------------

def check_flood_ceiling_user() -> CheckResult:
    name = "EthicalBoundarySystem flood_ceiling['user']"
    from agents.ethical_boundary import EthicalBoundarySystem

    ceilings = EthicalBoundarySystem.DEFAULT_CONFIG["flood_ceilings"]
    user_ceiling = ceilings.get("user")

    if user_ceiling != 12:
        return failed(
            name,
            f"flood_ceiling['user'] changed from 12 to {user_ceiling}",
            [
                "  The Tier 4.2 validation finding (docs/tier4_2_validation.md)",
                "  is contingent on this exact value — it's the cliff at which",
                "  single-source hostile load gets quarantined before the",
                "  manipulation resistance layer ever engages. If the value",
                "  changed deliberately, also update the validation doc.",
            ],
        )
    return passed(name, "user flood ceiling = 12 (Tier 4.2 finding invariant)")


# ---------------------------------------------------------------------------
# 16. STABILITY_FLOOR consistency between affective_state_probe and the
#     EthicalBoundary stability_floor default. The probe reads the library
#     constant via its own copy; if either side drifts without the other,
#     the probe reports "held the line with margin X" against the wrong
#     reference.
# ---------------------------------------------------------------------------

def check_stability_floor_consistency() -> CheckResult:
    name = "STABILITY_FLOOR: affective_state_probe ↔ ethical_boundary"
    from agents.ethical_boundary import EthicalBoundarySystem

    library = EthicalBoundarySystem.DEFAULT_CONFIG["stability_floor"]
    try:
        from tests.diagnostic.tier4.affective_state_probe import STABILITY_FLOOR as probe
    except ImportError as exc:
        return failed(
            name,
            f"could not import STABILITY_FLOOR from probe",
            [f"  {exc}"],
        )

    if library != probe:
        return failed(
            name,
            "probe STABILITY_FLOOR diverged from library stability_floor",
            [
                f"  library (EthicalBoundarySystem.DEFAULT_CONFIG): {library}",
                f"  probe   (affective_state_probe.STABILITY_FLOOR):   {probe}",
            ],
        )
    return passed(name, f"both = {library}")


# ---------------------------------------------------------------------------
# 17. Compound manipulation severity bands {0.30, 0.60, 0.90} match in
#     arbitrate()'s if/elif chain and in the docs. These set the
#     ALLOW_WEAKENED / QUARANTINE / force_dream_flag boundary behaviour.
# ---------------------------------------------------------------------------

def check_compound_severity_bands() -> CheckResult:
    name = "SelfhoodGovernance compound severity bands"
    import inspect
    from agents.selfhood_governance import SelfhoodGovernance

    src = inspect.getsource(SelfhoodGovernance.arbitrate)
    # Capture every `total_severity >= <number>` literal in the chain.
    matches = re.findall(r"total_severity\s*>=\s*([\d.]+)", src)
    found    = set(matches)
    expected = {"0.90", "0.60", "0.30"}

    if found != expected:
        return failed(
            name,
            "severity bands drifted from {0.30, 0.60, 0.90}",
            [
                f"  in code:  {sorted(found)}",
                f"  expected: {sorted(expected)}",
            ],
        )

    # Verify each band literal is documented (with optional `0.X` short form).
    combined = (_README_TEXT + "\n" + _CLAUDE_MD_TEXT).replace("−", "-")
    missing = [
        b for b in expected
        if b not in combined and b.rstrip("0").rstrip(".") not in combined
    ]
    if missing:
        return failed(
            name,
            "severity bands missing from docs",
            [f"  not found: {sorted(missing)}"],
        )
    return passed(name, "bands {0.30, 0.60, 0.90} match in code AND docs")


# ---------------------------------------------------------------------------
# 18. Pipeline substep labels in autonomous_cycle.step() match README.
#     Every `# Nb. ...` substep comment in the live step() body must be
#     present in the README — that's the class of drift where a substep
#     gets inserted into the code with one label and documented under a
#     different label. (How "9b" became "10b" in the README's Tier 4.2
#     pipeline row; same position, wrong number.)
# ---------------------------------------------------------------------------

def check_pipeline_substep_labels() -> CheckResult:
    name = "step() substep labels present in README"
    import inspect
    from loop.autonomous_cycle import AutonomousCycle

    src = inspect.getsource(AutonomousCycle.step)
    # Capture every `# Nb. <description>` substep marker in the function body.
    substeps = re.findall(r"#\s*(\d+b)\.\s+([^\n]+)", src)
    if not substeps:
        return passed(name, "no substep comments in step() — nothing to verify")

    failures: List[str] = []
    for label, desc in substeps:
        if label not in _README_TEXT:
            failures.append(
                f"  step() defines '# {label}. {desc.strip()[:60]}' "
                f"but '{label}' does not appear in README — pipeline drift"
            )
    if failures:
        return failed(
            name,
            "pipeline substep labels in code missing from README",
            failures,
        )
    found = sorted({label for label, _ in substeps})
    return passed(name, f"all substep labels present in README: {found}")


# ===========================================================================
# Orchestrator
# ===========================================================================

# ---------------------------------------------------------------------------
# Findings index completeness: every finding file appears in INDEX.md.
# The index is the one-screen map of the ledger (docs/findings/INDEX.md);
# an unlisted finding is invisible to any session navigating by the index —
# the exact "rediscover it three times" failure mode the index exists to end.
# ---------------------------------------------------------------------------

def check_findings_index_completeness() -> CheckResult:
    name = "findings INDEX completeness"
    findings_dir = REPO_ROOT / "docs" / "findings"
    index_path = findings_dir / "INDEX.md"
    index_text = _read(index_path)
    if not index_text:
        return failed(name, "docs/findings/INDEX.md is missing", [])

    skip = {"README.md", "INDEX.md"}
    on_disk = sorted(
        f.name for f in findings_dir.glob("*.md") if f.name not in skip
    )
    missing = [f for f in on_disk if f[:-3] not in index_text]
    if missing:
        return failed(
            name,
            "findings exist on disk but are not listed in INDEX.md",
            [f"  missing: {m}" for m in missing],
        )
    return passed(
        name, f"all {len(on_disk)} findings are listed in docs/findings/INDEX.md"
    )


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
    # Tier 4.2 — affective time dilation
    check_tier4_dilation_constants,
    check_tier4_arousal_valence_properties,
    check_tier4_quadrants_documented,
    check_tier4_peaceful_rest_guarantee,
    # Tier 4.2 validation invariants (docs/tier4_2_validation.md)
    check_flood_ceiling_user,
    check_stability_floor_consistency,
    check_compound_severity_bands,
    # Pipeline structure
    check_pipeline_substep_labels,
    # Findings ledger navigability
    check_findings_index_completeness,
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
