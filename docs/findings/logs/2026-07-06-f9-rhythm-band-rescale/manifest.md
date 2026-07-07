# Full-system run — manifest

- Date (UTC): 2026-07-07T09:12:10Z
- Commit: `ede9b8c6963da710aed40f6400b25f5160b97ebe`
- Python: 3.11.15 | numpy 2.4.6 | torch 2.12.1+cu130
- Platform: Linux-6.18.5-x86_64-with-glibc2.39
- Steps: 1000 | seeds: [42, 7, 11] | arms: ['levers_on', 'levers_off'] | status_every: 25

Arms:
- `levers_on`  — default CONFIG (corpus pretrain + novelty attenuation ON)
- `levers_off` — graduated levers OFF (pretrain off, novelty off); dim 128, eval on

Input: weighted multi-source round-robin over ['source_samuel', 'source_claude', 'source_gemini', 'source_grok'] (weights {'source_samuel': 0.4, 'source_claude': 0.25, 'source_gemini': 0.2, 'source_grok': 0.15}), origin_type='internal'.
