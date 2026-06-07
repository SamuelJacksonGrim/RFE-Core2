"""
tests/diagnostic/conformity_bias_probe.py

Does field-coherence buy extra survival, holding everything else equal?

The reaper's retention is governance+reaper acting as a circulation chamber
(staged death ACTIVE→WARM→COLD→GRAVEYARD, minimum_lifespan immunity, decay floor,
recurrence-weighted reinforcement). The chamber is real. The open question is
whether it has a CONFORMITY BIAS: `field_coherence_weight` is positive in every
DecayProfile, so a pattern that agrees with the existing field may earn extra
survival on top of recurrence — the monoculture pump.

This probe isolates the `field_coherence` term as the SOLE differing signal.
`DecayProfile.compute(state, step)` is a pure function of the state, so we build
two SymbolStates identical in every field EXCEPT field_coherence, run compute()
over N laps, and compare survival trajectories. Because every other reinforcement
signal (recurrence, attractor_strength, centrality, crystal_binding) is forced
equal by construction, any divergence is attributable to field_coherence ALONE.
This is tighter than "inject a coherent vs a novel pattern and match recurrence" —
real coherent patterns also carry correlated attractor/crystal binding (the
inputCos-style confound), so they must be equalized by hand, not sampled.

PRE-DECLARED SIGNATURES (discipline #4)
---------------------------------------
  A-WINS (conformity bias CONFIRMED):
      high-coherence state retains MORE usage / survives longer than the
      low-coherence state at matched recurrence → field_coherence buys survival;
      Fix 0-B must add a counterweight (novelty-positive term) to reinforcement.
  TIE (recurrence dominates):
      trajectories within noise of each other → the coherence term is present in
      the formula but negligible in practice at these signal magnitudes.
  B-WINS (hidden anti-coherence effect):
      low-coherence state survives longer → something in the formula opposes
      coherence; would contradict the formula-level read and need explaining.

  Quantify: report usage(N) ratio and the step each crosses staged thresholds.
  The control IS the construction: two states, one field differs.

Informational. exit 0. NEVER in run_all_tests.sh (discipline #3).
"""
import sys
import logging

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from agents.symbolic_memory import (   # noqa: E402
    SymbolState, DecayProfile, DECAY_PROFILES, TokenClass,
)


def make_state(symbol, coherence, token_class, recurrence,
               attractor, centrality, crystal):
    """A SymbolState with every reinforcement signal set explicitly, so two
    states can be made identical except for one field."""
    return SymbolState(
        symbol=symbol,
        stable_id=abs(hash(symbol)) % 100000,
        address=0,
        token_class=token_class,
        usage=1.0,
        recurrence=recurrence,
        centrality=centrality,
        attractor_strength=attractor,
        crystal_binding=crystal,
        field_coherence=coherence,
        created_step=0,
        last_seen_step=0,
    )


def run_pair_symmetric(profile: DecayProfile, token_class: TokenClass,
                       n_laps=400, recur=0.8):
    """PROTOTYPE (probe-only, NOT substrate): apply the recurrence gate
    SYMMETRICALLY to both coherence and novelty, so neither earns survival
    without recurring first. This is the candidate Fix 0-B.

        gate              = 1 - exp(-0.5 * recurrence)
        effective_coher   = field_coherence * gate
        effective_novelty = (1 - field_coherence) * gate

    Everything else identical to run_pair. Returns the same (ratio, dlog, 2x)
    so it's directly comparable to the baseline.
    """
    import math
    common = dict(token_class=token_class, recurrence=recur,
                  attractor=0.3, centrality=0.3, crystal=0.3)
    A = make_state("coherent_A", coherence=0.90, **common)
    B = make_state("novel_B",    coherence=0.05, **common)

    def reinforce(state):
        gate = 1.0 - math.exp(-0.5 * state.recurrence)
        eff_coher = state.field_coherence * gate
        eff_novel = max(0.0, 1.0 - state.field_coherence) * gate
        return (1.0
                + profile.recurrence_weight      * state.recurrence
                + profile.attractor_weight       * state.attractor_strength
                + profile.centrality_weight      * state.centrality
                + profile.field_coherence_weight * eff_coher
                + profile.crystal_binding_weight * state.crystal_binding
                + profile.novelty_weight         * eff_novel)

    log_a = log_b = 0.0
    ratios = []
    for step in range(1, n_laps + 1):
        if step % 5 == 0:
            A.last_seen_step = step
            B.last_seen_step = step
        age_a = A.age(step)
        decay = max(profile.base_decay * math.exp(-profile.age_factor * age_a), 0.01)
        a_mult = decay * reinforce(A)
        b_mult = decay * reinforce(B)
        ratios.append(a_mult / b_mult if b_mult > 1e-12 else float("inf"))
        log_a += math.log(max(a_mult, 1e-12))
        log_b += math.log(max(b_mult, 1e-12))

    mean_ratio = sum(ratios) / len(ratios)
    dlog = log_a - log_b
    if mean_ratio > 1.0 + 1e-9:
        laps_2x = math.log(2) / math.log(mean_ratio)
    elif mean_ratio < 1.0 - 1e-9:
        laps_2x = -math.log(2) / math.log(mean_ratio)
    else:
        laps_2x = float("inf")
    return mean_ratio, dlog, laps_2x


def noise_immunity_check(profile, token_class):
    """Signature 3: a one-off (recurrence=0) dissonant pattern must get NO
    novelty bonus. With recurrence=0 the gate is 0, so effective_novelty=0.
    Returns the reinforcement a recurrence=0 novel pattern receives vs the
    baseline 1.0 (should be ~1.0 = no bonus)."""
    import math
    s = make_state("oneoff_novel", coherence=0.0, token_class=token_class,
                   recurrence=0.0, attractor=0.0, centrality=0.0, crystal=0.0)
    gate = 1.0 - math.exp(-0.5 * s.recurrence)   # = 0
    eff_novel = (1.0 - s.field_coherence) * gate  # = 0
    reinforcement = 1.0 + profile.novelty_weight * eff_novel
    return reinforcement   # ~1.0 means noise got no survival bonus


def high_recur_parity(profile, token_class):
    """Signature 4: at HIGH recurrence (gate ~fully open), coherent and novel
    should tie. Returns per-step ratio at recurrence=5.0."""
    r, _, _ = run_pair_symmetric(profile, token_class, n_laps=100, recur=5.0)
    return r


def run_pair(profile: DecayProfile, token_class: TokenClass,
             n_laps=400, recur=0.8):
    """Baseline: reads the CURRENT live formula (asymmetric gate as patched into
    the substrate). Reports the HONEST per-step lean, not runaway usage.
    Both states recur on the same schedule (recurrence/age matched).
    """
    common = dict(token_class=token_class, recurrence=recur,
                  attractor=0.3, centrality=0.3, crystal=0.3)
    A = make_state("coherent_A", coherence=0.90, **common)
    B = make_state("novel_B",    coherence=0.05, **common)

    import math
    log_a = log_b = 0.0          # track usage in log-space (no overflow)
    per_step_ratios = []
    for step in range(1, n_laps + 1):
        if step % 5 == 0:
            A.last_seen_step = step
            B.last_seen_step = step
        # reinforcement = compute()/(usage*decay); but compute() multiplies usage,
        # so derive the per-step multiplier directly from the state instead.
        a_mult = profile.compute(A, step) / max(A.usage, 1e-12)
        b_mult = profile.compute(B, step) / max(B.usage, 1e-12)
        per_step_ratios.append(a_mult / b_mult if b_mult > 1e-12 else float("inf"))
        log_a += math.log(max(a_mult, 1e-12))
        log_b += math.log(max(b_mult, 1e-12))
        # advance usage in log-space, keep states' usage normalized to avoid 1e57
        A.usage = 1.0
        B.usage = 1.0

    mean_ratio = sum(per_step_ratios) / len(per_step_ratios)
    dlog = log_a - log_b
    # laps to 2x: solve mean_ratio^n = 2  ->  n = ln2 / ln(mean_ratio)
    if mean_ratio > 1.0 + 1e-9:
        laps_to_2x = math.log(2) / math.log(mean_ratio)
    elif mean_ratio < 1.0 - 1e-9:
        laps_to_2x = -math.log(2) / math.log(mean_ratio)  # B pulls ahead
    else:
        laps_to_2x = float("inf")
    return mean_ratio, dlog, laps_to_2x


def main():
    import math
    print("=" * 74)
    print("  CONFORMITY-BIAS PROBE + SYMMETRIC-GATE PROTOTYPE (Fix 0-B candidate)")
    print("=" * 74)
    print("  Two states identical except field_coherence (A=0.90, B=0.05).")
    print("  Comparing: [current patch: asymmetric gate] vs [prototype: symmetric].")
    print("  Targets for symmetric: lean→0, laps-to-2x→inf, noise→no bonus,")
    print("                         high-recurrence→tie.")
    print("-" * 74)

    for tc in [TokenClass.GLYPH, TokenClass.ENTITY, TokenClass.LANGUAGE]:
        profile = DECAY_PROFILES[tc]
        # current live formula (asymmetric gate, already patched into substrate)
        r_asym, _, l_asym = run_pair(profile, tc)
        # prototype: symmetric gate (probe-only)
        r_sym, _, l_sym = run_pair_symmetric(profile, tc)
        # signature checks
        noise = noise_immunity_check(profile, tc)
        parity = high_recur_parity(profile, tc)

        print(f"\n  {tc.value.upper()}  (coh_w={profile.field_coherence_weight}, "
              f"nov_w={profile.novelty_weight})")
        print(f"    asymmetric (current) : {(r_asym-1)*100:+.2f}%/lap   "
              f"2x in {l_asym:.0f} laps" if l_asym != float('inf')
              else f"    asymmetric (current) : {(r_asym-1)*100:+.2f}%/lap   2x never")
        print(f"    SYMMETRIC (prototype): {(r_sym-1)*100:+.2f}%/lap   "
              + (f"2x in {l_sym:.0f} laps" if l_sym != float('inf') else "2x NEVER ✓"))
        print(f"    [sig3] noise (recur=0) reinforcement: {noise:.4f}  "
              + ("✓ no bonus" if abs(noise - 1.0) < 1e-6 else "✗ got bonus"))
        print(f"    [sig4] high-recur (5.0) parity ratio: {parity:.4f}  "
              + ("✓ tie" if abs(parity - 1.0) < 0.005 else "✗ still leans"))

    print("\n" + "-" * 74)
    print("READ: if symmetric collapses the lean toward 0 and the two signatures")
    print("hold (noise→1.0, high-recur→1.0), symmetric gating is the validated")
    print("Fix 0-B candidate. If the lean PERSISTS even symmetric, the cause is")
    print("elsewhere (e.g. the ungated coherence appears in OTHER correlated")
    print("signals) and needs a deeper look before touching the substrate.")
    print("PROTOTYPE IS PROBE-ONLY. Substrate currently has the asymmetric patch;")
    print("do not ship symmetric until isolated AND full-loop validation pass.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
