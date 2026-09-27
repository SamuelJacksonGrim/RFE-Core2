"""Build the long-sequence corpora beside the live rhythm jsonl.

Three arms, same sequence counts as corpus v1.3.0 (train 8527, holdout 1505):

  long    4-5 word lines (some 3s), one glue on the long lines, added vocabulary
  length  same shape as long, live vocabulary only
  vocab   live length and glue pattern, added vocabulary

Balance: content-word counts differ by at most 1 inside a split (ticket deal),
hub share stays under 5% of that split, bags are deduped as unordered sets.
The live rhythm_train.jsonl / rhythm_holdout.jsonl are read and then hashed.
This script does not write them.

    python -m tools.longseq.gen_corpus --arm all
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import random
import re
from pathlib import Path

from tools.longseq.lexicon import GLUE, REGIONS

ROOT = Path(__file__).resolve().parents[2]
LIVE_DIR = ROOT / "data" / "corpus"
OUT_ROOT = LIVE_DIR / "scratch" / "longseq"
TOKEN_RE = re.compile(r"^[a-z]+$")
GLUE_SET = frozenset(GLUE)
RHYTHMS = ("stabilize", "dream", "reflect", "explore", "rupture")

# sha256 of the live files at branch cut. Regenerating must not move these.
LIVE_SHA256 = {
    "rhythm_train.jsonl": "f5d608597c195719f2b3634bbfcedbbe10f9aefac5b0bae4c4546741be221e61",
    "rhythm_holdout.jsonl": "61c93de1089c6b515675698fe63e8e29123c93001aae44b665f247254c148888",
}

# Length mix for the long and length arms. Same for every rhythm, so length
# is not itself a rhythm feature (in the live file, rupture is the long one).
LENGTH_WEIGHTS = {3: 0.15, 4: 0.42, 5: 0.43}
SEEDS = {"long": 1188, "length": 1189, "vocab": 1190}
HUB_SHARE = 0.05
PAIR_CAP = 4


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in rows:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")


def _split_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    content, glue = [], []
    for t in tokens:
        (glue if t in GLUE_SET else content).append(t)
    return content, glue


def _allocate(n: int, weights: dict[int, float]) -> dict[int, int]:
    raw = {k: n * w for k, w in weights.items()}
    floors = {k: int(v) for k, v in raw.items()}
    left = n - sum(floors.values())
    order = sorted(raw, key=lambda k: (raw[k] - floors[k], -k), reverse=True)
    for k in order[:left]:
        floors[k] += 1
    return floors


def _scaffold_specs(n: int, rng: random.Random) -> list[tuple[int, int]]:
    """(n_content, n_glue) per sequence. One glue on every 4 and 5; half of the 3s."""
    counts = _allocate(n, LENGTH_WEIGHTS)
    specs: list[tuple[int, int]] = []
    n3 = counts[3]
    n_glue3 = n3 // 2
    for i in range(n3):
        specs.append((2, 1) if i < n_glue3 else (3, 0))
    specs.extend((3, 1) for _ in range(counts[4]))
    specs.extend((4, 1) for _ in range(counts[5]))
    # 19 glue words cannot sit under a 5% cap if every long line takes one.
    # Convert the surplus glued lines into same-length content lines.
    cap = int(HUB_SHARE * n - 1e-9)
    budget = cap * len(GLUE)
    order = list(range(len(specs)))
    rng.shuffle(order)
    for i in order:
        if sum(g for _c, g in specs) <= budget:
            break
        c, g = specs[i]
        if g:
            specs[i] = (c + g, 0)
    rng.shuffle(specs)
    return specs


def _record_specs(records: list[dict]) -> list[tuple[int, int]]:
    specs = []
    for rec in records:
        content, glue = _split_tokens(rec["tokens"])
        if not content and not glue:
            raise SystemExit(f"live line is empty: {rec}")
        specs.append((len(content), len(glue)))
    return specs


def _added_words(live_vocab: set[str]) -> tuple[dict[str, list[str]], list[tuple[str, str, str]]]:
    added: dict[str, list[str]] = {r: [] for r in RHYTHMS}
    dropped: list[tuple[str, str, str]] = []
    claimed: dict[str, str] = {}
    for rhythm in RHYTHMS:
        for region, words in REGIONS[rhythm].items():
            for w in words:
                if not TOKEN_RE.match(w):
                    dropped.append((rhythm, w, "illegal token"))
                    continue
                if w in GLUE_SET:
                    dropped.append((rhythm, w, "glue"))
                    continue
                if w in live_vocab:
                    dropped.append((rhythm, w, "already in the live vocabulary"))
                    continue
                if w in claimed:
                    dropped.append((rhythm, w, f"claimed by {claimed[w]}"))
                    continue
                claimed[w] = f"{rhythm}/{region}"
                added[rhythm].append(w)
    return added, dropped


def _lexicon(arm: str, rhythm: str, homes: dict[str, set[str]], added: dict[str, list[str]]) -> list[str]:
    base = sorted(w for w, hs in homes.items() if rhythm in hs and w not in GLUE_SET)
    if arm == "length":
        return base
    extra = [w for w in added[rhythm] if w not in base]
    return base + extra


def _render(content: list[str], glues: list[str]) -> list[str]:
    if not content:
        return list(glues)
    if not glues:
        return list(content)
    if len(glues) == 1:
        return [content[0], glues[0], *content[1:]]
    out = [content[0]]
    gi = 0
    for c in content[1:]:
        if gi < len(glues):
            out.append(glues[gi])
            gi += 1
        out.append(c)
    while gi < len(glues):
        out.append(glues[gi])
        gi += 1
    return out


def _deal(
    specs: list[tuple[int, int]],
    words: list[str],
    rng: random.Random,
    used_bags: set[frozenset[str]],
    used_content: set[frozenset[str]],
) -> list[list[str]]:
    if not words:
        raise SystemExit("empty lexicon")
    slots = sum(n_content for n_content, _g in specs)
    n_seq = len(specs)
    if slots < len(words):
        raise SystemExit(
            f"not enough content slots ({slots}) for {len(words)} words in {n_seq} lines"
        )
    cap = int(HUB_SHARE * n_seq - 1e-9)  # strictly under 5%
    if cap < 1:
        raise SystemExit(f"hub cap is {cap} on {n_seq} lines")
    words_sorted = sorted(words)
    base, _extra = divmod(slots, len(words_sorted))
    if base > cap:
        raise SystemExit(
            f"level target {base} exceeds hub cap {cap} "
            f"({len(words_sorted)} words, {slots} slots, {n_seq} lines)"
        )

    counts: collections.Counter = collections.Counter({w: 0 for w in words_sorted})
    glue_counts: collections.Counter = collections.Counter({g: 0 for g in GLUE})
    pair_counts: collections.Counter = collections.Counter()
    made_c: list[list[str]] = []
    made_g: list[list[str]] = []
    made_t: list[list[str]] = []

    def free(content: list[str], glues: list[str]) -> bool:
        if len(content) != len(set(content)) or len(glues) != len(set(glues)):
            return False
        if len(content) >= 2 and frozenset(content) in used_content:
            return False
        tokens = _render(content, glues)
        if len(tokens) != len(set(tokens)):
            return False
        if frozenset(tokens) in used_bags:
            return False
        return True

    def commit_new(content: list[str], glues: list[str]) -> None:
        tokens = _render(content, glues)
        for w in content:
            counts[w] += 1
        for g in glues:
            glue_counts[g] += 1
        for a, b in itertools.combinations(content, 2):
            pair_counts[frozenset((a, b))] += 1
        if len(content) >= 2:
            used_content.add(frozenset(content))
        used_bags.add(frozenset(tokens))
        made_c.append(content)
        made_g.append(glues)
        made_t.append(tokens)

    for n_content, n_glue in specs:
        placed = None
        for slack in (0, 1, 2, 6, 10**6):
            for pair_cap in (PAIR_CAP, 12, 10**6):
                pool = [w for w in words_sorted if counts[w] < cap]
                if len(pool) < n_content:
                    continue
                if n_content == 0:
                    band = []
                else:
                    floor = min(counts[w] for w in pool)
                    band = [w for w in pool if counts[w] <= floor + slack]
                    if len(band) < n_content:
                        continue
                gband = [g for g in GLUE if glue_counts[g] < cap]
                if n_glue and len(gband) < n_glue:
                    continue
                gfloor = min((glue_counts[g] for g in gband), default=0)
                gprefer = [g for g in gband if glue_counts[g] <= gfloor + max(slack, 1)]
                if n_glue and len(gprefer) < n_glue:
                    gprefer = gband
                for _try in range(60):
                    chosen = rng.sample(band, n_content)
                    if any(
                        pair_counts[frozenset((a, b))] >= pair_cap
                        for a, b in itertools.combinations(chosen, 2)
                    ):
                        continue
                    glues = rng.sample(gprefer, n_glue) if n_glue else []
                    if free(chosen, glues):
                        placed = (chosen, glues)
                        break
                if placed:
                    break
            if placed:
                break
        if placed is None:
            raise SystemExit(
                f"stuck after {len(made_t)} sequences "
                f"(need {n_content} content + {n_glue} glue)"
            )
        commit_new(*placed)

    def retarget(i: int, content: list[str], glues: list[str]) -> None:
        old_c, old_g, old_t = made_c[i], made_g[i], made_t[i]
        if len(old_c) >= 2:
            used_content.discard(frozenset(old_c))
        used_bags.discard(frozenset(old_t))
        for a, b in itertools.combinations(old_c, 2):
            pair_counts[frozenset((a, b))] -= 1
        for w in old_c:
            counts[w] -= 1
        for g in old_g:
            glue_counts[g] -= 1
        tokens = _render(content, glues)
        for w in content:
            counts[w] += 1
        for g in glues:
            glue_counts[g] += 1
        for a, b in itertools.combinations(content, 2):
            pair_counts[frozenset((a, b))] += 1
        if len(content) >= 2:
            used_content.add(frozenset(content))
        used_bags.add(frozenset(tokens))
        made_c[i] = content
        made_g[i] = glues
        made_t[i] = tokens

    # Swap high-count content words toward low-count ones until the
    # per-rhythm counts differ by at most 1.
    for _round in range(n_seq * 30):
        hi = max(words_sorted, key=lambda w: (counts[w], w))
        lo = min(words_sorted, key=lambda w: (counts[w], w))
        if counts[hi] - counts[lo] <= 1:
            break
        candidates = [i for i, c in enumerate(made_c) if hi in c and lo not in c]
        rng.shuffle(candidates)
        moved = False
        for i in candidates:
            new_c = [lo if w == hi else w for w in made_c[i]]
            old_c, old_g, old_t = made_c[i], made_g[i], made_t[i]
            if len(old_c) >= 2:
                used_content.discard(frozenset(old_c))
            used_bags.discard(frozenset(old_t))
            if free(new_c, old_g):
                retarget(i, new_c, old_g)
                moved = True
                break
            if len(old_c) >= 2:
                used_content.add(frozenset(old_c))
            used_bags.add(frozenset(old_t))
        if not moved:
            raise SystemExit(
                f"cannot level content {hi}={counts[hi]} vs {lo}={counts[lo]}"
            )
    else:
        hi = max(words_sorted, key=lambda w: counts[w])
        lo = min(words_sorted, key=lambda w: counts[w])
        raise SystemExit(f"content leveling did not finish {counts[hi]} vs {counts[lo]}")

    if any(glue_counts[g] for g in GLUE):
        for _round in range(n_seq * 10):
            hi = max(GLUE, key=lambda g: (glue_counts[g], g))
            lo = min(GLUE, key=lambda g: (glue_counts[g], g))
            if glue_counts[hi] - glue_counts[lo] <= 1:
                break
            if glue_counts[lo] >= cap:
                break
            candidates = [i for i, gs in enumerate(made_g) if hi in gs and lo not in gs]
            rng.shuffle(candidates)
            moved = False
            for i in candidates:
                new_g = [lo if g == hi else g for g in made_g[i]]
                old_c, old_t = made_c[i], made_t[i]
                # Release this line before the free-check, or its own content
                # bag looks like a collision.
                if len(old_c) >= 2:
                    used_content.discard(frozenset(old_c))
                used_bags.discard(frozenset(old_t))
                if free(old_c, new_g):
                    retarget(i, old_c, new_g)
                    moved = True
                    break
                if len(old_c) >= 2:
                    used_content.add(frozenset(old_c))
                used_bags.add(frozenset(old_t))
            if not moved:
                break

    if max(counts.values()) - min(counts.values()) > 1:
        raise SystemExit("content counts drifted after glue repair")
    if max(counts.values()) > cap:
        raise SystemExit(f"content count {max(counts.values())} over cap {cap}")
    if any(glue_counts[g] > cap for g in GLUE):
        raise SystemExit(f"glue count {max(glue_counts.values())} over cap {cap}")
    return list(made_t)


def _live_forbidden() -> tuple[set[frozenset[str]], set[frozenset[str]], dict[str, set[str]], dict[str, list[dict]]]:
    homes: dict[str, set[str]] = collections.defaultdict(set)
    bags: set[frozenset[str]] = set()
    content_bags: set[frozenset[str]] = set()
    by_split: dict[str, list[dict]] = {}
    for name in ("rhythm_train.jsonl", "rhythm_holdout.jsonl"):
        rows = _load_jsonl(LIVE_DIR / name)
        by_split[name] = rows
        for rec in rows:
            bags.add(frozenset(rec["tokens"]))
            content, _glue = _split_tokens(rec["tokens"])
            # A one-word content line is distinguished by its glue. Dedup those
            # by the full bag only; dedup richer bags with the glue stripped
            # so a function word cannot disguise a repeated content set.
            if len(content) >= 2:
                content_bags.add(frozenset(content))
            for t in rec["tokens"]:
                homes[t].add(rec["rhythm"])
    return bags, content_bags, homes, by_split


def _profile(rows: list[dict]) -> dict:
    lengths = collections.Counter(len(r["tokens"]) for r in rows)
    glue_n = collections.Counter(
        sum(t in GLUE_SET for t in r["tokens"]) for r in rows
    )
    by_rhythm = collections.Counter(r["rhythm"] for r in rows)
    content_counts: dict[str, collections.Counter] = {
        r: collections.Counter() for r in RHYTHMS
    }
    glue_counts: collections.Counter = collections.Counter()
    pair_instances = 0
    unique_pairs: set[tuple[str, str]] = set()
    bags = []
    for rec in rows:
        content, glue = _split_tokens(rec["tokens"])
        for t in content:
            content_counts[rec["rhythm"]][t] += 1
        for t in glue:
            glue_counts[t] += 1
        pair_instances += len(content) * (len(content) - 1) // 2
        for a, b in itertools.combinations(sorted(set(content)), 2):
            unique_pairs.add((a, b))
        bags.append(frozenset(rec["tokens"]))
    n = len(rows)
    freq = {}
    for rhythm, counts in content_counts.items():
        vals = list(counts.values())
        freq[rhythm] = {
            "words": len(vals),
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
        }
    hottest_c = max(
        ((rhythm, w, c) for rhythm, counts in content_counts.items() for w, c in counts.items()),
        default=("none", "", 0),
        key=lambda t: t[2],
    )
    hottest_g = glue_counts.most_common(1)
    return {
        "n": n,
        "by_rhythm": dict(by_rhythm),
        "lengths": {str(k): v for k, v in sorted(lengths.items())},
        "glue_per_line": {str(k): v for k, v in sorted(glue_n.items())},
        "content_freq": freq,
        "content_pairs_per_seq": round(pair_instances / n, 3) if n else None,
        "unique_content_pairs": len(unique_pairs),
        "dup_bags": sum(1 for _b, c in collections.Counter(bags).items() if c > 1),
        "max_content_share": round(hottest_c[2] / n, 4) if n else None,
        "max_content_word": {"rhythm": hottest_c[0], "word": hottest_c[1], "n": hottest_c[2]},
        "max_glue_share": round(hottest_g[0][1] / n, 4) if hottest_g and n else 0.0,
        "max_glue_word": hottest_g[0][0] if hottest_g else None,
        "vocab": len({t for r in rows for t in r["tokens"]}),
    }


def _check_invariants(rows: list[dict], label: str) -> None:
    n = len(rows)
    bags = [frozenset(r["tokens"]) for r in rows]
    if len(bags) != len(set(bags)):
        raise SystemExit(f"{label}: duplicate bag")
    counts: dict[str, collections.Counter] = {r: collections.Counter() for r in RHYTHMS}
    glue_counts: collections.Counter = collections.Counter()
    for rec in rows:
        if rec["rhythm"] not in RHYTHMS:
            raise SystemExit(f"{label}: bad rhythm {rec['rhythm']}")
        toks = rec["tokens"]
        if len(toks) != len(set(toks)):
            raise SystemExit(f"{label}: repeated token {toks}")
        if not (2 <= len(toks) <= 5):
            raise SystemExit(f"{label}: bad length {toks}")
        for t in toks:
            if not TOKEN_RE.match(t):
                raise SystemExit(f"{label}: illegal token {t}")
            if t in GLUE_SET:
                glue_counts[t] += 1
            else:
                counts[rec["rhythm"]][t] += 1
    for rhythm, counter in counts.items():
        if not counter:
            continue
        # Per-rhythm share is against the rhythm's own lines, which is the
        # authoring cap. Also require the global share under 5%.
        rn = sum(1 for r in rows if r["rhythm"] == rhythm)
        for w, c in counter.items():
            if c / rn >= HUB_SHARE or c / n >= HUB_SHARE:
                raise SystemExit(f"{label}: content hub {rhythm}/{w} {c}/{rn}")
        vals = list(counter.values())
        if max(vals) - min(vals) > 1:
            raise SystemExit(
                f"{label}: {rhythm} content counts not level "
                f"(min {min(vals)} max {max(vals)})"
            )
    global_counts: collections.Counter = collections.Counter()
    for counter in counts.values():
        global_counts.update(counter)
    for w, c in global_counts.items():
        if c / n >= HUB_SHARE:
            raise SystemExit(f"{label}: global content hub {w} {c}/{n}")
    for w, c in glue_counts.items():
        if c / n >= HUB_SHARE:
            raise SystemExit(f"{label}: glue hub {w} {c}/{n}")


def build_arm(arm: str, homes, added, by_split, used_bags, used_content) -> dict:
    rng = random.Random(SEEDS[arm])
    out_dir = OUT_ROOT / arm
    report = {"arm": arm, "seed": SEEDS[arm], "added_words": {r: list(added[r]) for r in RHYTHMS}}
    if arm == "length":
        report["added_words"] = {r: [] for r in RHYTHMS}
    written = {}
    for split_name, out_name in (
        ("rhythm_train.jsonl", "rhythm_train.jsonl"),
        ("rhythm_holdout.jsonl", "rhythm_holdout.jsonl"),
    ):
        live_rows = by_split[split_name]
        rows_out = []
        for rhythm in RHYTHMS:
            live_r = [r for r in live_rows if r["rhythm"] == rhythm]
            lex = _lexicon(arm, rhythm, homes, added)
            if arm == "vocab":
                specs = _record_specs(live_r)
            else:
                specs = _scaffold_specs(len(live_r), random.Random(f"{SEEDS[arm]}:{split_name}:{rhythm}"))
            seqs = _deal(specs, lex, rng, used_bags, used_content)
            if len(seqs) != len(live_r):
                raise SystemExit(f"{arm} {rhythm}: got {len(seqs)} want {len(live_r)}")
            for tokens in seqs:
                rows_out.append({"tokens": tokens, "rhythm": rhythm})
        _check_invariants(rows_out, f"{arm}:{split_name}")
        path = out_dir / out_name
        _write_jsonl(path, rows_out)
        written[out_name] = _profile(rows_out)
        written[out_name]["sha256"] = _sha256(path)
        written[out_name]["path"] = str(path.relative_to(ROOT)).replace("\\", "/")
    report["splits"] = written
    # Vocabulary added, counted on the train split only (the fit's vocabulary).
    train_rows = _load_jsonl(out_dir / "rhythm_train.jsonl")
    train_vocab = {t for r in train_rows for t in r["tokens"]}
    live_train_vocab = {t for r in by_split["rhythm_train.jsonl"] for t in r["tokens"]}
    report["train_vocab"] = len(train_vocab)
    report["train_vocab_added"] = sorted(train_vocab - live_train_vocab)
    report["train_vocab_added_n"] = len(report["train_vocab_added"])
    (out_dir / "profile.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _print_profile(title: str, profile: dict) -> None:
    print(
        f"{title} n={profile['n']} vocab={profile['vocab']} "
        f"len={profile['lengths']} glue={profile['glue_per_line']} "
        f"content_pairs/seq={profile['content_pairs_per_seq']} "
        f"unique_pairs={profile['unique_content_pairs']} "
        f"max_content_share={profile['max_content_share']} "
        f"max_glue_share={profile['max_glue_share']} dups={profile['dup_bags']}",
        flush=True,
    )
    for rhythm, freq in profile["content_freq"].items():
        print(
            f"  {rhythm} words={freq['words']} count {freq['min']}..{freq['max']}",
            flush=True,
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("long", "length", "vocab", "all"), default="all")
    args = ap.parse_args()

    for name, expect in LIVE_SHA256.items():
        got = _sha256(LIVE_DIR / name)
        if got != expect:
            raise SystemExit(f"live {name} hash moved: {got} != {expect}")

    used_bags, used_content, homes, by_split = _live_forbidden()
    live_vocab = set(homes)
    added, dropped = _added_words(live_vocab)
    print(
        "added "
        + " ".join(f"{r}={len(added[r])}" for r in RHYTHMS)
        + f" dropped={len(dropped)}",
        flush=True,
    )
    for rhythm, word, why in dropped:
        print(f"  drop {rhythm}/{word}: {why}", flush=True)

    live_profile = _profile(by_split["rhythm_train.jsonl"])
    _print_profile("LIVE train", live_profile)

    arms = ("long", "length", "vocab") if args.arm == "all" else (args.arm,)
    summaries = []
    for arm in arms:
        # Each arm may reuse a live bag's rejection set, but arms are separate
        # corpora and may share bags with each other. Only the live bags are forbidden.
        arm_bags = set(used_bags)
        arm_content = set(used_content)
        report = build_arm(arm, homes, added, by_split, arm_bags, arm_content)
        summaries.append({
            "arm": arm,
            "train_vocab": report["train_vocab"],
            "train_vocab_added_n": report["train_vocab_added_n"],
            "train": report["splits"]["rhythm_train.jsonl"],
            "holdout": report["splits"]["rhythm_holdout.jsonl"],
        })
        _print_profile(f"{arm} train", report["splits"]["rhythm_train.jsonl"])
        _print_profile(f"{arm} holdout", report["splits"]["rhythm_holdout.jsonl"])

    # Hash the live files again after the writes.
    for name, expect in LIVE_SHA256.items():
        got = _sha256(LIVE_DIR / name)
        if got != expect:
            raise SystemExit(f"live {name} changed during generation: {got}")
    print("LIVE HASHES UNCHANGED", flush=True)
    (OUT_ROOT / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
