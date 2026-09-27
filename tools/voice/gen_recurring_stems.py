"""Entropy-gated recurring stems for the Phase B co-balance corpus.

A stem is one sorted content bag. It is completed many times, by different
rhythm-appropriate fillers, and the filler multiset is kept only when its
Shannon entropy is at least 2.5 bits. Glue is a scaffold field. It is not
in the context and it is not a target.

The filler mode is a function of a two-word kernel, not of any one token.
The same kernel is realized by many surface stems (a varying partner). The
held-out `novel` split uses a partner token that never occurs in train.
`novel_tuple` uses a partner that does occur, but not in this bag.
`unseen_kernel` is the negative control: the kernel pair itself is absent.
None of these is the old similar split. That split trained the bare pivot,
then hid it inside new partners, so the pivot token alone was the answer.

Domains, all rhythm-tagged, fillers drawn from that rhythm:
  relational   Entity | Attribute | Temporal_Frame | Value
  logic        Locus | Prev_State | Trigger | Target
  structural   Carrier | Pattern | Operator | Value

    python -m tools.voice.gen_recurring_stems --selftest
    python -m tools.voice.gen_recurring_stems
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from tools.completion.corpus import GLUE, attach_dists, build_rows, content_of
from tools.completion.live_guard import REPO, assert_live_intact, sha256
from training.corpus import RHYTHMS, TRAIN_PATH, corpus_version, load_corpus

SCRATCH = REPO.parent / "scratch" / "completion" / "s3"
ENTROPY_FLOOR_BITS = 2.5
# Unique mode (5) and six lighter fillers. H is about 2.76 bits.
COUNT_PATTERN = (5, 4, 4, 3, 3, 3, 2)
N_MODES = 6
N_ALTERNATES = 30
# Leftover rhythm-pure words become more surface partners, up to this many
# train partners per domain. More surfaces of one kernel, not copies of one bag.
MAX_TRAIN_PARTNERS = 20
SEED = 0

# name, role_a, role_b, role_vary, n_a, n_b, degree, n_modes, n_train, n_oov, n_withhold
DOMAINS = (
    ("relational", "attribute", "temporal_frame", "entity", 6, 6, 4, 6, 8, 4, 2),
    ("logic", "prev_state", "trigger", "locus", 5, 5, 3, 6, 6, 3, 2),
    ("structural", "pattern", "operator", "carrier", 5, 5, 3, 6, 6, 3, 2),
)


def shannon_bits(counts: dict) -> float:
    """H(F) in bits. Empty or a one-point slot is 0."""
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for count in counts.values():
        if count <= 0:
            continue
        p = count / total
        h -= p * math.log2(p)
    return h


def unique_mode(counts: dict) -> str | None:
    if not counts:
        return None
    best = max(counts.values())
    words = [w for w, c in counts.items() if c == best]
    if len(words) != 1:
        return None
    return words[0]


def entropy_filter(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep stems whose filler multiset clears the floor and has one mode."""
    kept = []
    rejected = []
    for rec in records:
        counts = rec["filler_counts"]
        bits = shannon_bits(counts)
        rec["slot_entropy_bits"] = round(bits, 4)
        if bits + 1e-9 < ENTROPY_FLOOR_BITS or unique_mode(counts) is None:
            rejected.append(rec)
        else:
            kept.append(rec)
    return kept, rejected


def _majority(records) -> tuple[dict, int]:
    """Content word -> rhythm, when one rhythm has at least 3/4 of its uses."""
    counts = defaultdict(Counter)
    for rec in records:
        rhythm = rec["rhythm"]
        if rhythm not in RHYTHMS:
            raise ValueError(f"unknown rhythm {rhythm}")
        for token in content_of(rec["tokens"]):
            counts[token][rhythm] += 1
    assigned = {r: [] for r in RHYTHMS}
    skipped = 0
    for token, ctr in counts.items():
        total = sum(ctr.values())
        best = max(ctr.values())
        if best / total < 0.75:
            skipped += 1
            continue
        for rhythm in RHYTHMS:
            if ctr[rhythm] == best:
                assigned[rhythm].append(token)
                break
    for rhythm in RHYTHMS:
        assigned[rhythm] = sorted(assigned[rhythm])
    return assigned, skipped


def _take(pool: list[str], n: int) -> list[str]:
    if len(pool) < n:
        raise ValueError(f"need {n} words, have {len(pool)}")
    got = pool[:n]
    del pool[:n]
    return got


def assign_kernels(n_a: int, n_b: int, degree: int, n_modes: int, rng: random.Random):
    """Each row links to `degree` columns. Modes stay unique in the row and the column.

    Rarest legal mode first, so the rhythm unigram does not pile onto one filler.
    Returns None if this shuffle cannot fill the square.
    """
    if n_a != n_b:
        raise ValueError("kernel design is square so every role word has the same degree")
    mode_of = {}
    col_modes = [set() for _ in range(n_b)]
    col_deg = [0] * n_b
    used = Counter()
    order_a = list(range(n_a))
    rng.shuffle(order_a)
    for a in order_a:
        candidates = [b for b in range(n_b) if col_deg[b] < degree]
        rng.shuffle(candidates)
        candidates.sort(key=lambda b: col_deg[b])
        row_modes = set()
        got = 0
        for b in candidates:
            if got >= degree:
                break
            opts = [m for m in range(n_modes) if m not in row_modes and m not in col_modes[b]]
            if not opts:
                continue
            rng.shuffle(opts)
            opts.sort(key=lambda m: used[m])
            mode = opts[0]
            row_modes.add(mode)
            col_modes[b].add(mode)
            col_deg[b] += 1
            used[mode] += 1
            mode_of[(a, b)] = mode
            got += 1
        if got < degree:
            return None
    if min(col_deg) < degree:
        return None
    return mode_of


def _assign_or_die(spec, rng_seed: int):
    _name, _ra, _rb, _rv, n_a, n_b, degree, n_modes, _nt, _no, _nw = spec
    for trial in range(200):
        found = assign_kernels(n_a, n_b, degree, n_modes, random.Random(rng_seed + trial))
        if found is not None:
            return found, rng_seed + trial
    raise RuntimeError(f"no kernel assignment for {spec[0]} after 200 shuffles")


def _lowest_alternates(pool: list[str], mode: str, load: Counter, n: int) -> list[str]:
    ranked = sorted(pool, key=lambda w: (load[w], w))
    picked = []
    for word in ranked:
        if word == mode or word in picked:
            continue
        picked.append(word)
        if len(picked) == n:
            return picked
    raise RuntimeError("alternate pool cannot fill a stem")


def _distribution(mode: str, alternates: list[str]) -> dict:
    counts = {mode: COUNT_PATTERN[0]}
    for word, weight in zip(alternates, COUNT_PATTERN[1:]):
        if word in counts:
            raise ValueError("duplicate filler")
        counts[word] = weight
    return counts


def _row(context, rhythm, targets, stem, split, domain, kernel, vary, bits) -> dict:
    if any(t in GLUE or t in targets for t in context):
        raise AssertionError("glue or a filler landed in the context")
    return {
        "context": list(context),
        "rhythm": rhythm,
        "targets": {w: int(targets[w]) for w in sorted(targets)},
        "kind": "recur",
        "n_content": len(context),
        "cross_rhythm": False,
        "split": split,
        "stem": stem,
        "domain": domain,
        "kernel": list(kernel),
        "vary": vary,
        "slot_entropy_bits": round(bits, 4),
        "scaffold": ["the", *context, "of", "a"],
        "source": "recur",
    }


def _stem_record(row, targets, bits) -> dict:
    mode = unique_mode(targets)
    fillers = [mode] + [w for w in sorted(targets) if w != mode]
    return {
        "context_stem": list(row["context"]),
        "fillers": fillers,
        "slot_entropy_bits": round(bits, 4),
        "filler_counts": {w: int(targets[w]) for w in sorted(targets)},
        "domain": row["domain"],
        "rhythm": row["rhythm"],
        "kernel": list(row["kernel"]),
        "vary": row["vary"],
        "split": row["split"],
        "n_obs": int(sum(targets.values())),
    }


def _pools_for(words: list[str], rng: random.Random) -> dict:
    pool = list(words)
    rng.shuffle(pool)
    modes = _take(pool, N_MODES)
    alternates = _take(pool, N_ALTERNATES)
    domains = {}
    for spec in DOMAINS:
        name, role_a, role_b, role_v, n_a, n_b, _deg, _nm, n_train, n_oov, n_with = spec
        domains[name] = {
            "spec": spec,
            "role_a": role_a,
            "role_b": role_b,
            "role_vary": role_v,
            "a": _take(pool, n_a),
            "b": _take(pool, n_b),
            "vary_train": _take(pool, n_train),
            "vary_oov": _take(pool, n_oov),
            "n_withhold": n_with,
        }
    # Smallest base pools first, so logic and structural are not stuck at 4 surfaces
    # while relational takes every spare word.
    order = ("logic", "structural", "relational")
    while pool:
        progressed = False
        for name in order:
            got = domains[name]["vary_train"]
            if len(got) >= MAX_TRAIN_PARTNERS:
                continue
            got.append(pool.pop())
            progressed = True
            if not pool:
                break
        if not progressed:
            break
    return {"modes": modes, "alternates": alternates, "domains": domains, "unused": len(pool)}


def build_rhythm(rhythm: str, words: list[str], seed: int) -> tuple[list, list, dict]:
    """Train and holdout completion rows, plus the stem records before the filter."""
    rng = random.Random(seed)
    packed = _pools_for(words, rng)
    modes = packed["modes"]
    alternates = packed["alternates"]
    rows = []
    records = []
    kernel_surfaces = Counter()
    load = Counter()
    mode_load = Counter()

    for spec in DOMAINS:
        name = spec[0]
        slot = packed["domains"][name]
        found, trial = _assign_or_die(spec, seed + (sum(ord(c) for c in name) * 17))
        slot["assign_trial"] = trial
        kernel_ids = sorted(found)
        # One filler distribution per kernel. Surface stems copy it.
        dist_of = {}
        for ordinal, (a_i, b_i) in enumerate(kernel_ids):
            mode = modes[found[(a_i, b_i)]]
            picked = _lowest_alternates(alternates, mode, load, 6)
            counts = _distribution(mode, picked)
            n_train_vary = len(slot["vary_train"]) - slot["n_withhold"]
            for word, weight in counts.items():
                if word == mode:
                    mode_load[word] += weight * n_train_vary
                else:
                    load[word] += weight * n_train_vary
            dist_of[(a_i, b_i)] = counts

        def emit(vary, a_i, b_i, split):
            a_word = slot["a"][a_i]
            b_word = slot["b"][b_i]
            targets = dist_of[(a_i, b_i)]
            context = sorted([vary, a_word, b_word])
            bits = shannon_bits(targets)
            stem = f"{name}:{rhythm}:{vary}|{a_word}|{b_word}"
            row = _row(
                context, rhythm, targets, stem, split, name,
                [a_word, b_word], vary, bits,
            )
            rows.append(row)
            records.append(_stem_record(row, targets, bits))
            if split == "train":
                kernel_surfaces[(name, a_word, b_word)] += 1

        for ordinal, (a_i, b_i) in enumerate(kernel_ids):
            n_train = len(slot["vary_train"])
            withheld = {(ordinal + s) % n_train for s in range(slot["n_withhold"])}
            for v_i, vary in enumerate(slot["vary_train"]):
                split = "novel_tuple" if v_i in withheld else "train"
                emit(vary, a_i, b_i, split)
            for vary in slot["vary_oov"]:
                emit(vary, a_i, b_i, "novel")

        # Pairs the design left unlinked. Tokens are seen; the pair is not.
        linked = set(found)
        probe_vary = slot["vary_train"][0]
        for a_i in range(len(slot["a"])):
            for b_i in range(len(slot["b"])):
                if (a_i, b_i) in linked:
                    continue
                # Reuse a trained kernel's distribution only as a label the
                # model has not earned: the mode of a linked pair is wrong
                # to copy. Give this pair its own distribution, then hold
                # it out, so the label is defined and still unseen.
                mode = modes[(a_i + 3 * b_i) % N_MODES]
                picked = _lowest_alternates(alternates, mode, load, 6)
                counts = _distribution(mode, picked)
                # Do not add these counts to the training load. The row is holdout.
                a_word = slot["a"][a_i]
                b_word = slot["b"][b_i]
                bits = shannon_bits(counts)
                context = sorted([probe_vary, a_word, b_word])
                stem = f"{name}:{rhythm}:{probe_vary}|{a_word}|{b_word}"
                row = _row(
                    context, rhythm, counts, stem, "unseen_kernel", name,
                    [a_word, b_word], probe_vary, bits,
                )
                rows.append(row)
                records.append(_stem_record(row, counts, bits))

    kept, rejected = entropy_filter(records)
    if rejected:
        raise RuntimeError(f"{rhythm}: entropy filter rejected {len(rejected)} stems")
    # The filter rewrote bits on the records. Mirror that onto the rows.
    bits_of = {
        (rec["rhythm"], tuple(rec["context_stem"]), rec["split"]): rec["slot_entropy_bits"]
        for rec in kept
    }
    for row in rows:
        row["slot_entropy_bits"] = bits_of[(row["rhythm"], tuple(row["context"]), row["split"])]

    stats = {
        "unused_pure_words": packed["unused"],
        "train_surfaces_per_kernel_min": min(kernel_surfaces.values()),
        "train_surfaces_per_kernel_max": max(kernel_surfaces.values()),
        "kernels": len(kernel_surfaces),
        "max_alternate_count": max(load.values()) if load else 0,
        "min_mode_count": min(mode_load.values()) if mode_load else 0,
        "assign_trials": {n: packed["domains"][n]["assign_trial"] for n in packed["domains"]},
    }
    if stats["max_alternate_count"] >= stats["min_mode_count"]:
        raise RuntimeError(
            f"{rhythm}: an alternate outruns the rarest mode "
            f"({stats['max_alternate_count']} >= {stats['min_mode_count']})"
        )
    return rows, kept, stats


def _bag_key(row) -> tuple:
    return (row["rhythm"], tuple(row["context"]))


def _assert_disjoint(rows: list[dict]) -> None:
    train_keys = {_bag_key(r) for r in rows if r["split"] == "train"}
    train_tokens = {t for r in rows if r["split"] == "train" for t in r["context"]}
    train_pairs = set()
    for row in rows:
        if row["split"] != "train":
            continue
        a, b = row["kernel"]
        train_pairs.add((row["rhythm"], row["domain"], frozenset((a, b))))
    seen = set()
    for row in rows:
        key = _bag_key(row) + (row["split"],)
        if key in seen:
            raise AssertionError(f"duplicate bag {key}")
        seen.add(key)
        if any(t in GLUE for t in row["context"]):
            raise AssertionError("glue in context")
        if any(t in row["targets"] for t in row["context"]):
            raise AssertionError("filler in context")
        if row["split"] == "train":
            continue
        if _bag_key(row) in train_keys:
            raise AssertionError(f"{row['split']} context leaked into train")
        a, b = row["kernel"]
        pair = (row["rhythm"], row["domain"], frozenset((a, b)))
        if row["split"] == "unseen_kernel":
            if pair in train_pairs:
                raise AssertionError("unseen kernel was trained")
            if row["vary"] not in train_tokens:
                raise AssertionError("unseen-kernel probe token was not trained")
        else:
            if pair not in train_pairs:
                raise AssertionError(f"{row['split']} kernel was never trained")
        if row["split"] == "novel" and row["vary"] in train_tokens:
            raise AssertionError("novel partner occurred in train")
        if row["split"] == "novel_tuple" and row["vary"] not in train_tokens:
            raise AssertionError("novel_tuple partner never occurred in train")
        # A trained context is the same length, so the only subset leak is equality,
        # already rejected. Refuse a shorter trained context inside this bag too.
        for other in train_keys:
            if other[0] != row["rhythm"]:
                continue
            if set(other[1]) < set(row["context"]):
                raise AssertionError("holdout context contains a trained context")


def single_token_mode_top1(train_rows, hold_rows) -> float:
    """Upper bound on a one-token policy. Counts the mode only, once per train stem.

    Shared alternates are ignored on purpose: they are a constant background,
    and a token can still point at the mode it co-occurred with.
    """
    marg = defaultdict(lambda: defaultdict(Counter))
    for row in train_rows:
        mode = unique_mode(row["targets"])
        for token in row["context"]:
            marg[row["rhythm"]][token][mode] += 1
    if not hold_rows:
        return 0.0
    hits = 0
    for row in hold_rows:
        mode = unique_mode(row["targets"])
        matched = False
        for token in row["context"]:
            ctr = marg[row["rhythm"]].get(token)
            if not ctr:
                continue
            best = max(ctr.values())
            guess = sorted(w for w, c in ctr.items() if c == best)[0]
            if guess == mode:
                matched = True
                break
        hits += int(matched)
    return hits / len(hold_rows)


def mode_unigram_top1(train_rows, hold_rows) -> float:
    """Rhythm marginal of target counts. Argmax word versus the holdout mode."""
    counts = {r: Counter() for r in {row["rhythm"] for row in train_rows}}
    for row in train_rows:
        for word, count in row["targets"].items():
            counts[row["rhythm"]][word] += count
    if not hold_rows:
        return 0.0
    hits = 0
    for row in hold_rows:
        ctr = counts[row["rhythm"]]
        best = max(ctr.values())
        guess = sorted(w for w, c in ctr.items() if c == best)[0]
        hits += int(guess == unique_mode(row["targets"]))
    return hits / len(hold_rows)


def _frequency(rows: list[dict]) -> dict:
    context_freq = Counter()
    target_freq = Counter()
    for row in rows:
        if row["split"] != "train":
            continue
        for token in row["context"]:
            context_freq[token] += 1
        for word, count in row["targets"].items():
            target_freq[word] += count
    def _span(ctr: Counter) -> dict:
        if not ctr:
            return {}
        vals = list(ctr.values())
        return {
            "words": len(vals),
            "min": min(vals),
            "median": int(statistics.median(vals)),
            "max": max(vals),
            "max_over_median": round(max(vals) / statistics.median(vals), 3),
        }
    return {"context": _span(context_freq), "target_counts": _span(target_freq)}


def _entropy_dist(records: list[dict]) -> dict:
    bits = sorted(r["slot_entropy_bits"] for r in records)
    if not bits:
        return {}
    def _q(p):
        i = min(len(bits) - 1, max(0, int(round(p * (len(bits) - 1)))))
        return bits[i]
    return {
        "n": len(bits),
        "min": bits[0],
        "p25": _q(0.25),
        "median": _q(0.50),
        "p75": _q(0.75),
        "max": bits[-1],
        "mean": round(sum(bits) / len(bits), 4),
        "below_floor": sum(1 for b in bits if b + 1e-9 < ENTROPY_FLOOR_BITS),
    }


def build_all(assigned: dict, seed: int) -> tuple[list, list, list, dict]:
    rows = []
    records = []
    per_rhythm = {}
    for rhythm in RHYTHMS:
        words = list(assigned[rhythm])
        need = N_MODES + N_ALTERNATES + sum(
            spec[4] + spec[5] + spec[8] + spec[9] for spec in DOMAINS
        )
        if len(words) < need:
            raise SystemExit(f"{rhythm} has {len(words)} pure words, need {need}")
        r_rows, r_recs, stats = build_rhythm(rhythm, words, seed + RHYTHMS.index(rhythm) * 1009)
        stats["pure_words"] = len(words)
        per_rhythm[rhythm] = stats
        rows.extend(r_rows)
        records.extend(r_recs)
    _assert_disjoint(rows)
    train = [r for r in rows if r["split"] == "train"]
    hold = [r for r in rows if r["split"] != "train"]
    summary = {
        "seed": seed,
        "entropy_floor_bits": ENTROPY_FLOOR_BITS,
        "count_pattern": list(COUNT_PATTERN),
        "pattern_entropy_bits": round(
            shannon_bits({str(i): c for i, c in enumerate(COUNT_PATTERN)}), 4
        ),
        "per_rhythm": per_rhythm,
        "entropy": _entropy_dist(records),
        "frequency": _frequency(rows),
        "rows_by_split": dict(Counter(r["split"] for r in rows)),
        "rows_by_domain": dict(Counter(r["domain"] for r in train)),
        "stems_train": len(train),
        "observations_per_stem": int(sum(COUNT_PATTERN)),
        "kernel_surface_min": min(s["train_surfaces_per_kernel_min"] for s in per_rhythm.values()),
        "kernel_surface_max": max(s["train_surfaces_per_kernel_max"] for s in per_rhythm.values()),
    }
    for split in ("novel", "novel_tuple", "unseen_kernel"):
        sub = [r for r in hold if r["split"] == split]
        uni = mode_unigram_top1(train, sub)
        single = single_token_mode_top1(train, sub)
        summary[f"unigram_{split}"] = round(uni, 4)
        summary[f"single_token_{split}"] = round(single, 4)
        summary[f"bar_3x_{split}"] = round(3 * uni, 4)
        if uni <= 0:
            raise RuntimeError(f"{split}: unigram is 0, the 3x bar would be vacuous")
        if single + 1e-9 >= 3 * uni:
            raise RuntimeError(
                f"{split}: one token already clears 3x unigram "
                f"(single {single:.3f}, unigram {uni:.3f})"
            )
    return train, hold, records, summary


def _seen_copies(train: list[dict], rng: random.Random, n: int) -> list[dict]:
    picks = list(train)
    rng.shuffle(picks)
    out = []
    for row in picks[:n]:
        copy = dict(row)
        copy["split"] = "seen"
        copy["targets"] = dict(row["targets"])
        out.append(copy)
    return out


def drop_broad_overlap(hold: list[dict], broad: list[dict]) -> tuple[list, int]:
    """A synthetic holdout bag that already occurs in the live completion rows is not novel."""
    keys = {(r["rhythm"], tuple(r["context"])) for r in broad}
    kept = []
    dropped = 0
    for row in hold:
        if (row["rhythm"], tuple(row["context"])) in keys:
            dropped += 1
            continue
        kept.append(row)
    return kept, dropped


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mix_rows(broad: list[dict], recur: list[dict], recur_fraction: float, seed: int) -> tuple[list, dict]:
    """Subsample the larger side. No cloned rows.

    recur_fraction is recurring rows / all training rows. 0 keeps every broad
    row. 1 keeps every recurring stem. In between, whichever side would have
    to be repeated is cut down instead, so coverage is a real count of live
    contexts and recurrence is a real count of stems.
    """
    if not 0.0 <= recur_fraction <= 1.0:
        raise ValueError("recur_fraction must be in [0, 1]")
    rng = random.Random(seed)
    broad_rows = []
    for row in broad:
        item = dict(row)
        item["source"] = "broad"
        item["split"] = item.get("split", "broad")
        broad_rows.append(item)
    recur_rows = [dict(r) for r in recur]
    rng.shuffle(broad_rows)
    rng.shuffle(recur_rows)
    if recur_fraction <= 0 or not recur_rows:
        chosen_b, chosen_r = broad_rows, []
    elif recur_fraction >= 1 or not broad_rows:
        chosen_b, chosen_r = [], recur_rows
    else:
        ratio = recur_fraction / (1.0 - recur_fraction)
        n_b = len(broad_rows)
        n_r = int(round(n_b * ratio))
        if n_r > len(recur_rows):
            n_r = len(recur_rows)
            n_b = int(round(n_r * (1.0 - recur_fraction) / recur_fraction))
            n_b = max(1, min(len(broad_rows), n_b))
        n_r = max(1, min(len(recur_rows), n_r))
        chosen_b = broad_rows[:n_b]
        chosen_r = recur_rows[:n_r]
    mixed = chosen_b + chosen_r
    rng.shuffle(mixed)
    meta = {
        "recur_fraction": recur_fraction,
        "broad_rows": len(chosen_b),
        "recur_rows": len(chosen_r),
        "mixed_rows": len(mixed),
        "broad_available": len(broad_rows),
        "unique_recur_available": len(recur_rows),
        "broad_to_recur": None,
        "repeated_rows": False,
    }
    if chosen_r:
        meta["broad_to_recur"] = round(len(chosen_b) / len(chosen_r), 4)
    return mixed, meta


def selftest() -> None:
    pattern_h = shannon_bits({str(i): c for i, c in enumerate(COUNT_PATTERN)})
    if pattern_h < ENTROPY_FLOOR_BITS:
        raise SystemExit(f"count pattern is under the floor: {pattern_h}")
    bad, = entropy_filter([{
        "filler_counts": {"only": 9, "other": 1},
        "slot_entropy_bits": 0,
    }])[1]
    if "only" not in bad["filler_counts"]:
        raise SystemExit("entropy filter did not reject a peaked slot")
    flat = {"a": 1, "b": 1}
    if unique_mode(flat) is not None:
        raise SystemExit("a tie must not count as a mode")
    words = {rhythm: [f"{rhythm[:3]}_{i:03d}" for i in range(140)] for rhythm in RHYTHMS}
    train, hold, records, summary = build_all(words, SEED)
    if summary["entropy"]["below_floor"] != 0:
        raise SystemExit("selftest emitted a stem under the entropy floor")
    if summary["entropy"]["min"] < ENTROPY_FLOOR_BITS:
        raise SystemExit("selftest entropy min is under the floor")
    if any(r["split"] == "train" and len(r["context"]) != 3 for r in train):
        raise SystemExit("train stem is not a 3-word bag")
    domains = {r["domain"] for r in train}
    if domains != {spec[0] for spec in DOMAINS}:
        raise SystemExit(f"missing domain: {domains}")
    for split in ("novel", "novel_tuple", "unseen_kernel"):
        if summary[f"single_token_{split}"] >= summary[f"bar_3x_{split}"]:
            raise SystemExit(f"selftest shortcut cleared the bar on {split}")
    # 0.5 with more broad rows than stems cuts broad, and never clones a row.
    mixed, meta = mix_rows(train[:50], train[50:80], 0.5, SEED)
    if meta["recur_rows"] != 30 or meta["broad_rows"] != 30:
        raise SystemExit(f"mix should subsample to 30/30, got {meta}")
    if len(mixed) != len({(r["rhythm"], tuple(r["context"]), r["stem"]) for r in mixed}):
        raise SystemExit("mix cloned a row")
    print(
        f"selftest ok  stems {summary['stems_train']}  "
        f"H {summary['entropy']['min']}-{summary['entropy']['median']}  "
        f"novel unigram {summary['unigram_novel']} single {summary['single_token_novel']}  "
        f"tuple unigram {summary['unigram_novel_tuple']} single {summary['single_token_novel_tuple']}",
        flush=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    selftest()
    if args.selftest:
        return 0

    live = assert_live_intact()
    records_live = load_corpus(TRAIN_PATH)
    assigned, skipped = _majority(records_live)
    for rhythm in RHYTHMS:
        print(f"pure {rhythm} {len(assigned[rhythm])}", flush=True)
    train, hold, stem_records, summary = build_all(assigned, SEED)
    broad = build_rows(records_live)
    hold, dropped = drop_broad_overlap(hold, broad)
    summary["broad_overlap_dropped"] = dropped
    summary["skipped_ambiguous_content_words"] = skipped
    rng = random.Random(SEED)
    n_seen = min(400, max(1, len(train) // 12))
    hold = hold + _seen_copies(train, rng, n_seen)
    _assert_disjoint([r for r in train + hold if r["split"] != "seen"])

    from tools.completion.measure import unigram_baseline

    vocab = sorted({t for rec in records_live for t in content_of(rec["tokens"])})
    stray = sorted({w for r in train + hold for w in r["targets"] if w not in set(vocab)})
    if stray:
        raise SystemExit(f"target outside live content vocab: {stray[:6]}")
    loaded_train = attach_dists(train)
    loaded_hold = attach_dists(hold)
    for split in ("novel", "novel_tuple", "unseen_kernel", "seen"):
        sub = [r for r in loaded_hold if r["split"] == split]
        summary[f"official_unigram_{split}"] = unigram_baseline(loaded_train, sub, vocab)

    _write_jsonl(SCRATCH / "stem_records.jsonl", stem_records)
    _write_jsonl(SCRATCH / "recur_train.jsonl", train)
    _write_jsonl(SCRATCH / "recur_holdout.jsonl", hold)
    _write_jsonl(SCRATCH / "broad_train.jsonl", broad)
    summary["corpus_version"] = corpus_version()
    summary["live_sha256"] = live
    summary["files"] = {
        "stem_records": str(SCRATCH / "stem_records.jsonl"),
        "recur_train": str(SCRATCH / "recur_train.jsonl"),
        "recur_holdout": str(SCRATCH / "recur_holdout.jsonl"),
        "broad_train": str(SCRATCH / "broad_train.jsonl"),
        "recur_train_sha256": sha256(SCRATCH / "recur_train.jsonl"),
        "recur_holdout_sha256": sha256(SCRATCH / "recur_holdout.jsonl"),
    }
    report_path = SCRATCH / "build_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log = REPO / "docs" / "findings" / "logs" / "2026-09-23-phase-b" / "s3_build.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    assert_live_intact()
    print(
        f"train {len(train)}  hold {dict(Counter(r['split'] for r in hold))}  "
        f"H {summary['entropy']['min']}-{summary['entropy']['median']}-"
        f"{summary['entropy']['max']}  "
        f"novel unigram {summary['official_unigram_novel']['mode_top1']}  "
        f"single {summary['single_token_novel']}",
        flush=True,
    )
    print(f"WROTE {SCRATCH}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
