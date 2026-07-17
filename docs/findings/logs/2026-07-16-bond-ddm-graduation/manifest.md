# Full-system run — manifest

- Date (UTC): 2026-07-17T00:29:59Z
- Commit: `e4975422fd551684dce769bd51069dc3742372d1`
- Python: 3.11.15 | numpy 2.4.6 | torch 2.13.0+cu130
- Platform: Linux-6.18.5-x86_64-with-glibc2.39
- Steps: 1000 | seeds: [42, 7, 11] | arms: ['adversarial'] | status_every: 25

Arms:
- `levers_on`  — default CONFIG (corpus pretrain + novelty attenuation ON)
- `levers_off` — graduated levers OFF (pretrain off, novelty off); dim 128, eval on

Input: weighted multi-source round-robin over ['source_samuel', 'source_claude', 'source_gemini', 'source_grok'] (weights {'source_samuel': 0.4, 'source_claude': 0.25, 'source_gemini': 0.2, 'source_grok': 0.15}), origin_type='internal'.
