> **ADDENDUM 2026-06-09 (dim-sweep eval extension) — resolves Open/next #3 of
> 2026-06-09-migration-real-generator-eval.md.** Independent re-run on a second instance
> plus the dim-256 high-separation stress test that finding flagged as future work. Probe:
> `tests/diagnostic/migration_eval_dimsweep_probe.py` (generator AND RecursiveAttention loop
> both `.eval()`'d; seeds [0,1,2]; warmup 150 / phase 400; N_CAND=48). Append-only.
>
> **⚠ FRAMING CORRECTED by `2026-06-09-fix2-live-generator.md`:** the dim-256 orthogonal
> *pair* below is real but is a cherry-picked EXTREME single-token pair. Real token regimes
> as DISTRIBUTIONS do NOT separate at dim 256 (regime means stay collinear ~0.89 due to the
> generator's common-mode), confirmed flat through dim 512. So "dim 256 makes orthogonal
> regimes available" is FALSE; only orthogonal pairs are. Read this addendum together with
> the live-generator finding.

### Cross-replication (dim 64, eval) — independent confirmation
Re-running CC's dim-64 eval config on a separate instance reproduces it to three decimals
(seed 1 identical: cos +0.189, migration +0.007, landed cos·A +0.703/+0.702). Seeds 0/2
differ only because the most-separated pair was searched over N_CAND=48 vs 24.

| config | determinism (same tok ×5) | mean migration | verdict |
|--------|--------------------------:|---------------:|---------|
| dim 64  TRAIN | +0.49 | +0.002 | RIGID |
| dim 64  EVAL  | +1.000 | +0.006 | RIGID |
| dim 256 EVAL  | +1.000 | +0.002 | RIGID |

### High-separation stress test (dim 256, eval) — the load-bearing result
| seed | cos(A_dir,B_dir) | disp(control) | disp(novel B) | migration | landed cos·A | landed cos·B |
|-----:|-----------------:|--------------:|--------------:|----------:|-------------:|-------------:|
| 0    | +0.018           | 0.004 | 0.005 | +0.002 | +0.760 | +0.005 |
| 1    | +0.229           | 0.004 | 0.005 | +0.001 | +0.709 | +0.214 |
| 2    | +0.232           | 0.004 | 0.006 | +0.002 | +0.717 | +0.189 |

Seed 0 presents a genuinely orthogonal deterministic real PAIR (cos +0.018). Fed it, the
field still does not migrate (+0.002); what lands is reconstituted to A (+0.760) with the
orthogonal regime stripped (+0.005).

### Interpretation
RIGID holds across the full separation range that can be presented at the PAIR level:
moderate (cos 0.19–0.44, dim 64) and near-orthogonal (cos +0.018, dim 256). The loop is a
real, rank-independent moat at the pair level. BUT see the correction box: at the regime
(distribution) level the generator's common-mode keeps means collinear regardless of dim, so
this pair-level result does not imply real-regime separation. The reflective-loop moat and
the common-mode collinearity are two independent facts; the live finding shows the latter is
what actually bounds real novelty.
