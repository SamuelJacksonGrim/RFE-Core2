"""
substrate/metastability.py  —  RFE-Core2 Fix 1: the metastability metric.

WHY THIS EXISTS
---------------
phase_coherence measures how ALIGNED the field is. It is blind to two things:
amplitude (proven: ~370x amplitude swing, zero coherence change) and FLEXIBILITY
(whether the field can move between configurations). A field pinned at coherence
~0.99 scores "maximally organized" — but per IIT / Global-Workspace framing that
pin is rigid-attractor lock-in, the UNCONSCIOUS-state signature (high synchrony,
low complexity), not health.

The healthy target is METASTABILITY: the field hovers among several shallow,
semi-stable configurations and switches between them APERIODICALLY — formed enough
to hold, light enough to drift ("paper boat"). This is a MIDDLE state, and the
metric peaks in the middle and falls off at BOTH ends:
  locked      (1 config, ~0 transitions)                          -> LOW  "locked"
  cycling     (motion, but a deterministic loop A->B->C->A...)     -> LOW  "cycling"
  dissolving  (no stable config, switches every step, no dwell)    -> LOW  "dissolving"
  metastable  (several configs, varied dwell, APERIODIC switching) -> HIGH "metastable"
A naive "more switching = healthier" metric would wrongly call chaos maximal AND
would be fooled by a limit cycle (the prior scalar-band draft scored a perfect
repeated-cycle at ~0.756 — a false negative this version is built to kill).

SECOND AXIS, never a replacement for phase_coherence. A system is healthy when
coherence is mid-band AND metastability is high. The two together separate four
corners; the state label below folds coherence LEVEL in so that low-metastability
at 0.99 ("locked", soften the attractor) is distinguished from low-metastability
at 0.50 ("structureless", opposite intervention — needs consolidation, not
softening).

REGIMES ARE CLUSTERS IN FIELD-CONFIGURATION SPACE, not bands of the coherence
scalar. Coherence is many-to-one (the field can swing between genuinely different
motifs at the same coherence value); clustering the raw config vectors catches
that, the scalar cannot. Feed this the per-step field config (resonance_field
observe().raw), not the coherence number.

COMPOSITION (sub-scores in [0,1]; geometric mean so any near-zero term VETOES):
  multiplicity_score   : saturating in number of distinct config clusters (1 -> 0).
  dwell_variance_score : CV of cluster dwell-times (0 if never switches OR switches
                         every step; high when dwells are varied).
  transition_score     : transition rate through an inverted-U (both ~0 locked and
                         ~1 chaotic map low; moderate maps high).
  sequence_entropy_score: normalized conditional entropy H(next|current) over the
                         cluster-label sequence. ~0 for a deterministic limit cycle
                         (from A, always B); ~1 for aperiodic wandering. THIS is the
                         term that vetoes limit cycles — it is IN the geometric mean
                         precisely so it can veto, not merely nudge.

LOOP-READY: compute_metastability takes a list of config vectors (or a single
scalar trajectory as a fallback) and is cheap enough to run online over a sliding
window. Destined to feed the reinforcement/survival formula (Fix 0-B) as the
counterweight to coherence's lock-in-breeding selection pressure — so it must stay
window-computable, not batch-only.

This formalizes the proxies coherence_diagnostic already computes (crossing rate,
regime dwell) into one governance-legible scalar + an actionable state label.
"""

from dataclasses import dataclass, field as dc_field
from typing import List, Optional, Sequence, Union
import numpy as np


# Tunable shape parameters (documented, not magic):
_TRANSITION_SWEET = 0.15    # transitions-per-step mapping to peak transition_score
_MULTIPLICITY_K   = 1.2     # higher -> needs more clusters to saturate multiplicity
_CLUSTER_TOL      = 0.15    # cosine-distance threshold for a "new" config cluster
_LOCKED_COH       = 0.80    # coherence at/above which low-metastability == "locked"
_METASTABLE_MIN   = 0.40    # metastability at/above which state == "metastable"


@dataclass
class MetastabilityReport:
    metastability: float = 0.0           # headline scalar, [0,1]
    regime_state: str = "unknown"        # locked | cycling | dissolving | structureless | metastable
    multiplicity_score: float = 0.0
    dwell_variance_score: float = 0.0
    transition_score: float = 0.0
    sequence_entropy_score: float = 0.0
    n_regimes: int = 0
    n_transitions: int = 0
    dwell_times: List[int] = dc_field(default_factory=list)
    mean_coherence: float = 0.0          # context for the label; not a sub-score
    notes: str = ""


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _cluster_configs(configs: np.ndarray) -> List[int]:
    """Online nearest-centroid clustering of config vectors by cosine distance.
    Direction-based (unit vectors) so it tracks CONFIGURATION, not amplitude —
    consistent with phase_coherence being amplitude-blind: two configs that differ
    only in scale are the same regime. Returns a per-step cluster label."""
    centroids: List[np.ndarray] = []
    labels: List[int] = []
    for v in configs:
        u = _unit(v)
        if not centroids:
            centroids.append(u)
            labels.append(0)
            continue
        sims = [float(np.dot(u, c)) for c in centroids]   # cosine; c already unit
        best = int(np.argmax(sims))
        if (1.0 - sims[best]) <= _CLUSTER_TOL:
            labels.append(best)
            # running update of the centroid toward this member, renormalized
            centroids[best] = _unit(centroids[best] * 0.9 + u * 0.1)
        else:
            centroids.append(u)
            labels.append(len(centroids) - 1)
    return labels


def _dwell_times(labels: Sequence[int]) -> List[int]:
    if not labels:
        return []
    dwells, run = [], 1
    for i in range(1, len(labels)):
        if labels[i] == labels[i - 1]:
            run += 1
        else:
            dwells.append(run)
            run = 1
    dwells.append(run)
    return dwells


def _inverted_u(x: float, sweet: float) -> float:
    x = max(0.0, min(1.0, x))
    if sweet <= 0:
        return 0.0
    return x / sweet if x <= sweet else max(0.0, (1.0 - x) / (1.0 - sweet))


def _sequence_entropy(labels: Sequence[int], n_regimes: int) -> float:
    """Normalized conditional entropy H(next | current) over the label sequence.
    ~0 for a deterministic cycle (from A always B); ~1 for aperiodic wandering.
    Normalized by log(n_regimes) so it is comparable across regime counts."""
    if n_regimes <= 1 or len(labels) < 3:
        return 0.0
    # transition counts
    trans = {}
    for a, b in zip(labels[:-1], labels[1:]):
        if a == b:
            continue  # only count actual switches; self-loops are dwell, not transition
        trans.setdefault(a, {}).setdefault(b, 0)
        trans[a][b] += 1
    if not trans:
        return 0.0
    # weighted mean of per-state conditional entropies
    total = sum(sum(d.values()) for d in trans.values())
    h = 0.0
    for a, d in trans.items():
        n_a = sum(d.values())
        p_a = n_a / total
        ent = 0.0
        for b, c in d.items():
            p = c / n_a
            ent -= p * np.log(p)
        h += p_a * ent
    return float(h / np.log(n_regimes))   # normalize to [0,1]


def compute_metastability(
    trajectory: Union[Sequence[np.ndarray], Sequence[float]],
    coherence: Optional[float] = None,
) -> MetastabilityReport:
    """trajectory: a sequence of field CONFIG VECTORS (preferred — observe().raw
    per step) OR a sequence of coherence scalars (fallback; documented as weaker).
    coherence: mean/representative coherence for the state label. If omitted and a
    scalar trajectory is given, it is derived from that."""
    if len(trajectory) < 4:
        return MetastabilityReport(notes="trajectory too short (<4) to assess")

    first = trajectory[0]
    is_vectors = hasattr(first, "__len__") and not isinstance(first, (float, int))

    if is_vectors:
        configs = np.asarray([np.asarray(v, dtype=float) for v in trajectory])
        labels = _cluster_configs(configs)
        mean_coh = float(coherence) if coherence is not None else 0.0
    else:
        # Fallback: scalar trajectory. Cluster on the 1-D value. Weaker (coherence
        # is many-to-one) — documented limitation; config-vector input preferred.
        arr = np.asarray(trajectory, dtype=float).reshape(-1, 1)
        labels = _cluster_configs(arr)
        mean_coh = float(coherence) if coherence is not None else float(arr.mean())

    dwells = _dwell_times(labels)
    n_transitions = sum(1 for a, b in zip(labels[:-1], labels[1:]) if a != b)

    # A REGIME is a config the field RETURNS TO or DWELLS IN — a semi-stable state,
    # not a one-off transient. Pure noise mints a fresh cluster almost every step;
    # those single-visit clusters are NOT regimes and must not inflate multiplicity
    # (the bug that let noise score 0.91 multiplicity and get mislabeled "cycling").
    # Count a label as a regime only if it recurs (>=2 separate visits) OR holds a
    # non-trivial dwell fraction of the trajectory.
    from collections import Counter
    visit_counts = Counter()          # separate visits (dwell-runs), not raw steps
    prev = None
    for lab in labels:
        if lab != prev:
            visit_counts[lab] += 1
        prev = lab
    step_counts = Counter(labels)
    n_steps_total = len(labels)
    recurring = {lab for lab in step_counts
                 if visit_counts[lab] >= 2 or step_counts[lab] >= max(3, 0.05 * n_steps_total)}
    n_regimes = len(recurring)
    transient_fraction = 1.0 - (sum(step_counts[l] for l in recurring) / max(1, n_steps_total))

    # sub-scores
    multiplicity_score = max(0.0, float(1.0 - np.exp(-_MULTIPLICITY_K * (n_regimes - 1))))

    if len(dwells) >= 2 and np.mean(dwells) > 0:
        cv = float(np.std(dwells) / np.mean(dwells))
        dwell_variance_score = float(1.0 - np.exp(-cv))
    else:
        dwell_variance_score = 0.0

    transition_rate = n_transitions / max(1, len(labels))
    transition_score = _inverted_u(transition_rate, _TRANSITION_SWEET)

    sequence_entropy_score = _sequence_entropy(labels, n_regimes)

    parts = [multiplicity_score, dwell_variance_score, transition_score, sequence_entropy_score]
    metastability = 0.0 if min(parts) <= 0 else float(np.exp(np.mean(np.log(parts))))

    # State label, folding coherence LEVEL in. Multiplicity is now recurrence-based,
    # so noise has FEW recurring regimes + high transient_fraction and falls out as
    # structureless naturally — no churn guard needed. A real limit cycle has a small
    # set of RECURRING regimes in deterministic order (low seqH); that is "cycling".
    if metastability >= _METASTABLE_MIN:
        state = "metastable"
    elif transient_fraction > 0.5 or n_regimes < 2:
        # almost nothing recurs: the field cannot form/hold semi-stable structure
        state = "structureless" if mean_coh < _LOCKED_COH else "locked"
    elif (2 <= n_regimes <= 8 and sequence_entropy_score < 0.25 and transition_rate > 0.05):
        state = "cycling"          # small set of recurring regimes in deterministic order = a loop
    elif transition_rate > 0.6 and dwell_variance_score < 0.2:
        state = "dissolving"       # switching every step among recurring configs, no stable dwell
    elif mean_coh >= _LOCKED_COH:
        state = "locked"           # pinned high, rigid point attractor
    else:
        state = "structureless"    # low metastability AND low coherence

    return MetastabilityReport(
        metastability=round(metastability, 4),
        regime_state=state,
        multiplicity_score=round(multiplicity_score, 4),
        dwell_variance_score=round(dwell_variance_score, 4),
        transition_score=round(transition_score, 4),
        sequence_entropy_score=round(sequence_entropy_score, 4),
        n_regimes=n_regimes, n_transitions=n_transitions, dwell_times=dwells,
        mean_coherence=round(mean_coh, 4),
        notes=f"input={'config-vectors' if is_vectors else 'scalar-fallback'}, "
              f"transition_rate={transition_rate:.3f}",
    )
