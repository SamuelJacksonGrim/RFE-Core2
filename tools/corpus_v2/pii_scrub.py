#!/usr/bin/env python3
"""
pii_scrub.py: strip personal info and credentials out of text files (chat exports, notes, logs, datasets).

Made for cleaning an AI-conversation archive into a training set, tuned against a real ~22M-word corpus.
Free to use, change, and share.

WHAT IT REMOVES (removed outright, no [REDACTED] placeholders, so the text stays natural)
  * credentials: private key blocks, API keys (OpenAI/Anthropic sk-, Google AIza, GitHub ghp_/github_pat_,
    AWS AKIA, xAI, Hugging Face hf_), JWTs (eyJ...), "Authorization: Bearer <token>", Slack/Stripe/GitLab
    tokens, database connection strings, password/token/secret values (TOKEN=..., api_key: ...)
  * every email address and every phone number (US formats: (406) 555-1234, +1 406.555.1234, 555-1234)
  * street addresses (123 Main St, 17 Oak Ln ...), IPv4 and MAC addresses, dashed SSNs
  * the username inside folder paths (C:\\Users\\name, /home/name, /Users/name)
  * anything you list in a --names-file (your name, nicknames, handles, city ...), one per line
  * optional --ner: people and places found by spaCy's language model

WHAT IT LEAVES ALONE
  dates (2026-10-02), version numbers (v1.3.0), ordinary numbers, and normal words.

SAFETY
  * dry run by default: it only REPORTS what it would remove
  * --write saves cleaned copies into a separate output folder; your original files are never modified

USAGE
  python pii_scrub.py my_exports/                          # dry run: counts per file
  python pii_scrub.py my_exports/ --write -o cleaned/      # write cleaned copies
  python pii_scrub.py my_exports/ --write -o cleaned/ --names-file me.txt --ner

  --ner needs:  pip install spacy  &&  python -m spacy download en_core_web_sm

WHY THE NER HAS A FILTER
  On real chat text spaCy mislabels ordinary words: it tagged "AI" as a place hundreds of times, and words like
  "cursor", "node", "keeper" as people. This script first learns from YOUR files which words you usually write in
  lowercase mid-sentence; those are ordinary words and are protected, along with short acronyms (AI, JSON, API).
  Words you almost always capitalize (real names, real places) still get removed.

WHAT IT DOESN'T DO
  No regex/NER tool is perfect. It can miss unusual formats and can't know context. Spot-check the output
  before you publish anything.
"""
import argparse
import collections
import re
import sys
from pathlib import Path

TEXT_EXT = {".txt", ".md", ".json", ".jsonl", ".csv", ".tsv", ".html", ".htm", ".log", ".xml", ".yaml", ".yml"}

PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    "api key": re.compile(r"\b(?:sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,}"
                          r"|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|xai-[A-Za-z0-9]{40,}|hf_[A-Za-z0-9]{30,})\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*"),
    "bearer token": re.compile(r"(?i)(?<=\bBearer )[A-Za-z0-9._~+/=-]{12,}"),
    "slack/stripe/gitlab token": re.compile(r"\b(?:xox[abprs]-[A-Za-z0-9-]{10,}|[sr]k_live_[A-Za-z0-9]{20,}"
                                            r"|glpat-[A-Za-z0-9_-]{20,})\b"),
    "db connection": re.compile(r"\b(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis)://[^\s\"'`]+"),
    "secret value": re.compile(r"(?i)(?:(?<=password)|(?<=passwd)|(?<=api_key)|(?<=apikey)|(?<=secret)|(?<=token))"
                               r"[\"']?\s?[:=]\s?[\"']?[^\s\"',;)`]{6,}"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<![\w-])(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?![\w-])"
                        r"|(?<![\w.-])\d{3}-\d{4}(?![\w-])"),
    "street address": re.compile(r"\b\d{1,5}\s+(?:[A-Za-z0-9#.-]+\s+){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard"
                                 r"|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl|Circle|Cir|Highway|Hwy|Parkway|Pkwy"
                                 r"|Terrace|Trail|Trl)\b\.?", re.I),
    "ip address": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    "mac address": re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}
USERPATH = re.compile(r"(?i)([A-Z]:\\Users\\|/(?:Users|home)/)[A-Za-z0-9_.-]+")


def load_names(path):
    if not path:
        return None
    items = [l.strip() for l in open(path, encoding="utf-8") if l.strip() and not l.startswith("#")]
    items.sort(key=len, reverse=True)
    return re.compile(r"(?<![\w])(?:" + "|".join(re.escape(i) for i in items) + r")(?:'s)?(?![\w])", re.I) if items else None


def regex_scrub(text, names_re, counts):
    for label, pat in PATTERNS.items():
        text, n = pat.subn("", text)
        counts[label] += n
    text, n = USERPATH.subn(r"\1", text)
    counts["path username"] += n
    if names_re:
        text, n = names_re.subn("", text)
        counts["your names list"] += n
    text = re.sub(r"[ \t]{2,}", " ", text)
    return re.sub(r" +([,.!?;:])", r"\1", text)


class EntityStripper:
    """spaCy PERSON/GPE/LOC/FAC removal, with a protect-filter learned from the user's own files."""
    LABELS = {"PERSON", "GPE", "LOC", "FAC"}
    ALWAYS_CUT = {"US", "USA", "UK", "UAE", "EU"}

    def __init__(self, files):
        try:
            import spacy
        except ImportError:
            sys.exit("--ner needs spaCy:  pip install spacy  &&  python -m spacy download en_core_web_sm")
        self.nlp = spacy.load("en_core_web_sm", exclude=["parser", "lemmatizer", "attribute_ruler", "tagger"])
        self.nlp.max_length = 3_000_000
        low, cap = collections.Counter(), collections.Counter()
        for f in files:  # learn which words this person writes in lowercase mid-sentence
            for sent in re.split(r"(?<=[.!?])\s+|\n+", f.read_text(encoding="utf-8", errors="ignore")):
                for w in re.findall(r"[A-Za-z]+", sent)[1:]:
                    (cap if w[0].isupper() else low)[w.lower()] += 1
        self.common = {w for w in low if low[w] >= 3 and low[w] >= cap[w]}

    def protected(self, text, label):
        t = re.sub(r"^(?:the|The)\s+", "", text.strip())
        if t.replace(".", "") in self.ALWAYS_CUT or (len(re.findall(r"[A-Za-z]+", t)) > 1 and label in ("GPE", "LOC")):
            return False
        if not t or t[0].islower() or (t.replace(".", "").isupper() and len(t) <= 6):
            return True
        words = re.findall(r"[A-Za-z]+", t)
        return bool(words) and all(w.lower() in self.common for w in words)

    def strip(self, text, counts):
        out = []
        for chunk in re.split(r"(\n{2,})", text):  # paragraph chunks keep memory flat on huge files
            if not chunk.strip():
                out.append(chunk); continue
            doc = self.nlp(chunk)
            ents = [e for e in doc.ents if e.label_ in self.LABELS and not self.protected(e.text, e.label_)]
            for e in sorted(ents, key=lambda e: e.start_char, reverse=True):
                chunk = chunk[:e.start_char] + chunk[e.end_char:]
            counts["names/places (ner)"] += len(ents)
            out.append(re.sub(r" {2,}", " ", chunk))
        return "".join(out)


def main():
    ap = argparse.ArgumentParser(description="Strip personal info and credentials from text files (dry run by default).")
    ap.add_argument("path", type=Path, help="a file or a folder (searched recursively)")
    ap.add_argument("--write", action="store_true", help="write cleaned copies (default is a dry run)")
    ap.add_argument("-o", "--out", type=Path, default=Path("cleaned"), help="output folder for --write (default: cleaned/)")
    ap.add_argument("--names-file", help="text file of your own identifiers to remove, one per line")
    ap.add_argument("--ner", action="store_true", help="also remove people/places with spaCy")
    a = ap.parse_args()

    root = a.path if a.path.is_dir() else a.path.parent
    files = [a.path] if a.path.is_file() else sorted(p for p in a.path.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXT)
    if a.write and a.out.resolve() in [p.resolve() for p in [a.path, root]]:
        sys.exit("Output folder must differ from the input folder (originals are never overwritten).")
    names_re = load_names(a.names_file)
    ner = EntityStripper(files) if a.ner else None
    total = collections.Counter()
    for f in files:
        counts = collections.Counter()
        text = regex_scrub(f.read_text(encoding="utf-8", errors="ignore"), names_re, counts)
        if ner:
            text = ner.strip(text, counts)
        total.update(counts)
        found = {k: v for k, v in counts.items() if v}
        if found:
            print(f"{f}: " + ", ".join(f"{k} {v}" for k, v in found.items()))
        if a.write:
            dst = a.out / f.relative_to(root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
    print("\nTOTAL " + (", ".join(f"{k} {v}" for k, v in total.most_common() if v) or "nothing found"))
    print(f"Cleaned copies written to {a.out}/" if a.write else "Dry run: nothing written. Add --write -o <folder> to save cleaned copies.")


if __name__ == "__main__":
    main()
