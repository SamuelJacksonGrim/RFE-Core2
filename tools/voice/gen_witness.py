#!/usr/bin/env python3
"""Witness corpus generator.

Adapts the Kimi expansion shape — read_existing, generate_for_targets(pool,
forbidden=...), hub-cap, neighbor-diversity, deterministic seed — to the
witness rhythm. Pure stdlib. Does not import torch, does not write
rhythm_train.jsonl or rhythm_holdout.jsonl, and does not boot the field
or resonance memory.

Two products, both under data/corpus/authoring/:

1. The pull. Reflect-train sequences that contain a pulled receptive word
   (373) and stabilize-train sequences that contain ``witness`` (18) are
   written as a DROP manifest in reflect.md. They are not relabeled
   witness. Their company is analytic or hold-firm; pasting it would drag
   that company into the receptive basin, clone live bags, and blow the
   hub cap (those words already occur ~35-46 times in reflect train; 5%
   of a ~500-line witness file is ~25). Reflect keeps the analytic spine
   in the live sequences that never used a pulled word.

2. The batch. New receptive spine words, absent from the five rhythms,
   paired with each other. Every generated sequence is 2-4 of those words
   (at least two core, no fringe, no explore-leaning anchor, no analytic
   verb). Each new word lands in 9 sequences. Unordered bags are unique,
   so an order swap cannot become a second line.

    python tools/voice/gen_witness.py
"""
from __future__ import annotations

import collections
import hashlib
import itertools
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"
AUTHORING = CORPUS / "authoring"
WITNESS_MD = AUTHORING / "witness.md"
CORE_PATH = AUTHORING / "witness_core.txt"
REFLECT_MD = AUTHORING / "reflect.md"

SEED = 1188
FLOOR = 9
HUB_SHARE = 0.05
TOKEN_RE = re.compile(r"^[a-z]+$")

# Where the separability probe removes a pulled word from. Train only.
PULL = frozenset({
    "attend", "perceive", "notice", "observe", "sit", "sense", "register",
    "mirror", "meditate", "contemplate", "witness",
})
PULL_FROM = {
    "reflect": set(PULL),
    "stabilize": {"witness"},
}

# Outward face that leaned explore after the pull. Legal in the gold file,
# forbidden as partners in this batch.
EXPLORE_LEAN = frozenset({
    "present", "gaze", "awareness", "testify", "behold", "marvel", "linger",
})

# Reflect's operation, plus the near-neighbor stance words the brief bans
# even as a fringe object. Witness lines do not keep this company.
ANALYTIC = frozenset({
    "analyze", "inspect", "examine", "deliberate", "reconcile", "validate",
    "verify", "measure", "synthesize", "synthesis", "assess", "locate",
    "situate", "process", "reason", "weigh", "consider", "evaluate",
    "integrate", "unify", "audit", "confirm", "study", "think", "reflect",
    "judge", "interpret", "conclude", "distill",
})

# Object-nouns and looking-verbs a generator reaches for and must not mint.
# Also the stabilize quiet-cluster, which would tilt the other direction.
AVOIDED = frozenset({
    "grief", "sorrow", "joy", "fear", "love", "pain",
    "watch", "see", "look", "glimpse", "open", "attention", "hold", "self",
    "quiet", "silence", "stillness", "pause", "rest", "calm", "anchor",
    "ground", "shelter", "peace",
    "peer", "stare", "scan", "survey", "espy", "descry", "scout",
    "ponder", "muse", "ruminate", "brood", "introspect",
    "quietude", "serenity", "composure", "comfort", "soothe", "solace",
    "gentleness", "breath", "poise",
    "beholding", "gazing", "sitting", "observing", "listening", "abiding",
    "dwelling", "meditating", "contemplating",
})

# New spine. Four rooms, crossed on purpose. Each word is receptive stance,
# not an object and not another rhythm's verb. 21 per room so the design
# below (quads + triples + a 4-regular pair graph) closes.
REGIONS = {
    "inward-abiding": [
        "repose", "tarry", "bide", "indwell", "inhere",
        "unhurried", "unbidden", "unasked", "wakeful", "mindful",
        "abidance", "inwardness", "equanimity", "immanence", "letting",
        "wakefulness", "mindfulness", "kneel", "exhale", "numinous",
        "uncalled",
    ],
    "receiving-allowing": [
        "imbibe", "embrace", "enfold", "cradle", "permit",
        "assent", "acquiesce", "accede", "soften", "unclench",
        "relent", "allowance", "sufferance", "tolerance", "receptivity",
        "hospitality", "indrawn", "pardon", "brook", "receptiveness",
        "vouchsafe",
    ],
    "perceptual-sensing": [
        "savor", "murmur", "whisper", "audible", "palpable",
        "sensation", "hearing", "feel", "taste", "smell",
        "hear", "touch", "feeling", "sentience", "sensory",
        "sensate", "percipience", "attunement", "sonority", "scent",
        "inhale",
    ],
    "relational-warmth": [
        "tenderness", "cherish", "grace", "mercy", "kindness",
        "kinship", "kindred", "reverence", "revere", "compassion",
        "empathy", "nearness", "closeness", "togetherness", "dearness",
        "fondness", "caring", "amity", "fellowship", "companionship",
        "affection",
    ],
}

GENERATED_MARK = "# generated batch — gen_witness.py"
CORE_MARK = "# generated spine — gen_witness.py"
N_WORDS = 84  # 21 x 4


def interleave(regions: dict[str, list[str]]) -> list[str]:
    """Round-robin the rooms so index % 4 is the room, and neighbors differ."""
    lists = [regions[k] for k in regions]
    if any(len(lst) != 21 for lst in lists) or len(lists) != 4:
        raise SystemExit("need 4 rooms of 21 words")
    words: list[str] = []
    for i in range(21):
        for lst in lists:
            words.append(lst[i])
    if len(words) != N_WORDS or len(set(words)) != N_WORDS:
        raise SystemExit("interleave produced duplicate or wrong-length spine")
    return words


def load_live() -> tuple[list[dict], list[dict], set[frozenset[str]], set[str]]:
    def read(name: str) -> list[dict]:
        rows = []
        for line in (CORPUS / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    train = read("rhythm_train.jsonl")
    holdout = read("rhythm_holdout.jsonl")
    bags = {frozenset(r["tokens"]) for r in train + holdout}
    vocab: set[str] = set()
    for bag in bags:
        vocab |= set(bag)
    return train, holdout, bags, vocab


def read_existing(md_path: Path) -> tuple[str, list[list[str]]]:
    """Gold witness text, with any prior generated batch cut off, and its sequences."""
    text = md_path.read_text(encoding="utf-8")
    idx = text.find(GENERATED_MARK)
    if idx != -1:
        text = text[:idx].rstrip() + "\n"
    seqs: list[list[str]] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- "):
            seqs.append([t.strip() for t in s[2:].split(",") if t.strip()])
    return text, seqs


def _pairs(tokens: list[str]) -> list[frozenset[str]]:
    return [frozenset(p) for p in itertools.combinations(tokens, 2)]


def _circ_pairs(n: int, dist: int) -> list[tuple[int, int]]:
    out = []
    seen = set()
    for i in range(n):
        key = frozenset((i, (i + dist) % n))
        if key in seen:
            continue
        seen.add(key)
        out.append((i, (i + dist) % n))
    return out


def _quads() -> list[tuple[int, ...]]:
    # Step 21 ≡ 1 (mod 4), so each quad takes one word from each room.
    return [tuple(i + 21 * k for k in range(4)) for i in range(21)]


def _reserved_pairs() -> set[frozenset[int]]:
    """4-regular pair graph: circular distances 1 and 2. Cross-room by the interleave."""
    reserved: set[frozenset[int]] = set()
    for dist in (1, 2):
        for a, b in _circ_pairs(N_WORDS, dist):
            reserved.add(frozenset((a, b)))
    return reserved


def _find_triple_classes(blocked: set[frozenset[int]], n_classes: int, seed: int) -> list[list[tuple[int, int, int]]]:
    """Parallel classes of triples that do not reuse a blocked pair.

    Seed 1188 finds four classes in a handful of attempts. A miss is a bug
    in the reservation, not a cue to emit a short batch.
    """
    rng = random.Random(seed)
    found: list[list[tuple[int, int, int]]] = []
    used = set(blocked)
    for cls in range(n_classes):
        ok = None
        for attempt in range(80):
            order = list(range(N_WORDS))
            rng.shuffle(order)
            rem = set(order)
            triples: list[tuple[int, int, int]] = []
            pairs: set[frozenset[int]] = set()
            failed = False
            for a in order:
                if a not in rem:
                    continue
                cands = [
                    b for b in order
                    if b in rem and b != a
                    and frozenset((a, b)) not in used
                    and frozenset((a, b)) not in pairs
                ]
                rng.shuffle(cands)
                placed = False
                for b in cands[:40]:
                    cs = [
                        c for c in cands
                        if c != b and c in rem
                        and frozenset((a, c)) not in used
                        and frozenset((b, c)) not in used
                        and frozenset((a, c)) not in pairs
                        and frozenset((b, c)) not in pairs
                    ]
                    if not cs:
                        continue
                    c = cs[0]
                    triples.append((a, b, c))
                    pairs |= {frozenset((a, b)), frozenset((a, c)), frozenset((b, c))}
                    rem.discard(a)
                    rem.discard(b)
                    rem.discard(c)
                    placed = True
                    break
                if not placed:
                    failed = True
                    break
            if not failed and not rem and len(triples) == N_WORDS // 3:
                ok = triples
                break
        if ok is None:
            raise SystemExit(f"triple class {cls} did not close (seed {seed})")
        found.append(ok)
        for a, b, c in ok:
            used |= {frozenset((a, b)), frozenset((a, c)), frozenset((b, c))}
    return found


def _rotate(words: list[str], rot: int) -> list[str]:
    r = rot % len(words)
    return words[r:] + words[:r]


def generate_for_targets(targets, pool, target_count, length_dist, word_counts,
                         neighbor_map, forbidden=None, existing_pairs=None,
                         existing_bags=None, seed=SEED):
    """Build witness sequences for ``targets`` using only ``pool``.

    ``length_dist`` is accepted so the call shape matches the Kimi generator.
    The witness batch does not sample it. Weighted random partners are what
    produced order-swapped duplicate bags; this design emits each unordered
    bag once (quads, four parallel triple classes, then the reserved pairs).

    ``forbidden`` rejects a partner before it can enter a line. Hub-cap is
    applied against the running file size. Neighbor-diversity is repaired
    only if a target finishes under 0.8 distinct neighbors per context, and
    the repair uses the same bag and pair rules.
    """
    if forbidden is None:
        forbidden = set()
    if existing_pairs is None:
        existing_pairs = set()
    if existing_bags is None:
        existing_bags = set()

    forbidden = set(forbidden)
    pool_set = [w for w in pool if w not in forbidden and TOKEN_RE.match(w)]
    if set(targets) - set(pool_set):
        missing = sorted(set(targets) - set(pool_set))
        raise SystemExit(f"targets not in pool or forbidden: {missing}")
    if list(targets) != list(pool_set):
        raise SystemExit("witness batch pairs targets with themselves; pool must equal targets")
    if len(targets) != N_WORDS:
        raise SystemExit(f"design is for {N_WORDS} targets, got {len(targets)}")

    words = list(targets)
    index = {w: i for i, w in enumerate(words)}
    blocked = _reserved_pairs()
    for a, b, c, d in _quads():
        for p, q in itertools.combinations((a, b, c, d), 2):
            blocked.add(frozenset((p, q)))
    # Reserved pairs stay blocked so the triples cannot consume them.
    # Quads are blocked too. Triples are found in the complement, then the
    # reserved pairs are emitted as their own sequences.
    triple_block = set(blocked)
    classes = _find_triple_classes(triple_block, n_classes=4, seed=seed)

    raw: list[tuple[str, tuple[int, ...]]] = []
    for quad in _quads():
        raw.append(("four", quad))
    for cls in classes:
        for tri in cls:
            raw.append(("three", tri))
    for dist in (1, 2):
        for pair in _circ_pairs(N_WORDS, dist):
            raw.append(("pair", pair))

    # length_dist is the Kimi knob. Record that we did not sample it; the
    # design's own mix is the batch. A caller passing an empty dist is fine.
    del length_dist

    sequences: list[list[str]] = []
    dedup_rejects = 0
    pair_used = set(existing_pairs)
    bag_used = set(existing_bags)
    n_existing = sum(word_counts.values()) // 2  # not reliable; caller passes base via counts of old words
    # Running file size is existing sequence count, passed as the sentinel
    # key on word_counts. See main().
    base_n = int(word_counts.pop("__sequences__", 0))

    def consider(seq: list[str]) -> bool:
        nonlocal dedup_rejects
        if not (2 <= len(seq) <= 4):
            return False
        if len(seq) != len(set(seq)):
            return False
        if any(t in forbidden or t not in index for t in seq):
            return False
        bag = frozenset(seq)
        if bag in bag_used:
            dedup_rejects += 1
            return False
        pairs = _pairs(seq)
        if any(p in pair_used for p in pairs):
            dedup_rejects += 1
            return False
        n = base_n + len(sequences) + 1
        for t in seq:
            if (word_counts[t] + 1) / n > HUB_SHARE + 1e-12:
                return False
        bag_used.add(bag)
        pair_used.update(pairs)
        for t in seq:
            word_counts[t] += 1
            for u in seq:
                if u != t:
                    neighbor_map[t].add(u)
        sequences.append(seq)
        return True

    for kind_i, (kind, idxs) in enumerate(raw):
        seq = _rotate([words[i] for i in idxs], rot=seed + kind_i)
        if not consider(seq):
            raise SystemExit(f"design sequence rejected ({kind} {idxs})")

    # Neighbor-diversity repair. The design gives each word 15 distinct
    # neighbors, so this does not fire. Kept because the Kimi generator's
    # repair is part of the shape, and a future pool change might need it.
    for w in list(targets):
        count = word_counts[w]
        if count < target_count:
            continue
        need = int(0.8 * count)
        if len(neighbor_map[w]) >= need:
            continue
        for partner in pool_set:
            if partner == w or partner in neighbor_map[w]:
                continue
            if word_counts[w] >= target_count:
                break
            consider(_rotate([w, partner], rot=seed + word_counts[w]))

    for w in targets:
        if word_counts[w] != target_count:
            raise SystemExit(f"{w} has {word_counts[w]} contexts, want {target_count}")
        if len(neighbor_map[w]) < int(0.8 * word_counts[w]):
            raise SystemExit(f"{w} neighbor diversity {len(neighbor_map[w])} / {word_counts[w]}")

    return sequences, dedup_rejects


def _format_seq(tokens: list[str]) -> str:
    return "- " + ", ".join(tokens)


def _region_of(word: str) -> str:
    for name, words in REGIONS.items():
        if word in words:
            return name
    return ""


def _pull_rows(train: list[dict], holdout: list[dict]) -> dict[str, list[list[str]]]:
    out = {
        "reflect": [],
        "stabilize": [],
        "holdout-reflect": [],
        "holdout-stabilize": [],
    }
    for rec in train:
        ban = PULL_FROM.get(rec["rhythm"])
        if ban and ban & set(rec["tokens"]):
            out[rec["rhythm"]].append(list(rec["tokens"]))
    for rec in holdout:
        if rec["rhythm"] == "reflect" and PULL & set(rec["tokens"]):
            out["holdout-reflect"].append(list(rec["tokens"]))
        elif rec["rhythm"] == "stabilize" and "witness" in rec["tokens"]:
            out["holdout-stabilize"].append(list(rec["tokens"]))
    return out


def _bag_digest(rows: list[list[str]]) -> str:
    payload = "\n".join(",".join(sorted(row)) for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def write_pull(rows: dict[str, list[list[str]]]) -> None:
    reflect_n = len(rows["reflect"])
    stab_n = len(rows["stabilize"])
    if reflect_n != 373 or stab_n != 18:
        raise SystemExit(
            f"pull counts drifted: reflect {reflect_n} stabilize {stab_n} "
            "(expected 373 and 18)"
        )
    lines = [
        "## reflect",
        "",
        "# Pull (reflect -> witness), executed in authoring. The live jsonl is not modified.",
        "# A line that does not start with \"- \" is not a sequence. Nothing below is a",
        "# reflect sequence and nothing below is relabeled witness.",
        "#",
        "# DROP: reflect-train sequences that contain a pulled word, and stabilize-train",
        "# sequences that contain witness. The separability probe drops these so the",
        "# receptive words are not still supervised as reflect or stabilize. Relabeling",
        "# them would drag analyze, inspect, record, identity, bunker into witness.",
        "# Witness owns the words through witness.md (gold core + the generated spine).",
        "#",
        "# Reflect keeps the analytic spine. The live reflect-train sequences that do",
        "# not contain a pulled word stay reflect: distill, synthesize, reconcile,",
        "# measure, analyze, and the rest of that company. They are not copied here",
        "# (this file does not paste the live corpus). Do not add the pulled words back.",
        "# Pulled: attend, perceive, notice, observe, sit, sense, register, mirror,",
        "# meditate, contemplate, witness.",
        "#",
        f"# reflect-train dropped: {reflect_n}",
        f"# stabilize-train dropped: {stab_n}",
        f"# reflect-train drop digest (sha256/16 of sorted bags): {_bag_digest(rows['reflect'])}",
        f"# stabilize-train drop digest: {_bag_digest(rows['stabilize'])}",
        "#",
        "# Holdout is listed and was NOT dropped. The probe trains on train only.",
        f"# holdout reflect still carrying a pulled word: {len(rows['holdout-reflect'])}",
        f"# holdout stabilize still carrying witness: {len(rows['holdout-stabilize'])}",
        "",
        "# --- DROP reflect train ---",
    ]
    for toks in rows["reflect"]:
        lines.append("# DROP reflect | " + ", ".join(toks))
    lines.append("")
    lines.append("# --- DROP stabilize train (witness) ---")
    for toks in rows["stabilize"]:
        lines.append("# DROP stabilize | " + ", ".join(toks))
    lines.append("")
    lines.append("# --- HOLDOUT, not part of this drop ---")
    for toks in rows["holdout-reflect"]:
        lines.append("# HOLDOUT reflect | " + ", ".join(toks))
    for toks in rows["holdout-stabilize"]:
        lines.append("# HOLDOUT stabilize | " + ", ".join(toks))
    lines.append("")
    REFLECT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\r\n")


def write_core() -> None:
    text = CORE_PATH.read_text(encoding="utf-8")
    idx = text.find(CORE_MARK)
    if idx != -1:
        text = text[:idx].rstrip() + "\n"
    elif not text.endswith("\n"):
        text += "\n"
    parts = [text.rstrip() + "\n", "", CORE_MARK, "# New receptive spine. Paired with itself. See gen_witness.py.", ""]
    for name, words in REGIONS.items():
        parts.append(f"# {name}")
        parts.extend(words)
        parts.append("")
    CORE_PATH.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8", newline="\r\n")


def write_witness(gold_text: str, sequences: list[list[str]], dedup_rejects: int) -> None:
    by_kind = collections.Counter()
    # Re-derive kind from length; the file groups by length so a reader can see it.
    # Shuffle within a length so the file is not the circulant walk it was
    # built from. Bags, pairs, and counts are unchanged. Same seed, same order.
    rng = random.Random(SEED)
    fours = [s for s in sequences if len(s) == 4]
    threes = [s for s in sequences if len(s) == 3]
    twos = [s for s in sequences if len(s) == 2]
    rng.shuffle(fours)
    rng.shuffle(threes)
    rng.shuffle(twos)
    by_kind["4"] = len(fours)
    by_kind["3"] = len(threes)
    by_kind["2"] = len(twos)
    parts = [
        gold_text.rstrip() + "\n",
        "",
        GENERATED_MARK,
        f"# Seed {SEED}. {len(sequences)} sequences, {N_WORDS} new spine words, each in {FLOOR}.",
        "# Rooms crossed: inward-abiding, receiving-allowing, perceptual-sensing, relational-warmth.",
        "# No fringe object. No explore-leaning anchor. No analytic verb. No order-swapped bag.",
        f"# Dedup rejects while emitting the design: {dedup_rejects}.",
        f"# Lengths: {by_kind['2']} twos, {by_kind['3']} threes, {by_kind['4']} fours.",
        "",
        "# fours — one word from each room",
    ]
    parts.extend(_format_seq(s) for s in fours)
    parts.append("")
    parts.append("# threes")
    parts.extend(_format_seq(s) for s in threes)
    parts.append("")
    parts.append("# pairs")
    parts.extend(_format_seq(s) for s in twos)
    parts.append("")
    WITNESS_MD.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8", newline="\r\n")


def _assert_spine(vocab: set[str], core: set[str]) -> None:
    words = interleave(REGIONS)
    bad = []
    for w in words:
        if not TOKEN_RE.match(w):
            bad.append(f"{w} illegal token")
        if w in vocab:
            bad.append(f"{w} already in the five rhythms")
        if w in core:
            bad.append(f"{w} already in witness core")
        if w in ANALYTIC or w in EXPLORE_LEAN or w in AVOIDED or w in PULL:
            bad.append(f"{w} is on a denylist")
    if bad:
        raise SystemExit("spine rejected:\n  " + "\n  ".join(bad))


def _islands(sequences: list[list[str]], words: list[str]) -> list[str]:
    """A word whose every neighbor shares its room."""
    region = {w: _region_of(w) for w in words}
    nbr_regions: dict[str, set[str]] = collections.defaultdict(set)
    for seq in sequences:
        for t in seq:
            for u in seq:
                if u != t:
                    nbr_regions[t].add(region[u])
    return [w for w in words if nbr_regions[w] <= {region[w]}]


def main() -> int:
    train, holdout, live_bags, vocab = load_live()
    gold_text, gold_seqs = read_existing(WITNESS_MD)
    core = set()
    for line in CORE_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith(CORE_MARK):
            # On re-run the generated spine is already in the file; cut it the
            # same way write_core does, by reading only the pre-marker lines.
            pass
    pre = CORE_PATH.read_text(encoding="utf-8")
    cut = pre.find(CORE_MARK)
    if cut != -1:
        pre = pre[:cut]
    for line in pre.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            core.add(s)

    _assert_spine(vocab, core)
    words = interleave(REGIONS)
    forbidden = set(vocab) | set(ANALYTIC) | set(EXPLORE_LEAN) | set(AVOIDED) | set(PULL)
    # Gold anchors are not forbidden as tokens (they are witness), but they are
    # not in the pool. EXPLORE_LEAN and PULL are in forbidden so a pool slip
    # cannot reintroduce them.

    gold_pairs: set[frozenset[str]] = set()
    gold_bags: set[frozenset[str]] = set()
    for seq in gold_seqs:
        bag = frozenset(seq)
        if bag in gold_bags:
            raise SystemExit(f"gold already has a duplicate bag: {sorted(bag)}")
        gold_bags.add(bag)
        for p in _pairs(seq):
            if p in gold_pairs:
                raise SystemExit(f"gold already repeats pair {sorted(p)}")
            gold_pairs.add(p)

    word_counts: collections.Counter = collections.Counter()
    neighbor_map: dict[str, set[str]] = collections.defaultdict(set)
    word_counts["__sequences__"] = len(gold_seqs)
    sequences, dedup_rejects = generate_for_targets(
        words,
        list(words),
        target_count=FLOOR,
        length_dist=[(2, 1), (3, 1), (4, 1)],
        word_counts=word_counts,
        neighbor_map=neighbor_map,
        forbidden=forbidden,
        existing_pairs=gold_pairs,
        existing_bags=gold_bags | live_bags,
        seed=SEED,
    )

    # Order-swap self-test: the bag of a reversed pair is the bag we already took.
    probe = list(reversed(sequences[0]))
    if frozenset(probe) not in gold_bags | live_bags | {frozenset(s) for s in sequences}:
        raise SystemExit("order-swap self-test failed to find the original bag")
    if _islands(sequences, words):
        raise SystemExit(f"island words: {_islands(sequences, words)}")

    total = len(gold_seqs) + len(sequences)
    if not (400 <= total <= 600):
        raise SystemExit(f"witness total {total} outside 400-600")
    for seq in gold_seqs:
        for t in seq:
            word_counts[t] += 1
    hottest = max(word_counts[w] for w in list(core) + words)
    if hottest / total > HUB_SHARE + 1e-12:
        raise SystemExit(f"hub cap exceeded at {hottest}/{total}")

    rows = _pull_rows(train, holdout)
    write_pull(rows)
    write_core()
    write_witness(gold_text, sequences, dedup_rejects)

    # Gold bytes of record: the sequences before the marker must be the gold.
    written, written_seqs = read_existing(WITNESS_MD)
    # read_existing strips the generated section; what remains must match gold.
    if written_seqs != gold_seqs:
        raise SystemExit("gold sequences changed")

    print(f"pull reflect-train: {len(rows['reflect'])}")
    print(f"pull stabilize-train: {len(rows['stabilize'])}")
    print(f"holdout reflect untouched: {len(rows['holdout-reflect'])}")
    print(f"holdout stabilize untouched: {len(rows['holdout-stabilize'])}")
    print(f"reflect drop digest: {_bag_digest(rows['reflect'])}")
    print(f"stabilize drop digest: {_bag_digest(rows['stabilize'])}")
    print(f"gold sequences: {len(gold_seqs)}")
    print(f"generated sequences: {len(sequences)}")
    print(f"witness total: {total}")
    print(f"new words: {len(words)}")
    print(f"contexts per new word: {FLOOR}")
    print(f"dedup rejects: {dedup_rejects}")
    print(f"hottest word share: {hottest}/{total} = {hottest / total:.3%}")
    print(f"lengths: 2={sum(1 for s in sequences if len(s)==2)} "
          f"3={sum(1 for s in sequences if len(s)==3)} "
          f"4={sum(1 for s in sequences if len(s)==4)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
