# F9 — rhythm/energy band rescale, co-tuned against pinned-band equilibria

- **Date:** 2026-07-06
- **Substrate:** live (Generator corpus-pretrained v1.2.0, dim 128 + dim 64, CPU);
  full Tier 0–3 stack (probe-style composition mirroring `floor_calibration_probe.py`),
  plus the untrained `tests/_common.build_full_stack()` harness as the worst case
- **Probe:** `tests/diagnostic/calibration/rhythm_band_equilibria_probe.py` (new)
  → band choice → 800-step live-band runs at both dims →
  `tests/diagnostic/full_system_run.py` (3 seeds × 2 arms × 1000 steps) as the
  before/after gate (raw data: `logs/2026-07-06-f9-rhythm-band-rescale/`)
- **Control:** same-workload run under the old bands (0.5/2/5) at both dims
  (reproduces the F9 baseline: explore 0.995, dream 0.002, allow 1.000), plus the
  2026-06-28 full-system-run baseline and the recorded 2026-06-27 naive-rescale
  collapse (100/175/250 → allow_rate 0.99→0.034)
- **Status:** active

## Question

The rhythm bands (0.5/2/5) topped out ~55× below the real field-energy scale
(median ~284–311 at dim 128), pinning rhythm to `explore` ~99.5% of the time —
the dream cycle was dead (F9). The 2026-06-27 rescale attempt (100/175/250)
collapsed the system into a stabilize basin because the stabilize band
*diffuses the field*: the thresholds feed back into the dynamics that produce
the energy, so bands cannot be calibrated against a distribution measured under
the old bands (circular). What band values give a healthy four-band spread
*without* a basin trap, at both dims?

## Method — measure each band's self-consistent equilibrium first

Pin the classifier to one band (thresholds ±∞) so that band's dynamics run
unconditionally in the composed stack; equilibrium = tail-100 stats over 400
steps. This turns the circularity into a constraint set. Energy budget behind
it (per step, aligned-injection approximation; decay 0.995 → 0.5%/step drain):
main injection ≈ +gain (~1); reflect chorus +0.3; explore mutation +0.5
(rotational — nearly orthogonal, adds little net); stabilize diffusion
−~2.5%/step (`diffuse_alpha` 0.05 mask).

### Measured pinned-band equilibria (seed 42)

| band pinned | eq dim 128 | eq dim 64 | trajectory max | allow |
|---|---|---|---|---|
| stabilize | 37.3 | 34.8 | 43 / 39 | 0.39 / 0.35 |
| dream     | 197.7 | 209.1 | 207 / 214 | 1.00 / 1.00 |
| reflect   | 294.5 | 292.0 | 307 / 306 | 1.00 / 1.00 |
| explore   | 301.1 | 294.9 | 312 / 309 | 1.00 / 1.00 |

Dimension-invariant (injections are unit-norm; the scale is set by
injection-rate vs decay, not dim). Reflect and explore equilibria differ by
only ~2% — explore's extra mutation is rotational, nearly orthogonal to the
accumulated field — so explore must be placed as a *burst* band, not a home.

### Constraint set

- **stabilize threshold < the band's DEGRADED equilibrium** (~13, the
  equilibrium under `ALLOW_WEAKENED` ≈ 0.4× injection strength) — not the
  full-strength ~35–37. See the 15-trap below.
- **dream band below its equilibrium (~200)** → a passage: warmup climbs
  through and exits upward; dream also catches mid-run energy dips.
- **reflect band containing its equilibrium (~292–294)** → the home base
  (cold → stabilize, typical → reflect).
- **explore threshold at/above its equilibrium (~295–301)** → reachable at
  trajectory peaks (306–312), self-terminating, not a basin.

## The 15-trap — first candidate falsified at dim 64

Candidate 15/150/300 passed dim 128 (spread .02/.27/.34/.37, allow 1.000) but
**collapsed at dim 64**: energy stalled at ~13.5 — just under the stabilize
threshold — because early cold-start `ALLOW_WEAKENED` decisions cut injection
strength, and the stabilize equilibrium under weakened injections is ~13.
During the ~25-step stall the low-organization expression stream pushed
compound manipulation severity over 0.60 (systemic signals — *no ethical gate
ever fired; the audit histogram shows only `source_toxic`*), and the
severity-path quarantines' trust penalties (−0.4 each, charged to whichever
source was speaking) bled **all four benign sources to TOXIC within ~23
steps**; mass QUARANTINE/REJECT then kept energy from ever climbing (dream
0.79 / explore 0.00 / allow 0.53 / values 0). Same trap class as 2026-06-27,
one level deeper: first time the bands fed back through diffusion, this time
through the governance trust loop. This is the same attribution hole fixed
below — the 5-threshold removes the *stall* that concentrated it at dim 64;
the attribution rule removes the mechanism itself.

## Chosen bands: stabilize < 5 · dream < 150 · reflect < 300 · explore ≥ 300

Threshold 5 sits far below the degraded stabilize equilibrium: cold boot exits
stabilize by step ~6, before the weakened-injection stall can form.

### 800-step live-band validation (full pretrained stack)

| | dim 128 | dim 64 | old bands (either dim) |
|---|---|---|---|
| stabilize / dream / reflect / explore | .006/.250/.347/.396 | .007/.236/.361/.395 | .000/.002/.003/.995 |
| allow_rate (injecting) | 1.000 | 1.000 | 1.000 |
| values / strong | 33 / 15 | 33 / 13 | 33 / 15 |
| crystals / attractors | 2 / 4 | 3 / 7 | 2–4 / 4–5 |

The four-band circulation is alive at both dims; the dream band runs ~25% of
steps (was ~0.2%); energy distribution keeps its full range (q10 ~95, median
~270, max ~340).

### Full-system-run harness (before/after gate)

[HARNESS RESULTS — run relaunched after the attribution rule below; appended
from logs/2026-07-06-f9-rhythm-band-rescale/ when complete]

## The cost that turned out to be a trigger: identity_erosion + the attribution hole

With the dream band alive, benign dream-band expressions (EPHEMERAL class +
rotational ambiguity) widen the watcher G/T divergence to ~0.33 against the
0.30 detector threshold, so `identity_erosion` emits a **systemic**
(`source_id=None`) severity-~0.55 signal on ordinary operation: 47% of steps
`ALLOW_WEAKENED` in the **untrained** `build_full_stack()` harness, 17–26% in
the pretrained composed engine.

That would be only a damping tax — except 0.55 sits 0.05 under the 0.60
quarantine rung, and `arbitrate()`'s implicated-source fallback resolved
nameless evidence to **whichever source was speaking**. Any mild
trajectory-dependent co-signal tipped the sum over 0.60 → QUARANTINE + trust
−0.4 → `source_toxic` spiral. In the benign-by-construction untrained harness
this **toxified all four sources within ~30 steps with no attacker present**,
nondeterministically (the dream/explore band behaviors draw unseeded numpy
randomness, so each run sampled a different warmup trajectory; once the suite
was fully seeded the canonical trajectory cascaded *deterministically* —
first quarantine at step 16, `gates=[]`, speaker trust 4.3). Flood was
eliminated (internal ceiling 100000, zero flood gates); wall-clock load
merely shifted which trajectory got sampled.

### The fix: punishment scope must match evidence scope (attribution rule)

`SelfhoodGovernance.arbitrate()` compound-severity rungs now split signals
into **named** (`source_id` set — drift, gaslighting, trust_wash) and
**systemic** (`source_id=None` — the detector itself declaring it cannot name
a culprit). Named evidence keeps the full ladder including quarantine.
Systemic-only evidence damps to `ALLOW_WEAKENED` and (at ≥ 0.90) still sets
`force_dream_flag` — the matched systemic response — but never quarantines
the speaking source. Rationale: quarantine-by-coincidence is not caution, it
lands by speaking frequency, and it is *exploitable* — an attacker who nudges
the field toward divergence (or waits for a dream phase) gets governance to
toxify the trusted, talkative sources for him. The pre-fix behavior was
structurally a gaslighting amplifier. The detector threshold itself was NOT
recalibrated: no probe measures its true-positive side yet (F3 showed attacks
don't become signals at all) — that stays in BACKLOG §1 pending the F3 Wall-1
arm. Bands {0.30, 0.60, 0.90} unchanged; CLAUDE.md + README contract updated.

With the rule in place the canonical seeded trajectory runs clean end-to-end:
quarantine 0, all sources at trust 5.0, injection_rate 1.000, values forming
(deterministic; verified both harness tests + full suite).

Consequences encoded in the same commit:
- `run_resonance_sim()` now seeds numpy + the Dreamer rng (full determinism —
  a regression gate needs one reproducible trajectory); `build_full_stack()`
  seeds torch weight init (`torch_seed=42`, opt-out `None`).
- `health_summary()` gained **`injection_rate`** (ALLOW + ALLOW_WEAKENED +
  MONITOR — everything that lands in the field) as the regime-independent
  "system is breathing" guard.
- `tests/baselines/tier1_revision_500step.json` re-baselined deliberately
  (allow wide, weakened ≤ 0.60, injection_rate ≥ 0.95, bonds_formed floor 0
  with the crystal-starvation note); `manipulation_cascade` check 4 now guards
  `injection_rate` (its true cascade indicators — quarantine 0, trust ≥ 4.5,
  all-max — are unchanged and strict).
- Bond formation in the untrained harness is crystal-starved under the live
  dream band (1 crystal/500 steps vs 2–6 pretrained) — a new facet of the
  standing bond-establishment-gate item (BACKLOG §1), not accepted as final.

## Threats / confounds

- Equilibria are workload-dependent (steady benign multi-source stream); any
  change to decay, `diffuse_alpha`, injection strengths, or band behaviors
  moves them — **re-run the equilibria probe before retuning anything**
  (stated at `ResonanceField.DEFAULT_THRESHOLDS`).
- Single seed for the band-choice runs; the harness adds seeds 42/7/11.
- Novel tokens first encountered during a dream-band step register EPHEMERAL
  in the ecology (existing symbols keep their class; corpus vocabulary is
  pre-registered LANGUAGE at boot) — dream semantics, noted because the dream
  band was previously never active.
- Resistance was validated under explore-pinned rhythm; the adversarial arm
  should be re-run under live bands (standing BACKLOG item 4 covers this).

## Open / next

- Warmup trust drain + identity_erosion ambient weakening (both BACKLOG §1) —
  the governance-side roots this rescale exposed; detectors were calibrated in
  the explore-pinned world.
- `dream_cycle_trigger` ("stabilize", entry-point lever) now fires only during
  cold-start consolidation; revisit whether it should also fire in the dream band.
- Bond-gate work (BACKLOG §1) now has two facets: the coherence-mean axis and
  dream-band crystal starvation in untrained stacks.
