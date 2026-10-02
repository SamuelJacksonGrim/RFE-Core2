"""Verify the reasoning probe set: every word in every probe must be in the encoder's vocabulary (content vocab file
+ GLUE from base_vocab_policy). A probe word outside the vocab is noise to this encoder, so the probe would be invalid.

    python -m tools.corpus_v2.check_probes --vocab path/to/base_vocab_final.txt [--probes data/probes/reasoning_probes_v1.jsonl]
"""
import argparse
import collections
import json
import re
from pathlib import Path

from tools.corpus_v2.base_vocab_policy import GLUE, TONE_MARKERS

META_KEYS = {"type", "relation", "expect", "note", "id", "family", "group"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vocab", required=True, help="content vocabulary, one word per line")
    ap.add_argument("--probes", default="data/probes/reasoning_probes_v1.jsonl")
    a = ap.parse_args()
    vocab = set(Path(a.vocab).read_text(encoding="utf-8").split()) | GLUE | TONE_MARKERS
    probes = [json.loads(l) for l in Path(a.probes).read_text(encoding="utf-8").splitlines() if l.strip()]
    missing, types = collections.Counter(), collections.Counter(p["type"] for p in probes)
    for p in probes:
        for k, v in p.items():
            if k not in META_KEYS and isinstance(v, str):
                missing.update(w for w in re.findall(r"[a-z']+", v.lower()) if w not in vocab)
    print(f"{len(probes)} probes: " + ", ".join(f"{t} {n}" for t, n in types.most_common()))
    if missing:
        print(f"FAIL: {sum(missing.values())} out-of-vocab words: " + ", ".join(f"{w}({n})" for w, n in missing.most_common(30)))
        raise SystemExit(1)
    print("OK: every probe word is in the vocabulary")


if __name__ == "__main__":
    main()
