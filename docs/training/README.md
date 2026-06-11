# Training path — documentation set

**Status: assessed viable (2026-06-11); plan proposed, not committed scope.**

This folder answers one question, raised when Tier 5 (meta-cognition /
attentional control) was found to be blocked on generator diversity: **is
training the generator the viable path forward, and what does it take?**

The project's own findings already pointed here — the 2026-06-08 diversity
audit ("training may be more load-bearing than downstream refinement") and the
ROADMAP's current understanding ("generator diversity — training, raising dim,
and the eval-decision — is the more upstream lever"). On 2026-06-11 the
question was probed empirically: the training stack's gradient path was broken
in two of three trainers; after repair, 40 epochs of rhythm pretraining took
the deterministic dim-64 generator from eff_rank 1.3 / mean cos 0.855 to
eff_rank 3.1 / mean cos 0.210 with perfect rhythm clustering — on the trained
distribution only. **Training works; corpus coverage is the binding
constraint.** (`docs/findings/2026-06-11-trainer-gradient-path.md`.)

## Verdict in one paragraph

Training is possible **now** — infrastructure exists and is repaired, the
objectives are sound, no external dependencies are missing, and the first
controlled run moved deterministic diversity exactly where the lock-in
analysis said it was needed. What does *not* exist yet is (a) a curated corpus
(the built-in seeds are 20 toy sequences; effects don't generalize past them),
(b) an identity-stability cost reading for training the live system, and
(c) the architect's `.eval()` decision. Those three are the work; none is a
research unknown.

## Documents

| File | What it covers |
|------|----------------|
| `viability_assessment.md` | Current state: generator/attention architecture, what the 2026-06-08 audit measured, trainer inventory + the gradient-path repair, what exists vs what's missing. The evidence behind the verdict. |
| `training_plan.md` | The phased plan: corpus-first pretraining → cost-gated validation → online training in the loop → re-running the lock-in probes → Tier 5 un-deferral. Each phase has pre-declared gates. |
| `data_curation.md` | The corpus question directly: what data exists (almost none), what a curated dataset needs (coverage, rhythm labels, source diversity), how to build it, what is *not* needed. |
| `tier5_readiness.md` | How training gates Tier 5: the prerequisite stack from here to the meta-cognition tier, and what Tier 5 is anchored to in the existing docs. |

## Discipline

Everything here follows the repo's standing rules: empirical results go to
`docs/findings/` (dated, control-named, pre-declared signatures); diagnostics
stay firewalled from CI; toy ≠ live; the trainers must never decide the live
dropout mode (open architect decision, 2026-06-08); and per `ROADMAP.md`'s
status discipline this folder is **direction, not committed scope** until the
architect commits it.
