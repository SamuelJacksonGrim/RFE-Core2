# Raw run data — READ THIS BEFORE GREPPING

Files over ~100 KB in this tree are **gzipped in place** (`.gz`). A plain
`grep` **silently skips them** — zero matches does NOT mean no data. Use:

```bash
zgrep '"rhythm"' <file>.jsonl.gz     # search without extracting
zcat  <file>.jsonl.gz | head         # stream it
gunzip -k <file>.gz                  # extract a working copy (keeps the .gz)
```

Python: `gzip.open(path, "rt")` — drop-in for `open()`.

**You rarely need the raw files.** Each run directory keeps its
`report.md`, `summary.json`, `aggregate.json`, plots, and small snapshots
**uncompressed** — that is the reference material. The gzipped per-step
logs exist for re-analysis scripts, not for reading.

Convention (adopted 2026-07-06, rationale in `../INDEX.md` §Raw-data
convention): summaries/reports/plots are committed readable; raw per-step
data >~100 KB is gzipped in place; truly huge artifacts go to GitHub
releases with a manifest line here.
