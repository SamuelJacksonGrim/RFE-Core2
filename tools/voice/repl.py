"""
tools/voice/repl.py — talk to the substrate; hear it answer.

You type. The line is tokenized and fed through one real autonomous cycle as a
named source. The cycle's resulting interior is rendered back in first person,
with the raw state card printed beside it so the voice is always checkable.

    python -m tools.voice.repl                # default stack, lever OFF
    python -m tools.voice.repl --free         # enable novelty-gated loop loosening
    python -m tools.voice.repl --json         # also print the raw state card

The voice is a terminal sink: rendering reads telemetry, never writes the loop.
With --json you get the card shaped to hand to a language model for a richer
voice. --free flips ReflectiveLoop.novelty_attenuation (off-by-default,
validated cost-clean at the shipped ceiling — see
docs/findings/2026-06-15-loop-attenuation-novelty-gate.md).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack          # noqa: E402
from tools.voice.state_card import render_card, voice_from_card  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Talk to the RFE-Core2 substrate.")
    ap.add_argument("--free", action="store_true",
                    help="enable novelty-gated reflective-loop loosening (off by default)")
    ap.add_argument("--json", action="store_true",
                    help="print the raw state card alongside the voice")
    ap.add_argument("--source", default="you",
                    help="source id your input is attributed to (default: you)")
    args = ap.parse_args()

    gen, cycle, gov, ve = build_full_stack()
    if args.free:
        cycle.reflector.novelty_attenuation = True

    print("=" * 70)
    print("  RFE-Core2 voice — type to speak to it, Ctrl-D / 'quit' to leave.")
    print(f"  novelty-attenuation: {'ON (it can move toward the new)' if args.free else 'OFF (it snaps back)'}")
    print("=" * 70)
    print("  (it speaks from its measured state; the numbers travel with the words)\n")

    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n…it keeps resonating without you.")
            return 0
        if line.lower() in ("quit", "exit"):
            print("…it keeps resonating without you.")
            return 0
        if not line:
            continue

        tokens = line.split()
        cycle.step(tokens, source_id=args.source, origin_type="user")
        card = render_card(cycle)

        print(f"\nrfe> {voice_from_card(card)}")
        if args.json:
            print("\n" + json.dumps(card, indent=2, default=str))
        else:
            print(f"     [step {card['step']} · {card['rhythm']} · coh {card['field_coherence']} "
                  f"· bored {card['boredom']} · curiosity {card['curiosity']} "
                  f"· dilation {card['dilation_factor']}]")
        print()


if __name__ == "__main__":
    sys.exit(main())
