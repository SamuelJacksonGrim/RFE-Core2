# §6.3 gain-sign — what is the feedback sign on the coherence range the system can actually reach?

- **Date:** 2026-06-12
- **Substrate:** (a) live stack with synthetic phase-seeded warm (the shipped
  standalone instrument); (b) live full stack mid-workload, real field states,
  real probe vectors (in-run sampling inside the field-map matrix).
- **Probe:** (a) `tests/diagnostic/lockin/gain_sign_check.py` (run 1, raw:
  `logs/2026-06-12-gain-sign-check-run1.log`); (b)
  `tests/diagnostic/lockin/secondlocker_field_map_probe.py` in-run sampler —
  every 25 steps, `field.coherence_impact()` measured **pre-injection**
  (guardrail-compliant, observe-only, non-destructive) for three probe
  classes: recent (perturbed real injections), novel (random unit), anti
  (negated recent). 570 samples across 30 cells. Raw:
  `logs/2026-06-12-secondlocker-field-map.json`.
- **Status:** active — conditional verdict; low-coherence arm unreachable.
- **Depends on:** 2026-06-12-secondlocker-field-map.md (host matrix),
  docs/lock_in_remediation_plan.md §6.3 (the gate this answers).

## Question

§6.3 gates Fix 0-A (and any coherence→loop coupling, Fix 2's wiring included):
if injection strength tracked `coherence_impact`, would the closed loop
stabilize or run away — especially at **low** coherence, where a positive gain
turns drift into collapse?

## Pre-declared signatures (instrument + probe headers, before the runs)

- **STABILIZING:** gain sign NEGATIVE at low coherence (restoring force).
- **RUNAWAY:** gain sign POSITIVE at low coherence.
- **CONFOUNDED:** probed-minus-control within float noise, or the sign tracks
  dilation rather than coherence. In-run sampler: |mean| ≤ noise floor
  (0.25 × |novel-control|) per bin.

## Result (observed)

**(a) Standalone instrument — CONFOUNDED, by its own criteria.** Targets
0.10–0.40 achieved only 0.49–0.94 (the phase-seeded warm cannot reach the
chaotic regime: mean-pairwise phase coherence over 64 vectors has a structural
floor near 0.5 — many vectors cannot be made pairwise anti-phase). 8 of 10
levels flagged CONFOUND; instrument's own verdict line: "low-coherence points
all CONFOUNDED — no Fix 0-A verdict." A second defect found on inspection:
the control subtracts a *phase-metric* drift from an *alignment-metric*
impact (different quantities), and the alignment metric is scale-invariant
under pure exponential decay — the proper no-injection control is ~0 by
construction.

**(b) In-run sampling on real states (570 samples, 30 cells):**

| | value |
|---|---|
| coherence levels reached | **[0.990, 1.000] — nothing below, under any band/seed/arm** |
| bins [0.00–0.95) | unreachable (no samples) |
| bin [0.95, 1.0]: recent | −0.01607 |
| bin [0.95, 1.0]: novel (control) | −0.01606 |
| bin [0.95, 1.0]: anti | −0.01605 |
| per-arm: control / pretrained | −0.0195 / −0.0126 (same insensitivity) |

## Interpretation

1. **The low-coherence regime is unreachable in vivo.** Across the full
   operational workload space (incl. 2870-sequence broad band), the live
   field never leaves [0.99, 1.0]. The regime §6.3 most wanted to
   characterize cannot be produced on the live substrate by workload, and the
   synthetic route is structurally confounded. That *is* the §6.3 answer for
   the gating question's domain: the runaway scenario lives in states the
   system does not visit.
2. **At the reachable end, there is no direction-selective feedback at the
   margin.** Recent, novel, and anti-aligned probes read identical impact to
   ~2×10⁻⁵ — the marginal `coherence_impact` at the pin is a uniform property
   of the saturated integrator (tanh + history-mean comparison), not a
   function of probe direction. A strength∝impact coupling would scale all
   injections nearly uniformly: no runaway signal, but also no discriminative
   signal for Fix 0-A to exploit at the pin.
3. **Verdict (conditional):** NO RUNAWAY EVIDENCE on the reachable range;
   low-coherence arm UNTESTABLE in vivo. Any future Fix 0-A wiring must
   therefore carry a **runtime coherence guard** (the regime where runaway
   would occur is precisely the regime that could not be tested), and §6.3
   must be re-run if any change makes lower coherence reachable.

## Threats / confounds

- Runs: standalone ×1, in-run sampler ×30 cells (570 samples; arm-split
  consistent).
- The direction-insensitivity could itself be metric saturation (tanh
  flattens marginal differences at high field magnitude) — indistinguishable
  from "true" uniform contraction at the pin, and operationally equivalent
  for the gating question, but named here.
- The novel-probe control shares the impact metric (by design, fixing defect
  (a2)); there is no fully independent second metric in the sampler.
- Probe vecs at 0.10 perturbation of recent injections; larger perturbations
  untested.

## Open / next

1. Record this as the standing §6.3 verdict; revisit only if (i) Fix 2 /
   Fix 0-B changes reachable coherence, or (ii) a phase-adversarial workload
   (the Tier 4.3 open item) lowers the floor.
2. The standalone instrument needs a redesign before it can ever produce the
   low-coherence arm (same-metric control; warm method that can actually
   construct low mean-pairwise coherence, if one exists at N>2) — deferred,
   since the in-vivo answer above covers the gating decision.
