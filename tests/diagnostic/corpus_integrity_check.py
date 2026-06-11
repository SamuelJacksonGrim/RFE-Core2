"""
tests/diagnostic/corpus_integrity_check.py

Integrity gate for the curated rhythm corpus (`data/corpus/`).

The corpus is training data for the generator — identity-shaping input — so
its structural guarantees are enforced mechanically, the same way
`verify_docs` enforces doc claims. Checks the MANIFEST's claims and the
curation spec (`docs/training/data_curation.md` §3) against the actual files:

  1. schema           — exact keys, rhythm/source enums, 2-4 non-empty tokens
  2. manifest counts  — "- train: N sequences" / "- holdout: N sequences" match
  3. no duplicates    — no exact token-sequence dup within either split
  4. no leakage       — no token sequence appears in both train and holdout
                        (holdout reads generalization; leakage inflates Gate G1)
  5. label coherence  — identical sequences never carry different rhythms
  6. vocab closure    — holdout vocabulary fully contained in train vocabulary
  7. context floor    — every train token appears in >= 8 distinct contexts
  8. stratification   — per-rhythm holdout fraction within [0.10, 0.20]
  9. sacred exclusion — the philosophical-constant token strings (3.12, 11.88,
                        280.90) never appear; corpus must not steer
                        sacred-symbol geometry

Deterministic, no model construction. Exit 0 = corpus sound, 1 = violation.

Run:
    python -m tests.diagnostic.corpus_integrity_check
"""

from __future__ import annotations

import collections
import re

from training.corpus import (
    HOLDOUT_PATH,
    MANIFEST_PATH,
    RHYTHMS,
    TRAIN_PATH,
    corpus_version,
    load_corpus,
)

SOURCES = {"source_samuel", "source_claude", "source_gemini", "source_grok"}
SACRED_TOKENS = {"3.12", "11.88", "280.90"}
MIN_CONTEXTS = 8          # data_curation.md §3 scale target
STRAT_BAND = (0.10, 0.20)  # around the ~15% holdout target


def main() -> int:
    print('=' * 72)
    print('  DIAGNOSTIC: corpus integrity check  (data/corpus/, gate)')
    print('=' * 72)
    print()

    failures: list[str] = []

    def check(ok: bool, label: str, detail: str = ""):
        mark = '✓' if ok else '✗'
        print(f'  {mark} {label}' + (f'  — {detail}' if detail else ''))
        if not ok:
            failures.append(label)

    train = load_corpus(TRAIN_PATH)
    holdout = load_corpus(HOLDOUT_PATH)
    version = corpus_version()
    print(f'  corpus version: {version}')
    print(f'  train={len(train)}  holdout={len(holdout)}')
    print()

    # 1. schema
    bad = 0
    for split_name, split in (("train", train), ("holdout", holdout)):
        for rec in split:
            if (set(rec) != {"tokens", "rhythm", "source"}
                    or rec["rhythm"] not in RHYTHMS
                    or rec["source"] not in SOURCES
                    or not (2 <= len(rec["tokens"]) <= 4)
                    or not all(isinstance(t, str) and t for t in rec["tokens"])):
                bad += 1
    check(bad == 0, 'schema: keys, enums, 2-4 non-empty string tokens', f'{bad} bad records')

    # 2. manifest counts
    manifest = MANIFEST_PATH.read_text(encoding="utf-8")
    m_train = re.search(r'^- train:\s*(\d+) sequences', manifest, re.MULTILINE)
    m_hold = re.search(r'^- holdout:\s*(\d+) sequences', manifest, re.MULTILINE)
    counts_ok = (m_train and m_hold
                 and int(m_train.group(1)) == len(train)
                 and int(m_hold.group(1)) == len(holdout))
    check(bool(counts_ok), 'manifest counts match files',
          f'manifest {m_train and m_train.group(1)}/{m_hold and m_hold.group(1)} '
          f'vs actual {len(train)}/{len(holdout)}')

    # 3. no duplicates within splits
    tr_keys = [tuple(r["tokens"]) for r in train]
    ho_keys = [tuple(r["tokens"]) for r in holdout]
    check(len(tr_keys) == len(set(tr_keys)), 'no duplicate sequences within train',
          f'{len(tr_keys) - len(set(tr_keys))} dups')
    check(len(ho_keys) == len(set(ho_keys)), 'no duplicate sequences within holdout',
          f'{len(ho_keys) - len(set(ho_keys))} dups')

    # 4. no train/holdout leakage
    leak = set(tr_keys) & set(ho_keys)
    check(len(leak) == 0, 'no sequence leakage between train and holdout',
          f'{len(leak)} leaked: {sorted(leak)[:3]}')

    # 5. label coherence
    labels = collections.defaultdict(set)
    for rec in train + holdout:
        labels[tuple(rec["tokens"])].add(rec["rhythm"])
    conflicts = {k: v for k, v in labels.items() if len(v) > 1}
    check(len(conflicts) == 0, 'no conflicting rhythm labels for identical sequences',
          f'{len(conflicts)} conflicts')

    # 6. vocab closure
    tr_vocab = {t for r in train for t in r["tokens"]}
    ho_vocab = {t for r in holdout for t in r["tokens"]}
    unseen = ho_vocab - tr_vocab
    check(len(unseen) == 0, 'holdout vocabulary contained in train vocabulary',
          f'{len(unseen)} unseen tokens: {sorted(unseen)[:5]}')

    # 7. context floor
    contexts = collections.defaultdict(set)
    for rec in train:
        key = tuple(rec["tokens"])
        for t in rec["tokens"]:
            contexts[t].add(key)
    floor = min(len(v) for v in contexts.values())
    check(floor >= MIN_CONTEXTS,
          f'every train token in >= {MIN_CONTEXTS} distinct contexts',
          f'min observed: {floor} over {len(contexts)} tokens')

    # 8. stratification
    strat_ok = True
    detail = []
    for rhythm in RHYTHMS:
        t = sum(1 for r in train if r["rhythm"] == rhythm)
        h = sum(1 for r in holdout if r["rhythm"] == rhythm)
        frac = h / max(t + h, 1)
        detail.append(f'{rhythm}={frac:.3f}')
        if not (STRAT_BAND[0] <= frac <= STRAT_BAND[1]):
            strat_ok = False
    check(strat_ok, f'per-rhythm holdout fraction in [{STRAT_BAND[0]}, {STRAT_BAND[1]}]',
          ' '.join(detail))

    # 9. sacred exclusion
    sacred_hits = (tr_vocab | ho_vocab) & SACRED_TOKENS
    check(len(sacred_hits) == 0, 'sacred-constant token strings absent',
          f'found: {sorted(sacred_hits)}')

    print()
    if failures:
        print(f'CORPUS INTEGRITY FAILED — {len(failures)} violation(s).')
        return 1
    print(f'CORPUS INTEGRITY VERIFIED — corpus v{version} sound.')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
