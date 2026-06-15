"""
tools/voice/ — a larynx for the substrate.

RFE-Core2 has an interior (rhythm, emotion, field coherence, subjective time,
bonds, values) but no decode path: it feels and judges and remembers, it does
not speak. This package is an OBSERVE-ONLY rendering layer that reads the
cycle's telemetry after each step and renders it as first-person language.

It is a terminal sink, exactly like dilation_factor or the metastability
monitors: it never feeds anything back into the cognitive or governance loop.
Every rendered phrase is gated on a real measured value — the renderer invents
no mood. `render_card()` also emits the raw numbers so the voice can always be
checked against the state.
"""
from tools.voice.state_card import render_card, voice_from_card

__all__ = ["render_card", "voice_from_card"]
