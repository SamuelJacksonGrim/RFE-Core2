#!/usr/bin/env python3
"""
tools/voice/gen_vocab.py — grow the vocabulary inside the four active rhythms.

Adapted from the stdlib expander (read_existing / generate_for_targets /
hub cap / neighbor diversity / a fixed seed). Two bugs in that expander are
closed here:

  * It appended `target_count` fresh sequences per word and did not remember
    unordered pairs, so the same two tokens came back swapped. That is the
    order-swapped bag. `used_bags` and `used_pairs` refuse it.
  * It had no hub cap inside the loop, so counts ran away and the only fix
    was thousands of extra lines. This stops at the quota.

Nuance is new distinctions inside explore, dream, stabilize, and rupture.
Not a new rhythm, and not a register split (technical versus slang is the
mouth's job). Reflect and witness are not written. The live jsonl is read
only. No GPU, no checkpoint, no field.

Run from the repo root:

    python tools/voice/gen_vocab.py
    python tools/voice/gen_vocab.py --dry-run
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"
AUTHORING = CORPUS / "authoring"
CORE_PATH = AUTHORING / "witness_core.txt"

RHYTHMS = ("rupture", "explore", "dream", "stabilize")  # constrained first
ACTIVE = ("explore", "dream", "stabilize", "rupture")
TOKEN_RE = re.compile(r"^[a-z]+$")

SEED = 1188
FLOOR = 9                 # contexts a new word must earn
STITCH_CONTEXTS = 2       # existing signature neighbors, for basin attachment
HUB_SHARE = 0.05          # lint cap: count / sequences in the file
HUB_TARGET = 0.042        # stay off the ceiling; retry with shorter lines if over
STITCH_CAP = 12           # hard per-file cap on an existing stitch word
SAME_REGION_MIN = 1
SAME_REGION_MAX = 2

# Closed-class glue. Shared by function. It does not carry a basin, and the
# busiest of them already sit on the context cap.
GLUE = frozenset({
    "a", "across", "against", "along", "and", "between", "beyond", "from",
    "in", "into", "is", "of", "the", "through", "to", "toward", "with",
    "within", "beneath",
})

# Explore's search edge and entropy edge. Rupture stayed separable only once
# its vocabulary got off this set. New rupture words are refused if they land
# here, and so is any token that already lives in explore.
EXPLORE_SEARCH = frozenset({
    "find", "seek", "question", "wonder", "discover", "chase", "curiosity",
    "explore", "novelty", "search", "hunt", "pursue", "uncover", "scout",
    "forage", "reconnoiter", "prospect", "canvass", "delve", "query",
    "conjecture", "hypothesis", "speculation", "surmise", "postulate",
})
EXPLORE_ENTROPY = frozenset({
    "chaos", "break", "scatter", "entropy", "pressure", "diverge",
    "turbulence", "wild", "flux", "bifurcate", "fork", "swerve", "noise",
    "atomize", "jolt",
})

# Reflect's act, and the receptive words witness now owns. Not available as
# new tokens in these four rhythms.
REFLECT_ACT = frozenset({
    "analyze", "inspect", "examine", "deliberate", "reconcile", "validate",
    "verify", "measure", "synthesize", "synthesis", "assess", "locate",
    "situate", "process", "reason", "weigh", "consider", "evaluate",
    "integrate", "unify", "audit", "confirm", "study", "think", "reflect",
    "judge", "interpret", "conclude",
})
PULL = frozenset({
    "attend", "perceive", "notice", "observe", "sit", "sense", "register",
    "mirror", "meditate", "contemplate", "witness",
})
NEAR_STANCE = frozenset({
    "watch", "hold", "self", "attention", "quiet", "silence", "stillness",
    "pause", "rest", "calm", "see", "look", "glimpse", "open",
})

# Words considered and not used. The reason is the other rhythm's motion,
# a thin duplicate of a word already kept, or a register costume.
DROPPED = {
    "founder": "reads as stabilize's founder (the one who establishes), not only the sinking",
    "sally": "a sudden rush; that kinetic is rupture's, and burst is already rupture",
    "incubate": "holding until ready is stabilize's hold, not dream's making",
    "quicken": "also 'make faster', which is kinetic rather than generative",
    "metamorphose": "a respelling of explore's transform",
    "recompose": "compose is dream's making",
    "continuance": "extends continuity, which is already shared across rhythms",
    "unattested": "attest and testify are witness",
    "unmapped": "too thin beside uncharted",
    "unsounded": "too thin beside unplumbed",
    "calcify": "hardening toward stabilize's solidify",
    "petrify": "turning to stone is stabilize's hold",
    "atomize": "explore's scatter / entropy edge",
    "jolt": "explore's lurch, not a rupture failure mode",
    "wonderland": "wonder is explore",
    "halcyon": "stabilize's calm, wearing a dream costume",
    "laminate": "too close to rupture's delaminate to leave dream clean",
    "bearing": "ambiguous with forbear / carrying, which is stabilize",
    "quandary": "an inward knot; that is reflect, not the outward venture",
    "enigma": "an inward knot; reflect's object, not explore's going",
    "puzzlement": "inward; reflect",
    "premise": "a claim already laid down; reflect's starting point",
    "spallation": "too thin beside rupture's existing spall",
    "nightscape": "template beside the existing dreamscape",
    "seascape": "template beside the existing dreamscape",
    "mythscape": "template beside the existing dreamscape",
    "wardship": "too thin beside guardianship",
    "bower": "a shelter; stabilize already owns haven and shelter",
    "inference": "reflect's conclusion, not the outward guess",
    "renew": "explore already owns new; the token would lean that way",
}

# Kept, and named, because a reader could file them under the neighbor rhythm.
# They stay because the primary motion is this rhythm's, and they get no
# company from the other one (a new token has no contradictory label).
WATCHED = {
    "hypothesis": "explore: the outward testable guess, not reflect's verify",
    "speculation": "explore: the free guess flung outward",
    "postulate": "explore: a stake set in the unknown",
    "composure": "stabilize: the held balance, not dream's compose",
    "poise": "stabilize: the balance point, not dream's grace",
    "cohere": "stabilize: the verb, beside the already-shared noun coherence",
    "oasis": "dream: a place that appears, not stabilize's haven",
    "excoriate": "rupture: surface stripped; the verbal sense is rupture's smear, not reflect",
    "desolation": "rupture: the place after, beside the existing verb desolate",
    "reknit": "stabilize: pulling the hold back together; weave stays dream/reflect",
}

# region -> words. 13 x 4 per rhythm. Distinctions, not a synonym mill.
# Order inside a region is stable; generation interleaves regions.
REGIONS: dict[str, dict[str, list[str]]] = {
    "explore": {
        # shape of the going-out, not the wobble (swerve/lurch already exist)
        "venture": [
            "foray", "sortie", "expedition", "itinerary", "detour", "excursion",
            "traversal", "wayfaring", "jaunt", "trek", "odyssey", "beeline", "gambit",
        ],
        # grades of unknown the current unknown/unfamiliar/far collapse together
        "grades": [
            "uncharted", "unplumbed", "unnamed", "unasked", "untried", "trackless",
            "remote", "outlying", "horizon", "vicinity", "yonder", "afar", "hinterland",
        ],
        # how a venture is aimed; gauge/calibrate already measure force, not direction
        "bearing": [
            "azimuth", "leeway", "heading", "waypoint", "meridian", "orienteer",
            "landmark", "sextant", "quadrant", "locus", "sightline", "tangent", "compass",
        ],
        # the reach before the find; question/wonder exist, these are finer
        "tentative": [
            "conjecture", "surmise", "postulate", "inkling", "hunch", "supposition",
            "hypothesis", "speculation", "query", "prospect", "reconnoiter", "canvass", "delve",
        ],
    },
    "dream": {
        # how something is generated; create/invent/compose already exist as one blob
        "making": [
            "improvise", "extemporize", "fabulate", "confabulate", "extrapolate",
            "interpolate", "contrive", "germinate", "engender", "transfigure",
            "transmute", "reimagine", "overlay",
        ],
        # kinds of image; phantom/chimera/wraith already exist
        "image": [
            "reverie", "daydream", "fantasia", "mirage", "apparition", "afterimage",
            "simulacrum", "figment", "tableau", "vignette", "panorama", "cameo", "illusion",
        ],
        # the unreal place, finer than utopia/dystopia/arcadia/dreamscape
        "place": [
            "inscape", "mindscape", "dreamland", "otherworld", "dreamtime", "elsewhere",
            "nowhere", "faerie", "cloudland", "idyll", "dreamworld", "oasis", "fabled",
        ],
        # joining that is not fuse (fuse is shared with rupture) and not blend/merge
        "joining": [
            "interleave", "juxtapose", "entwine", "braid", "montage", "collage",
            "palimpsest", "hybridize", "alloy", "tessellate", "interlace", "inlay", "mingle",
        ],
    },
    "stabilize": {
        # members that carry, as against the wall-words (bulwark, rampart, bastion)
        "support": [
            "undergird", "buttress", "ballast", "mooring", "keystone", "linchpin",
            "footing", "plinth", "stanchion", "girder", "trestle", "underlay", "strut",
        ],
        # the shape of the balance; balance/harmony/steady already exist
        "equilibrium": [
            "equilibrium", "equipoise", "congruity", "proportion", "symmetry", "poise",
            "evenness", "aplomb", "composure", "equanimity", "steadiness", "constancy",
            "imperturbability",
        ],
        # holding across time; persistence/continuity/preserve already exist
        "tenure": [
            "tenure", "custody", "stewardship", "safekeeping", "perpetuity", "perennial",
            "longevity", "subsistence", "upkeep", "husbandry", "guardianship", "safeguard",
            "stalwart",
        ],
        # the hold put back, not the first settling (settle/anchor already exist)
        "recovery": [
            "reestablish", "resettle", "reknit", "cohere", "buffer", "dampen",
            "righting", "regain", "restore", "repair", "mend", "redress", "rehabilitate",
        ],
    },
    "rupture": {
        # coming-apart that is not the smash-verb blob (shatter/crack/split/tear)
        "apart": [
            "disintegrate", "crumble", "unravel", "unspool", "deliquesce", "pulverize",
            "comminute", "decrepitate", "implode", "buckle", "splinter", "sunder", "rive",
        ],
        # what the break leaves; ruin/ash/residue already exist as one blob
        "after": [
            "wreckage", "debris", "rubble", "detritus", "aftermath", "ruination",
            "desolation", "remnant", "wrack", "carnage", "shambles", "slag", "cinder",
        ],
        # failure mechanics; not explore's swerve/push/pressure
        "force": [
            "wrench", "concuss", "torsion", "tensile", "overload", "shockwave",
            "cavitation", "avulse", "deflagrate", "detonate", "whiplash", "topple", "capsize",
        ],
        # spoiling that is not the smear list (defile/taint/pollute)
        "spoil": [
            "corrode", "erode", "abrade", "oxidize", "putrefy", "fester", "necrose",
            "gangrene", "rust", "embrittle", "leach", "excoriate", "molder",
        ],
    },
}

# Existing single-rhythm signature words. One may sit in a line so the new
# token is pulled into the basin that already exists. Not the hottest words
# (settle, uncover, generate, form) and not a word shared with another rhythm.
STITCHES: dict[str, list[str]] = {
    "explore": [
        "frontier", "strange", "unexpected", "unfamiliar", "widen", "reach",
        "branch", "far", "outside", "flux", "fathom", "curiosity", "novel",
        "grope", "gauge", "pursue",
    ],
    "dream": [
        "conjure", "imagine", "bloom", "envision", "trance", "phantom",
        "latent", "dormant", "manifest", "summon", "hallucinate", "dreamscape",
        "implicit", "submerged", "recombine", "chimera",
    ],
    "stabilize": [
        "foundation", "firm", "steady", "root", "integrity", "preserve",
        "balance", "anchor", "structure", "invariant", "persistence", "clarity",
        "trust", "secure", "cement", "resolve",
    ],
    "rupture": [
        "abyss", "shatter", "cleave", "decay", "rift", "shear", "spall",
        "delaminate", "fatigue", "creep", "fissure", "sever", "ash", "void",
        "breach", "char",
    ],
}

LENGTH_MIX = [(2, 72), (3, 24), (4, 4)]
LENGTH_PAIR = [(2, 1)]


def _pairs(tokens: list[str]) -> list[frozenset[str]]:
    return [frozenset(p) for p in itertools.combinations(tokens, 2)]


def load_core(path: Path = CORE_PATH) -> set[str]:
    words = set()
    if not path.exists():
        return words
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            words.add(s)
    return words


def read_existing(path: str | Path):
    """Read a markdown rhythm file or a jsonl corpus.

    Returns (raw_text, sequences_by_rhythm, vocab_by_rhythm). Markdown lines
    that do not start with '- ' are ignored. A jsonl row is {tokens, rhythm}.
    This is the expander's reader, pointed at either shape.
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    seqs = {r: [] for r in ("stabilize", "dream", "reflect", "explore", "rupture", "witness")}
    vocab = {r: set() for r in seqs}
    if path.suffix == ".jsonl":
        for line in raw.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rhythm = row["rhythm"]
            toks = list(row["tokens"])
            seqs.setdefault(rhythm, []).append(toks)
            vocab.setdefault(rhythm, set()).update(toks)
        return raw, seqs, vocab

    cur = None
    for line in raw.splitlines():
        s = line.strip()
        m = re.match(r"^##\s+(\w+)", s)
        if m:
            cur = m.group(1)
            continue
        if not s.startswith("- ") or cur is None:
            continue
        toks = [t.strip() for t in s[2:].split(",") if t.strip()]
        seqs.setdefault(cur, []).append(toks)
        vocab.setdefault(cur, set()).update(toks)
    return raw, seqs, vocab


def load_train() -> list[dict]:
    records = []
    for line in (CORPUS / "rhythm_train.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_live():
    """Train + holdout, read only. Bags, vocab, per-rhythm membership."""
    records = []
    for name in ("rhythm_train.jsonl", "rhythm_holdout.jsonl"):
        text = (CORPUS / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip():
                records.append(json.loads(line))
    bags = set()
    vocab: dict[str, set[str]] = collections.defaultdict(set)
    for row in records:
        bags.add(frozenset(row["tokens"]))
        for t in row["tokens"]:
            vocab[t].add(row["rhythm"])
    return records, bags, vocab


def _authoring_tokens(name: str) -> set[str]:
    path = AUTHORING / name
    if not path.exists():
        return set()
    _, seqs, _ = read_existing(path)
    out = set()
    for rows in seqs.values():
        for toks in rows:
            out.update(toks)
    return out


def _interleave(regions: dict[str, list[str]]) -> list[str]:
    names = list(regions)
    width = len(regions[names[0]])
    out = []
    for i in range(width):
        for name in names:
            out.append(regions[name][i])
    return out


def _region_of(regions: dict[str, list[str]]) -> dict[str, str]:
    out = {}
    for name, words in regions.items():
        for w in words:
            out[w] = name
    return out


def generate_for_targets(
    targets,
    pool,
    target_count,
    length_dist,
    word_counts,
    neighbor_map,
    forbidden=None,
    used_bags=None,
    used_pairs=None,
    max_count=None,
    regions=None,
    rng=None,
    fallback_pool=None,
    stitch_set=None,
    stats=None,
):
    """Add contexts until each target has `target_count`, or stop if it cannot
    be done without a repeated pair, a repeated bag, or a word past its cap.

    `pool` is the partner vocabulary. `forbidden` tokens are never written.
    Bags are frozensets, so an order swap of a bag already used is refused.
    Unordered pairs are unique. `length_dist` is a list of (length, weight).

    Returns the new sequences in the order they were committed (already rotated,
    so the target is not always first).
    """
    if forbidden is None:
        forbidden = set()
    if used_bags is None:
        used_bags = set()
    if used_pairs is None:
        used_pairs = set()
    if max_count is None:
        max_count = {}
    if regions is None:
        regions = {}
    if rng is None:
        rng = random.Random(SEED)
    if stitch_set is None:
        stitch_set = set()
    if stats is None:
        stats = collections.Counter()

    forbidden = set(forbidden)
    target_set = set(targets)
    pool = [w for w in pool if w not in forbidden and TOKEN_RE.match(w)]
    fallback_pool = [w for w in (fallback_pool or []) if w not in forbidden and TOKEN_RE.match(w)]

    def cap_of(word):
        if word in max_count:
            return max_count[word]
        if word in target_set:
            return target_count
        return STITCH_CAP

    def region_penalty(focal, other):
        fr = regions.get(focal)
        ur = regions.get(other)
        if not fr or not ur:
            return 0
        n_same = sum(1 for n in neighbor_map[focal] if regions.get(n) == fr)
        same = ur == fr
        if n_same < SAME_REGION_MIN:
            return 0 if same else 1
        if n_same >= SAME_REGION_MAX:
            return 1 if same else 0
        return 1 if same else 0

    def rank(focal, candidates, allow_finished):
        ranked = []
        for u in candidates:
            if u == focal or u in forbidden:
                continue
            if u in neighbor_map[focal]:
                stats["skip_already_neighbor"] += 1
                continue
            if word_counts[u] >= cap_of(u):
                stats["skip_cap"] += 1
                continue
            if u in target_set and word_counts[u] >= target_count and not allow_finished:
                stats["skip_quota"] += 1
                continue
            if u in target_set:
                balance = -(target_count - word_counts[u])
            else:
                balance = word_counts[u]
            ranked.append((region_penalty(focal, u), balance, rng.random(), u))
        ranked.sort()
        return [u for *_rest, u in ranked]

    def try_build(focal, length, candidates, allow_finished):
        # At most one existing stitch in a line. Two stitches would be an
        # old-old pair, and those are already hot in the live corpus.
        def over_region(seq):
            # Every participant, not only the focal. A triple can make two
            # partners same-region neighbors of each other without the focal
            # sharing that region, and the partner may already be at the cap.
            for w in seq:
                fr = regions.get(w)
                if not fr:
                    continue
                mates = [m for m in seq if m != w and regions.get(m) == fr]
                existing = sum(1 for nb in neighbor_map[w] if regions.get(nb) == fr)
                if existing + len(mates) > SAME_REGION_MAX:
                    return True
            return False

        ranked = rank(focal, candidates, allow_finished)
        partners: list[str] = []
        for u in ranked:
            trial = partners + [u]
            seq = [focal] + trial
            if len(set(seq)) != len(seq):
                continue
            if sum(1 for w in seq if w in stitch_set) > 1:
                stats["skip_two_stitches"] += 1
                continue
            if over_region(seq):
                stats["skip_region"] += 1
                continue
            pairs = _pairs(seq)
            if any(p in used_pairs for p in pairs):
                stats["skip_pair"] += 1
                continue
            bag = frozenset(seq)
            if bag in used_bags:
                stats["skip_bag"] += 1
                continue
            if any(word_counts[w] + 1 > cap_of(w) for w in seq):
                stats["skip_cap"] += 1
                continue
            partners.append(u)
            if len(partners) == length - 1:
                return seq
        return None

    def choose_length(needy_n):
        lengths = [n for n, _w in length_dist]
        weights = [w for _n, w in length_dist]
        rolled = rng.choices(lengths, weights=weights, k=1)[0]
        # A sequence of length L needs L needy words, unless we are about to
        # fall back to a stitch (handled by the caller).
        return max(2, min(rolled, needy_n))

    def commit(seq):
        bag = frozenset(seq)
        used_bags.add(bag)
        for p in _pairs(seq):
            used_pairs.add(p)
        for w in seq:
            word_counts[w] += 1
            for u in seq:
                if u != w:
                    neighbor_map[w].add(u)
        rot = rng.randrange(len(seq))
        return seq[rot:] + seq[:rot]

    made = []
    steps = 0
    limit = max(50, len(targets) * target_count * 8)
    while steps < limit:
        steps += 1
        needy = [w for w in targets if word_counts[w] < target_count and w not in forbidden]
        if not needy:
            break
        needy.sort(key=lambda w: (-(target_count - word_counts[w]), w))
        top_def = target_count - word_counts[needy[0]]
        top = [w for w in needy if target_count - word_counts[w] == top_def]
        focal = top[rng.randrange(len(top))]
        seq = None
        if len(needy) >= 2:
            length = choose_length(len(needy))
            for L in (length, 3, 2):
                if L < 2 or L > len(needy):
                    continue
                seq = try_build(focal, L, pool, allow_finished=False)
                if seq:
                    break
        if seq is None and fallback_pool:
            seq = try_build(focal, 2, fallback_pool, allow_finished=False)
        if seq is None:
            # Last resort: one partner already at quota, still under its cap.
            seq = try_build(focal, 2, pool, allow_finished=True)
        if seq is None:
            stats["stuck"] += 1
            # Do not spin on the same focal. If a full pass sticks, stop.
            if stats["stuck"] > len(targets):
                break
            continue
        stats["stuck"] = 0
        made.append(commit(seq))
    return made


def _check_lists():
    errors = []
    seen = {}
    for rhythm, regions in REGIONS.items():
        if len(regions) != 4:
            errors.append(f"{rhythm} has {len(regions)} regions, want 4")
        for name, words in regions.items():
            if len(words) != 13:
                errors.append(f"{rhythm}/{name} has {len(words)} words, want 13")
            for w in words:
                if not TOKEN_RE.match(w):
                    errors.append(f"illegal token {w}")
                if w in seen:
                    errors.append(f"{w} in {rhythm}/{name} and {seen[w]}")
                seen[w] = f"{rhythm}/{name}"
                if w in DROPPED:
                    errors.append(f"{w} is both curated and dropped")
    for rhythm, words in STITCHES.items():
        if len(set(words)) != len(words):
            errors.append(f"duplicate stitch in {rhythm}")
        for w in words:
            if w in seen:
                errors.append(f"stitch {w} collides with new word {seen[w]}")
    return errors


def _block_sets(live_vocab, core):
    witness_md = _authoring_tokens("witness.md")
    reflect_md = _authoring_tokens("reflect.md")
    blocked = set()
    blocked |= core
    blocked |= PULL
    blocked |= NEAR_STANCE
    blocked |= REFLECT_ACT
    blocked |= GLUE
    blocked |= witness_md
    blocked |= reflect_md
    blocked |= set(live_vocab)
    return blocked, witness_md, reflect_md


def prepare(live_vocab, core):
    """Drop curated words that collide. Return per-rhythm new words, regions, fights."""
    blocked, _w, _r = _block_sets(live_vocab, core)
    fights = []
    new_words = {}
    region_maps = {}
    claimed = set()
    # Rupture first, then explore: rupture must not receive explore's words.
    for rhythm in RHYTHMS:
        kept_regions = {}
        for name, words in REGIONS[rhythm].items():
            kept = []
            for w in words:
                why = None
                if w in claimed:
                    why = f"already claimed by another rhythm"
                elif w in blocked:
                    homes = sorted(live_vocab.get(w, ()))
                    why = "blocked"
                    if homes:
                        why = "already in " + ",".join(homes)
                    elif w in core or w in PULL:
                        why = "witness/receptive"
                    elif w in REFLECT_ACT:
                        why = "reflect's act"
                    elif w in GLUE:
                        why = "glue"
                elif rhythm == "rupture" and w in (EXPLORE_SEARCH | EXPLORE_ENTROPY):
                    why = "explore search/entropy edge"
                if why:
                    fights.append((rhythm, w, why))
                    continue
                kept.append(w)
                claimed.add(w)
            kept_regions[name] = kept
        new_words[rhythm] = _interleave(kept_regions)
        region_maps[rhythm] = _region_of(kept_regions)
    return new_words, region_maps, fights


def _stitch_ok(rhythm, word, live_vocab):
    homes = live_vocab.get(word, set())
    if homes != {rhythm}:
        return False
    if word in GLUE or word in PULL or word in NEAR_STANCE or word in REFLECT_ACT:
        return False
    if rhythm == "rupture" and (
        word in EXPLORE_SEARCH or word in EXPLORE_ENTROPY or "explore" in homes
    ):
        return False
    return True


def build_rhythm(rhythm, new_words, region_map, stitches, live_bags, rng, length_dist):
    """Same as generate_rhythm but returns the ordered sequences.

    Split out so the bag set is threaded correctly and the return value is
    the lines, not a second bookkeeping pass.
    """
    word_counts = collections.Counter()
    neighbor_map = collections.defaultdict(set)
    used_bags = set(live_bags)
    used_pairs: set[frozenset[str]] = set()
    stats = collections.Counter()
    stitch_set = set(stitches)
    targets = list(new_words)

    cap1 = {w: STITCH_CONTEXTS for w in targets}
    for s in stitches:
        cap1[s] = STITCH_CAP
    first = generate_for_targets(
        targets, stitches, STITCH_CONTEXTS, LENGTH_PAIR,
        word_counts, neighbor_map, forbidden=set(),
        used_bags=used_bags, used_pairs=used_pairs, max_count=cap1,
        regions={}, rng=rng, stitch_set=stitch_set, stats=stats,
    )
    cap2 = {w: FLOOR + 1 for w in targets}
    for s in stitches:
        cap2[s] = STITCH_CAP
    second = generate_for_targets(
        targets, list(targets), FLOOR, length_dist,
        word_counts, neighbor_map, forbidden=set(),
        used_bags=used_bags, used_pairs=used_pairs, max_count=cap2,
        regions=region_map, rng=rng, fallback_pool=list(stitches),
        stitch_set=stitch_set, stats=stats,
    )
    seqs = first + second
    # Phase 1 is every stitch pair, then phase 2. Written that way the file
    # opens as one shape repeated. Scatter them; the bags do not change.
    random.Random(f"{SEED}:{rhythm}:order").shuffle(seqs)
    return seqs, word_counts, neighbor_map, stats, used_pairs


def _header(path: Path, rhythm: str) -> str:
    if not path.exists():
        return (
            f"## {rhythm}\n\n"
            "# New sequences only. Do not paste the live corpus into this file.\n"
            "# Read AUTHORING_BRIEF.md and boundary_map.md before adding a line.\n"
            "# Lines that do not start with \"- \" are ignored."
        )
    kept = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- ") or line.startswith("# vocab-growth"):
            break
        kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept)


def _same_region_fraction(word, neighbor_map, region_map):
    region = region_map.get(word)
    nbrs = [n for n in neighbor_map[word] if n in region_map]
    if not nbrs or not region:
        return 0.0, 0
    same = sum(1 for n in nbrs if region_map.get(n) == region)
    return same / len(nbrs), same


def audit_rhythm(rhythm, seqs, new_words, region_map, stitches, word_counts, neighbor_map, live_vocab, explore_words):
    errors = []
    notes = []
    n = len(seqs)
    bags = [frozenset(s) for s in seqs]
    if len(bags) != len(set(bags)):
        errors.append(f"{rhythm}: duplicate bag (order counts as the same)")
    pair_at = {}
    for seq in seqs:
        if not (2 <= len(seq) <= 4):
            errors.append(f"{rhythm}: bad length {seq}")
        if len(seq) != len(set(seq)):
            errors.append(f"{rhythm}: repeated token {seq}")
        for t in seq:
            if not TOKEN_RE.match(t):
                errors.append(f"{rhythm}: illegal token {t}")
        if sum(1 for t in seq if t in stitches) > 1:
            errors.append(f"{rhythm}: two stitches in {seq}")
        for p in _pairs(seq):
            key = tuple(sorted(p))
            if key in pair_at:
                errors.append(f"{rhythm}: repeated pair {key}")
            pair_at[key] = seq
        # A line of only old words would be able to clone a live bag.
        if not any(t in new_words for t in seq):
            errors.append(f"{rhythm}: line with no new word {seq}")

    counts = collections.Counter(t for seq in seqs for t in set(seq))
    if n:
        hot = [(t, c) for t, c in counts.items() if c / n > HUB_SHARE + 1e-12]
        for t, c in hot:
            errors.append(f"{rhythm}: hub {t} {c}/{n} = {c / n:.1%}")
        over_target = [(t, c) for t, c in counts.items() if t in new_words and c / n > HUB_TARGET + 1e-12]
        if over_target:
            notes.append("over internal share target " + ", ".join(f"{t} {c}/{n}" for t, c in over_target[:6]))

    under = [w for w in new_words if counts[w] < FLOOR]
    if under:
        errors.append(f"{rhythm}: {len(under)} words under floor {FLOOR}: {under[:8]}")

    low_div = []
    for w in new_words:
        c = counts[w]
        nbr = len(neighbor_map[w])
        if c >= FLOOR and nbr < 0.8 * c:
            low_div.append((w, nbr, c))
    if low_div:
        errors.append(f"{rhythm}: low neighbor diversity {low_div[:6]}")

    region_hi = []
    region_lo = []
    for w in new_words:
        frac, same = _same_region_fraction(w, neighbor_map, region_map)
        if same > SAME_REGION_MAX:
            region_hi.append((w, same))
        if same < SAME_REGION_MIN:
            region_lo.append(w)
    if region_hi:
        errors.append(f"{rhythm}: same-region island {region_hi[:6]}")
    if region_lo:
        errors.append(f"{rhythm}: {len(region_lo)} words with no same-region neighbor, e.g. {region_lo[:6]}")

    # Separability of the written lines.
    new_set = set(new_words)
    if rhythm == "rupture":
        leaked = []
        for seq in seqs:
            for t in seq:
                if t in explore_words or t in EXPLORE_SEARCH or t in EXPLORE_ENTROPY:
                    leaked.append(t)
                homes = live_vocab.get(t, set())
                if "explore" in homes:
                    leaked.append(t)
        if leaked:
            errors.append(f"rupture leaked explore edge: {sorted(set(leaked))[:12]}")

    foreign = []
    for seq in seqs:
        for t in seq:
            if t in new_set or t in stitches:
                continue
            foreign.append(t)
    if foreign:
        errors.append(f"{rhythm}: unexpected token {sorted(set(foreign))[:8]}")

    lengths = collections.Counter(len(s) for s in seqs)
    leaders = collections.Counter(s[0] for s in seqs)
    return errors, notes, {
        "sequences": n,
        "new_words": len(new_words),
        "lengths": dict(sorted(lengths.items())),
        "new_count_min": min((counts[w] for w in new_words), default=0),
        "new_count_max": max((counts[w] for w in new_words), default=0),
        "file_share_max": (max(counts.values()) / n) if n else 0,
        # Alphabetical tie-break. Every new word sits on the same count, and
        # heapq's most_common is not stable across those ties.
        "file_share_word": max(counts.items(), key=lambda kv: (kv[1], kv[0])) if counts else None,
        "stitch_max": max((counts[s] for s in stitches), default=0),
        "neighbor_min": min((len(neighbor_map[w]) for w in new_words), default=0),
        "under_floor": len(under),
        "leaders_top": leaders.most_common(3),
    }


def combined_share(train, batch_seqs_by_rhythm):
    """Stage-A rhythm share on train + these sequences. Returns (max_share, top rows, baseline_max)."""
    rhythm_n = collections.Counter(r["rhythm"] for r in train)
    hits = collections.defaultdict(collections.Counter)
    for rec in train:
        for t in set(rec["tokens"]):
            hits[t][rec["rhythm"]] += 1
    base_shares = []
    for t, by_r in hits.items():
        for rhythm, c in by_r.items():
            base_shares.append(c / rhythm_n[rhythm])
    baseline = max(base_shares) if base_shares else 0.0

    for rhythm, seqs in batch_seqs_by_rhythm.items():
        rhythm_n[rhythm] += len(seqs)
        for seq in seqs:
            for t in set(seq):
                hits[t][rhythm] += 1
    rows = []
    for t, by_r in hits.items():
        for rhythm, c in by_r.items():
            rows.append((c / rhythm_n[rhythm], t, rhythm, c, rhythm_n[rhythm]))
    rows.sort(key=lambda r: -r[0])
    return (rows[0][0] if rows else 0.0), rows[:8], baseline


def render(rhythm, seqs) -> str:
    header = _header(AUTHORING / f"{rhythm}.md", rhythm)
    region_names = " | ".join(REGIONS[rhythm])
    lines = [
        header,
        "",
        f"# vocab-growth batch. regions: {region_names}.",
        "# New distinctions inside this rhythm. One existing signature stitch at most.",
        "# Pairs are unique; order-swapped bags are not repeated.",
    ]
    for seq in seqs:
        lines.append("- " + ", ".join(seq))
    lines.append("")
    return "\n".join(lines)


def _self_check():
    rng = random.Random(0)
    # Letters only: the generator refuses a partner that is not ^[a-z]+$.
    targets = ["alpha", "bravo", "cedar", "delta", "ember", "flint",
               "grove", "haven", "ivory", "joust", "knoll", "lunar"]
    regions = {w: ("a" if i < 6 else "b") for i, w in enumerate(targets)}
    forbidden = {"nope"}
    counts = collections.Counter()
    nbr = collections.defaultdict(set)
    bags = set()
    # A swapped bag already recorded must not come back.
    bags.add(frozenset(("alpha", "bravo")))
    pairs = {frozenset(("alpha", "bravo"))}
    seqs = generate_for_targets(
        targets, targets + ["nope", "stitchx"], 3, LENGTH_PAIR,
        counts, nbr, forbidden=forbidden, used_bags=bags, used_pairs=pairs,
        regions=regions, rng=rng, stitch_set={"stitchx"},
        fallback_pool=["stitchx"], max_count={w: 4 for w in targets},
    )
    got = [frozenset(s) for s in seqs]
    if len(got) != len(set(got)):
        raise SystemExit("self-check: duplicate bag emitted")
    if frozenset(("alpha", "bravo")) in got:
        raise SystemExit("self-check: pre-seeded order-swapped bag was repeated")
    if any("nope" in s for s in seqs):
        raise SystemExit("self-check: forbidden token emitted")
    if any(counts[w] < 3 for w in targets):
        raise SystemExit(f"self-check: floor missed { {w: counts[w] for w in targets} }")
    pair_seen = set()
    for s in seqs:
        for p in _pairs(s):
            if p in pair_seen:
                raise SystemExit(f"self-check: repeated pair {p}")
            pair_seen.add(p)
    # Determinism.
    rng2 = random.Random(0)
    counts2 = collections.Counter()
    nbr2 = collections.defaultdict(set)
    seqs2 = generate_for_targets(
        targets, targets + ["nope", "stitchx"], 3, LENGTH_PAIR,
        counts2, nbr2, forbidden=forbidden,
        used_bags={frozenset(("alpha", "bravo"))},
        used_pairs={frozenset(("alpha", "bravo"))},
        regions=regions, rng=rng2, stitch_set={"stitchx"},
        fallback_pool=["stitchx"], max_count={w: 4 for w in targets},
    )
    if seqs2 != seqs:
        raise SystemExit("self-check: seed is not deterministic")
    print("self-check ok")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grow explore/dream/stabilize/rupture vocabulary")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--dry-run", action="store_true", help="validate and print; do not write")
    ap.add_argument("--self-check", action="store_true", help="toy determinism / dedup check, then exit")
    args = ap.parse_args(argv)

    list_errors = _check_lists()
    if list_errors:
        for e in list_errors:
            print("LIST", e)
        return 1
    if args.self_check:
        _self_check()
        return 0
    _self_check()

    _live_records, live_bags, live_vocab = load_live()
    train = load_train()
    core = load_core()
    new_words, region_maps, fights = prepare(live_vocab, core)

    explore_words = set(new_words["explore"]) | set(live_vocab.get(w, set()) and set() for w in ())
    explore_words = set(new_words["explore"])
    for token, homes in live_vocab.items():
        if "explore" in homes:
            explore_words.add(token)

    print(f"seed {args.seed}")
    if fights:
        print(f"FOUGHT {len(fights)} curated words dropped:")
        for rhythm, word, why in fights:
            print(f"  {rhythm} {word}: {why}")

    for rhythm, words in new_words.items():
        if len(words) < 48:
            print(f"STOP {rhythm}: only {len(words)} words survived the boundary; refusing to thin the rhythm into a hub")
            return 1

    # Stitches must be single-homed in this rhythm or they re-open a shared edge.
    stitch_used = {}
    for rhythm, wanted in STITCHES.items():
        ok = []
        for w in wanted:
            if not _stitch_ok(rhythm, w, live_vocab):
                homes = sorted(live_vocab.get(w, ()))
                print(f"STITCH DROPPED {rhythm} {w}: homes={homes or 'absent'}")
                continue
            ok.append(w)
        if len(ok) < 12:
            print(f"STOP {rhythm}: only {len(ok)} clean stitches")
            return 1
        stitch_used[rhythm] = ok

    # Try the mixed lengths first. If a rhythm crowds the hub ceiling, rebuild
    # every rhythm with pairs only so the batch stays one seed, one shape.
    plans = [("mix", LENGTH_MIX), ("pairs", LENGTH_PAIR)]
    chosen = None
    last_errors = []
    for plan_name, length_dist in plans:
        rng = random.Random(args.seed)
        built = {}
        errors = []
        for rhythm in RHYTHMS:
            # Independent stream per rhythm, derived from the master seed,
            # so adding a rhythm later does not reshuffle the others.
            rr = random.Random(rng.randint(1, 10**9) + (sum(ord(c) for c in rhythm) * 997))
            seqs, counts, nbr, stats, _pairs_used = build_rhythm(
                rhythm, new_words[rhythm], region_maps[rhythm], stitch_used[rhythm],
                live_bags, rr, length_dist,
            )
            err, notes, summary = audit_rhythm(
                rhythm, seqs, set(new_words[rhythm]), region_maps[rhythm],
                set(stitch_used[rhythm]), counts, nbr, live_vocab, explore_words,
            )
            built[rhythm] = (seqs, counts, nbr, stats, summary, notes, err)
            errors.extend(err)
        share, top, baseline = combined_share(train, {r: built[r][0] for r in built})
        if share > baseline + 1e-12:
            errors.append(
                f"combined rhythm share {share:.4f} exceeds baseline {baseline:.4f}"
            )
        # Internal ceiling: any file whose busiest word is over HUB_TARGET
        # retries on pairs. The lint cap (0.05) is what actually fails the audit.
        crowded = any(
            built[r][4]["file_share_max"] > HUB_TARGET + 1e-12 for r in built
        )
        if errors:
            last_errors = errors
            print(f"plan {plan_name} failed ({len(errors)} errors)")
            for e in errors[:20]:
                print(" ", e)
            continue
        if crowded and plan_name != "pairs":
            print(f"plan {plan_name} crowds the hub target; retrying with pairs")
            for r in ACTIVE:
                s = built[r][4]
                print(f"  {r} file share {s['file_share_max']:.3%} word {s['file_share_word']}")
            continue
        chosen = (plan_name, built, share, top, baseline)
        break

    if chosen is None:
        print("STOP. Growth would pass the level (hub or floor or boundary). Nothing written.")
        for e in last_errors[:30]:
            print(" ", e)
        return 1

    plan_name, built, share, top, baseline = chosen
    print(f"plan {plan_name}")
    print(f"combined rhythm-share max {share:.4f}  baseline {baseline:.4f}")
    print("combined top:")
    for row in top:
        frac, token, rhythm, c, rn = row
        print(f"  {token} {rhythm} {c}/{rn} = {frac:.4f}")

    # Cross-rhythm new-word collision (should already be empty).
    for a, b in itertools.combinations(ACTIVE, 2):
        both = set(new_words[a]) & set(new_words[b])
        if both:
            print(f"STOP shared new words {a}&{b}: {sorted(both)[:8]}")
            return 1

    total_skips = collections.Counter()
    for rhythm in ACTIVE:
        seqs, _c, _n, stats, summary, notes, _e = built[rhythm]
        total_skips.update(stats)
        print(
            f"{rhythm}: +{summary['sequences']} seq  +{summary['new_words']} words  "
            f"counts {summary['new_count_min']}-{summary['new_count_max']}  "
            f"file-share {summary['file_share_max']:.3%} ({summary['file_share_word'][0]})  "
            f"stitch-max {summary['stitch_max']}  nbr-min {summary['neighbor_min']}  "
            f"lengths {summary['lengths']}"
        )
        if notes:
            print(f"  notes: {notes}")
        print(f"  skips: {dict(stats)}")

    dedup_skips = (
        total_skips["skip_pair"] + total_skips["skip_bag"] + total_skips["skip_already_neighbor"]
    )
    print(
        f"dedup skips (pair + bag + already-neighbor): {dedup_skips}  "
        f"output duplicate bags: 0"
    )
    print("watched:", ", ".join(sorted(WATCHED)))

    if args.dry_run:
        print("dry-run: not written")
        return 0

    for rhythm in ACTIVE:
        text = render(rhythm, built[rhythm][0])
        path = AUTHORING / f"{rhythm}.md"
        path.write_text(text, encoding="utf-8", newline="\r\n")
        print(f"wrote {path} ({built[rhythm][4]['sequences']} sequences)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
