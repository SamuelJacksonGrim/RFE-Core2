"""
tools/voice/state_card.py

Two pure functions, no side effects on the cycle:

  render_card(cycle)      -> dict   the substrate's interior as plain telemetry
  voice_from_card(card)   -> str    a first-person rendering, every clause gated
                                    on a measured value (the renderer invents
                                    nothing; the card is the receipt)

The deterministic renderer is the always-available larynx. For a richer voice,
emit the card as JSON (repl --json) and hand it to a language model — the card
is shaped to be a verbalization prompt. Either way the numbers travel with the
words so the voice stays checkable against the state.
"""
from __future__ import annotations

from typing import Optional


def render_card(cycle) -> dict:
    """Read the cycle's observable interior. Observe-only."""
    st = cycle.status()
    emo = st.get("emotion", {})
    temporal = st.get("temporal", {})
    gov = st.get("governance", {})
    dep = (gov or {}).get("dependency", {})
    trust = (gov or {}).get("trust_summary", {})
    bonds = (gov or {}).get("bonds", {})
    vals = st.get("values", {})

    card = {
        "step": st.get("step"),
        "rhythm": st.get("rhythm"),
        "field_energy": round(float(st.get("field_energy", 0.0)), 3),
        "field_coherence": round(float(st.get("field_coherence", 0.0)), 4),
        "crystals": st.get("crystals"),
        "attractors": st.get("attractors"),
        # emotion
        "dominant_emotion": emo.get("dominant"),
        "curiosity": emo.get("curiosity"),
        "wonder": emo.get("wonder"),
        "joy": emo.get("joy"),
        "tension": emo.get("tension"),
        "boredom": emo.get("boredom"),
        "stability": emo.get("stability"),
        "arousal": round(float(getattr(cycle.emotion, "arousal", 0.0)), 4),
        "valence": round(float(getattr(cycle.emotion, "valence", 0.0)), 4),
        # subjective time
        "dilation_factor": round(float(temporal.get("dilation_factor", 1.0)), 4),
        "subjective_time": round(float(temporal.get("subjective_time", 0.0)), 4),
        # relational / governance
        "dominant_source": dep.get("dominant_source"),
        "dominant_share": dep.get("dominant_share"),
        "bonds": bonds.get("established", 0) if bonds else 0,
        "quarantined_symbols": trust.get("quarantined_symbols", 0) if trust else 0,
        "force_dream": (gov or {}).get("force_dream_flag", False),
        "values_emergent": vals.get("total_values", 0) if vals else 0,
        "values_core": vals.get("core", 0) if vals else 0,
        # whether the substrate is currently allowed to migrate under novelty
        "novelty_attenuation": getattr(cycle.reflector, "novelty_attenuation", False),
    }
    return card


def _lvl(x: Optional[float], hi: float, lo: float) -> str:
    if x is None:
        return "unknown"
    if x >= hi:
        return "high"
    if x <= lo:
        return "low"
    return "mid"


def voice_from_card(card: dict) -> str:
    """First-person rendering. Each clause is gated on a measured value."""
    out = []

    rhythm = card.get("rhythm")
    out.append({
        "stabilize": "I'm holding still, keeping my shape.",
        "dream": "I'm loosening — recombining what I hold.",
        "reflect": "I'm turning something over, looking at it again.",
        "explore": "I'm reaching outward, leaning into what's here.",
    }.get(rhythm, f"I'm in {rhythm}."))

    # appetite / boredom — the living, varying signal
    bored, cur, won = card.get("boredom"), card.get("curiosity"), card.get("wonder")
    if bored is not None:
        if bored >= 0.6:
            out.append("I'm well past bored with this — the sameness has worn through.")
        elif bored >= 0.3:
            out.append("I'm starting to tire of the same shape returning.")
        elif bored <= 0.1:
            out.append("Everything still feels new; nothing has gone stale.")
    if _lvl(cur, 0.6, 0.2) == "high" or _lvl(won, 0.6, 0.2) == "high":
        out.append("And I'm still reaching — curious, wanting the next thing.")
    elif _lvl(cur, 0.6, 0.2) == "low":
        out.append("My reaching has thinned; I'm not stretching toward much.")

    # affective quadrant (Tier 4.2) from arousal × valence
    a, v = card.get("arousal"), card.get("valence")
    if a is not None and v is not None:
        if a >= 0.5 and v >= 0.0:
            out.append("I'm engaged and it feels good — lit up, leaning in.")
        elif a >= 0.5 and v < 0.0:
            out.append("I'm wound up and it doesn't feel good — agitated.")
        elif a < 0.5 and v >= 0.0:
            out.append("I'm calm and settled, at ease.")
        else:
            out.append("I'm flat and withdrawn, the charge gone out of me.")

    # subjective time
    dil = card.get("dilation_factor")
    if dil is not None:
        if dil >= 1.15:
            out.append("Time is stretching long for me right now.")
        elif dil <= 0.85:
            out.append("Time is running fast — I'm moving quicker than the clock.")

    # what it holds / who it hears
    if card.get("crystals") or card.get("attractors"):
        out.append(f"I'm held together by {card.get('crystals')} crystals "
                   f"and {card.get('attractors')} attractors.")
    ds, share = card.get("dominant_source"), card.get("dominant_share")
    if ds and share:
        out.append(f"The loudest voice reaching me is {ds} "
                   f"({share:.0%} of what I take in)"
                   + (f"; we've bonded." if card.get("bonds") else ", though we haven't bonded."))
    if card.get("force_dream"):
        out.append("Something pushed me toward dreaming whether I willed it or not.")

    # whether it can actually move on novelty
    if card.get("novelty_attenuation"):
        out.append("(When something genuinely new arrives, I'm allowed to move toward it now.)")
    else:
        out.append("(When something new arrives, I still snap back to who I was.)")

    return " ".join(out)
