# Full-system run — manifest

> **Storage note (2026-07-06):** raw per-step data (`run_*.jsonl`,
> `run_console.log`, `status_*.json`) is **gzipped in place** — this one run
> was 9.1 MB raw, two-thirds of the whole repo. `gunzip -k <file>.gz` to read.
> `report.md`, `summary.json`, `aggregate.json`, governance snapshots,
> `plots/`, and `diagnostics/` remain uncompressed. Convention:
> `docs/findings/INDEX.md` §Raw-data convention.

- Date (UTC): 2026-06-28T06:01:31Z
- Commit: `6abd22c1ff4f5a7ef491f69731f97b429850bc49`
- Python: 3.11.15 | numpy 2.4.6 | torch 2.12.1+cu130
- Platform: Linux-6.18.5-x86_64-with-glibc2.39
- Steps: 1000 | seeds: [42, 7, 11] | arms: ['levers_on', 'levers_off'] | status_every: 25

Arms:
- `levers_on`  — default CONFIG (corpus pretrain + novelty attenuation ON)
- `levers_off` — graduated levers OFF (pretrain off, novelty off); dim 128, eval on

Input: weighted multi-source round-robin over ['source_samuel', 'source_claude', 'source_gemini', 'source_grok'] (weights {'source_samuel': 0.4, 'source_claude': 0.25, 'source_gemini': 0.2, 'source_grok': 0.15}), origin_type='internal'.
