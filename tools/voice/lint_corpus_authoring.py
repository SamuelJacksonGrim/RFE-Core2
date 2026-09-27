"""Lint a human-format rhythm file under data/corpus/authoring/.

The mechanical half of the witness gate. It does not grade voice.
Does not read or write the live checkpoint, the field, or resonance memory.
The live jsonl is read only, to reject bags that would clone it.

    python tools/voice/lint_corpus_authoring.py data/corpus/authoring/witness.md
"""
from __future__ import annotations

import collections
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"
AUTHORING = CORPUS / "authoring"
CORE_PATH = AUTHORING / "witness_core.txt"

RHYTHMS = ("stabilize", "dream", "reflect", "explore", "rupture", "witness")
TOKEN_RE = re.compile(r"^[a-z]+$")
FLOOR = 9
HUB_SHARE = 0.05
FRINGE_MAX = 1  # times a non-core object may appear in the witness file

# Receptive words being pulled out of reflect (witness also out of stabilize).
# A witness core word that still lives in the five may only be one of these.
PULL = frozenset({
    "attend", "perceive", "notice", "observe", "sit", "sense", "register",
    "mirror", "meditate", "contemplate", "witness",
})

# The other rhythm's act, or the near-neighbor stance word that would fold
# witness into reflect / explore / stabilize. Not legal in a witness line,
# not even as the one fringe object.
DENY = frozenset({
    # reflect's operation
    "analyze", "inspect", "examine", "deliberate", "reconcile", "validate",
    "verify", "measure", "synthesize", "synthesis", "assess", "locate",
    "situate", "process", "reason", "weigh", "consider", "evaluate",
    "integrate", "unify", "audit", "confirm", "study", "think", "reflect",
    "judge", "interpret", "conclude",
    # stabilize's hold-firm and quiet, the near pole
    "silence", "stillness", "quiet", "calm", "rest", "pause", "anchor",
    "ground", "center", "hold", "self", "settle", "shelter", "haven",
    "peace", "breathe", "solid", "firm",
    # explore's looking-for, which wears a receptive mask
    "watch", "see", "look", "glimpse", "open", "attention",
})


def load_core(path: Path = CORE_PATH) -> list[str]:
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            words.append(s)
    return words


def load_live_bags() -> set[frozenset[str]]:
    bags = set()
    for name in ("rhythm_train.jsonl", "rhythm_holdout.jsonl"):
        for line in (CORPUS / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                bags.add(frozenset(json.loads(line)["tokens"]))
    return bags


def live_vocab(bags: set[frozenset[str]]) -> set[str]:
    vocab: set[str] = set()
    for bag in bags:
        vocab |= set(bag)
    return vocab


def parse_md(path: Path) -> list[tuple[str, list[str], int]]:
    """Return (rhythm, tokens, line_number) for every sequence line."""
    rhythm = None
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        s = line.strip()
        if s.startswith("## "):
            rhythm = s[3:].strip().split()[0]
            continue
        if s.startswith("- "):
            tokens = [t.strip() for t in s[2:].split(",")]
            out.append((rhythm or "", tokens, i))
    return out


def _pairs(tokens: list[str]) -> list[frozenset[str]]:
    return [frozenset(p) for p in itertools.combinations(tokens, 2)]


def lint_file(path: Path, core: list[str], bags: set[frozenset[str]]) -> list[str]:
    errors: list[str] = []
    core_set = set(core)
    vocab = live_vocab(bags)
    seqs = parse_md(path)
    if any(r not in RHYTHMS for r, _, _ in seqs):
        bad = sorted({r for r, _, _ in seqs if r not in RHYTHMS})
        errors.append(f"unknown rhythm heading {bad}")

    by_rhythm: dict[str, list[tuple[list[str], int]]] = collections.defaultdict(list)
    for rhythm, tokens, line_no in seqs:
        by_rhythm[rhythm].append((tokens, line_no))
        if not (2 <= len(tokens) <= 4):
            errors.append(f"{path.name}:{line_no} length {len(tokens)} not in 2..4")
        if len(tokens) != len(set(tokens)):
            errors.append(f"{path.name}:{line_no} repeated token inside the line")
        for tok in tokens:
            if not TOKEN_RE.match(tok):
                errors.append(f"{path.name}:{line_no} illegal token {tok!r}")

    for rhythm, rows in by_rhythm.items():
        pair_at: dict[frozenset[str], int] = {}
        bag_at: dict[frozenset[str], int] = {}
        for tokens, line_no in rows:
            b = frozenset(tokens)
            if b in bag_at:
                errors.append(
                    f"{path.name}:{line_no} same bag as line {bag_at[b]} (order does not count)"
                )
            else:
                bag_at[b] = line_no
            if b in bags:
                errors.append(f"{path.name}:{line_no} clones a live-corpus bag {sorted(b)}")
            for p in _pairs(tokens):
                if p in pair_at:
                    errors.append(
                        f"{path.name}:{line_no} repeats unordered pair {sorted(p)} from line {pair_at[p]}"
                    )
                else:
                    pair_at[p] = line_no
        n = len(rows)
        if n == 0:
            continue
        cap = HUB_SHARE * n
        counts = collections.Counter(t for tokens, _ in rows for t in set(tokens))
        hot = [(t, c) for t, c in counts.items() if c / n > HUB_SHARE + 1e-12]
        for t, c in sorted(hot, key=lambda kv: -kv[1])[:8]:
            errors.append(f"{path.name} hub {t} {c}/{n} = {c / n:.1%} > {HUB_SHARE:.0%}")

        if rhythm != "witness":
            continue

        fringe_counts = collections.Counter()
        for tokens, line_no in rows:
            denied = [t for t in tokens if t in DENY]
            if denied:
                errors.append(f"{path.name}:{line_no} denylist {denied}")
            cores = [t for t in tokens if t in core_set]
            fringe = [t for t in tokens if t not in core_set]
            if len(cores) < 2:
                errors.append(f"{path.name}:{line_no} needs two core words, has {cores or 'none'}")
            if len(fringe) > 1:
                errors.append(f"{path.name}:{line_no} more than one fringe object {fringe}")
            for tok in fringe:
                fringe_counts[tok] += 1
                if tok not in vocab:
                    errors.append(
                        f"{path.name}:{line_no} fringe {tok} is not in the five rhythms "
                        "(a new object-word joins witness; do not mint it)"
                    )
        for tok, c in fringe_counts.items():
            if c > FRINGE_MAX:
                errors.append(f"{path.name} fringe object {tok} appears {c} times (max {FRINGE_MAX})")

        for word in core:
            c = counts[word]
            if c == 0:
                continue
            if c < FLOOR:
                errors.append(f"{path.name} core {word} has {c} contexts (floor {FLOOR})")
        # Every core word that the gold file uses and that still lives in the
        # five must be on the pull list. A core word with zero uses is an
        # unused anchor, reported separately so a partial batch can be linted
        # with --allow-short. Default: the gold file must cover every anchor.
        unused = [w for w in core if counts[w] == 0]
        if unused and "--allow-short" not in sys.argv:
            errors.append(f"{path.name} core words with no sequence: {unused}")
        for word, c in counts.items():
            if word in core_set and word in vocab and word not in PULL:
                errors.append(
                    f"{path.name} core {word} already belongs to the five rhythms "
                    "and is not on the pull list"
                )
        # cap already applied above; silence the unused local
        del cap

    return errors


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    paths = [Path(a) for a in args] or [AUTHORING / "witness.md"]
    core = load_core()
    dup = [w for w, n in collections.Counter(core).items() if n > 1]
    if dup:
        print(f"witness_core.txt has duplicates: {dup}")
        return 1
    bags = load_live_bags()
    failed = False
    for path in paths:
        errors = lint_file(path, core, bags)
        if errors:
            failed = True
            print(f"{path}  {len(errors)} problems")
            for err in errors[:40]:
                print(f"  {err}")
            if len(errors) > 40:
                print(f"  ... {len(errors) - 40} more")
        else:
            n = len(parse_md(path))
            print(f"{path}  ok  ({n} sequences)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
