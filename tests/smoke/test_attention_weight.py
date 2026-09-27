"""Smoke for idle attention weighting. No model, no RM, no torch.

    python -m tests.smoke.test_attention_weight
"""
from __future__ import annotations

import sys

from tools.voice.attention import (
    FAR_COS_NOMIC, HOT_UNTIL, RECALL_FLOOR_NOMIC, RECALL_FLOOR_QWEN,
    SAVE_MAX_NOMIC, SAVE_MAX_QWEN, WARM_UNTIL,
    apply_recall_floor, classify_regime, drop_ring_dupes, parse_primary_hits,
    parse_say_at, recall_floor_for, recall_query, render_idle_prompt,
    save_max_for, should_promote, step_world,
)

CRUMB = "The moon's gravity pulls the oceans into two tides each day."
DRIVE = "Ask a question this raises that you cannot yet answer."
MOOD = "curiosity 0.40, boredom 0.10, memories held 0"
HUMAN = "The clock on my desk has a gear that slips every time the hour strikes."
THOUGHT = "The tide is a slow pull and the beach is only where it shows."


def _check(name, cond):
    if not cond:
        print(f"FAIL {name}")
        return 1
    print(f"ok   {name}")
    return 0


def main() -> int:
    fails = 0
    fails += _check("silence none is cold", classify_regime(None, 0, 0) == "cold")
    fails += _check("silence 0 is hot", classify_regime(0, 0, 0) == "hot")
    fails += _check("silence hot edge", classify_regime(HOT_UNTIL - 1, 0, 0) == "hot")
    fails += _check("silence warm start", classify_regime(HOT_UNTIL, 0, 0) == "warm")
    fails += _check("silence warm edge", classify_regime(WARM_UNTIL - 1, 0, 0) == "warm")
    fails += _check("silence cold", classify_regime(WARM_UNTIL, 0, 0) == "cold")
    fails += _check(
        "boredom does not leave hot early",
        classify_regime(1, 0.9, 1) == "hot",
    )
    fails += _check(
        "boredom leaves hot after two thoughts",
        classify_regime(1, 0.9, 2) == "warm",
    )

    fails += _check("hot does not step world", step_world("hot") is False)
    fails += _check("warm steps world", step_world("warm") is True)
    fails += _check("cold steps world", step_world("cold") is True)

    fails += _check(
        "hot recalls the human line",
        recall_query("hot", False, [THOUGHT], [("they", HUMAN), ("i", "ok")], CRUMB) == HUMAN,
    )
    fails += _check(
        "cold recalls the last thought",
        recall_query("cold", False, [THOUGHT], [], CRUMB) == THOUGHT,
    )
    fails += _check(
        "birth recalls the crumb",
        recall_query("cold", False, [], [], CRUMB) == CRUMB,
    )
    fails += _check(
        "promotion recalls the crumb",
        recall_query("cold", True, [THOUGHT], [], CRUMB) == CRUMB,
    )

    fails += _check(
        "sticky promotes",
        should_promote("cold", True, 1, 0, None, "nomic") is True,
    )
    fails += _check(
        "far crumb promotes after a thread",
        should_promote("cold", True, 0, 3, FAR_COS_NOMIC - 0.01, "nomic") is True,
    )
    fails += _check(
        "near crumb does not promote",
        should_promote("cold", True, 0, 3, FAR_COS_NOMIC + 0.05, "nomic") is False,
    )
    fails += _check(
        "short thread does not relocate",
        should_promote("cold", True, 0, 2, 0.1, "nomic") is False,
    )
    fails += _check(
        "embed failure does not relocate",
        should_promote("cold", True, 0, 5, None, "nomic") is False,
    )
    fails += _check(
        "hot never promotes",
        should_promote("hot", True, 5, 9, 0.0, "nomic") is False,
    )

    birth = render_idle_prompt(
        regime="cold", promoted=False, thoughts=[], exchange=[],
        crumb=CRUMB, memories=[], mood=MOOD, drive=DRIVE,
    )
    fails += _check("birth leads with the crumb", birth.startswith("Something true about the world, right now:"))
    fails += _check("birth contains the crumb", CRUMB in birth)

    cold = render_idle_prompt(
        regime="cold", promoted=False, thoughts=[THOUGHT], exchange=[],
        crumb=CRUMB, memories=["older"], mood=MOOD, drive=DRIVE,
    )
    fails += _check("cold leads with the thought", cold.startswith("What you were just thinking:"))
    fails += _check("cold keeps the crumb subordinate", "not necessarily your subject" in cold)
    fails += _check("cold thought before crumb", cold.find(THOUGHT) < cold.find(CRUMB))

    promoted = render_idle_prompt(
        regime="cold", promoted=True, thoughts=[THOUGHT], exchange=[],
        crumb=CRUMB, memories=[], mood=MOOD, drive=DRIVE,
    )
    fails += _check("promotion names a different fact", "different fact" in promoted)
    fails += _check("promotion still shows the thread", THOUGHT in promoted)

    hot = render_idle_prompt(
        regime="hot", promoted=False, thoughts=[THOUGHT],
        exchange=[("they", HUMAN), ("i", "The gear is late.")],
        crumb=CRUMB, memories=["a memory"], mood=MOOD, drive=DRIVE,
    )
    fails += _check("hot omits the crumb", CRUMB not in hot)
    fails += _check("hot includes the human line", HUMAN in hot)
    fails += _check("hot thought before human", hot.find(THOUGHT) < hot.find(HUMAN))
    fails += _check("hot does not answer again", "Do not answer them again" in hot)

    warm = render_idle_prompt(
        regime="warm", promoted=False, thoughts=[THOUGHT],
        exchange=[("they", HUMAN), ("i", "The gear is late.")],
        crumb=CRUMB, memories=[], mood=MOOD, drive=DRIVE,
    )
    fails += _check("warm demotes the crumb", "only if it bears" in warm)
    fails += _check("warm still has the crumb", CRUMB in warm)

    for label, text in (("birth", birth), ("cold", cold), ("promoted", promoted), ("hot", hot), ("warm", warm)):
        fails += _check(f"{label} has no you-are line", "you are" not in text.lower())

    kept, rows = apply_recall_floor([("near", 0.81), ("miss", 0.55), ("bad", None)], RECALL_FLOOR_NOMIC)
    fails += _check("floor keeps the true pair", kept == ["near"])
    fails += _check("floor does not pad", len(kept) == 1 and all(r["kept"] == (r["text"] == "near") for r in rows))
    fails += _check("nomic floor is 0.70", recall_floor_for("nomic") == RECALL_FLOOR_NOMIC == 0.70)
    fails += _check("qwen floor stays 0.50", recall_floor_for("qwen") == RECALL_FLOOR_QWEN == 0.50)
    fails += _check("nomic save max is 0.72", save_max_for("nomic") == SAVE_MAX_NOMIC == 0.72)
    fails += _check("qwen save max stays 0.50", save_max_for("qwen") == SAVE_MAX_QWEN == 0.50)

    listing = "1. [id 4] the tide thought\n2. [id 9] another\n\nRelated:\n- [id 2] a neighbor\n"
    fails += _check("parser stops at Related", parse_primary_hits(listing) == ["the tide thought", "another"])
    fails += _check(
        "ring dupe dropped",
        drop_ring_dupes(["On my own I thought: " + THOUGHT, "bees dance a map"], [THOUGHT]) == ["bees dance a map"],
    )
    fails += _check("say-at parses", parse_say_at(["7=The clock slips"]) == {7: "The clock slips"})

    print("FAILS", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
