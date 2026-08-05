# Where is the lock? (generator / governance / magnitude moat)

- **Date:** 2026-06-06 · **Status:** superseded — the 3-lock *map* was right; every lock since resolved/struck/downgraded
- **Substrate:** sim (token→direction stub; rest of the live step loop real) · **Probe:** `trained_generator_sim.py`
- **Depends on:** `2026-06-06-read-side-boundary`, `2026-06-06-frame-correction` (coherent field = spec, not pathology)

**Verdict:** the lock decomposed into **three layers**, not one. Control honest (`spread=0.0` → coh 0.971,
`locked`). Sweeping the generator from 1-D projector to maximally-orthogonal (spread 0→1): the field held
coh_mean **0.94–0.97** throughout, and what actually *landed* averaged inputCos **0.91** even under orthogonal
sources; the governance gate blocked ~**85%** of diverse internal input.

**Misread caught (load-bearing):** the first printed verdict ("field moved off pin → generator is the lock")
trusted the regime *label* (which flipped `locked`→`metastable` on a 0.020→0.043 dwell-variance nudge) over the
coherence *number* (which never left the high band). Corrected to the stronger read: the field couldn't be moved
off ~0.95 even at max diversity.

**Disposition of the three locks (all since relocated):**
- **#1 generator 1-D (cos 0.998)** — *partially resolved*: `sqrt(d_model)` scale fix moved it off 0.998, but the
  deterministic generator is still low-rank (~1.6 at dim 64) and runs with dropout → `2026-06-08-generator-dropout-diversity`.
- **#2 85% governance gate** — **STRUCK**: a single-source HHI=1.0 monopoly artifact, not a filter; diverse input
  passes 100%. `2026-06-07-gate-decomposition`.
- **#3 magnitude moat** — **DOWNGRADED**: real but surmountable, not the locker. `2026-06-07-attractor-migration`.

The actual mechanism is the **reflective loop** (`2026-06-07-reconstruction-ablation`) — but it locks *low-rank*
input, so generator diversity is the more upstream lever.

*Consolidated 2026-08-05 — numbers, the misread, and all three dispositions preserved. Full history in git.*
