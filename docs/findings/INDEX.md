# Findings index — the one-screen map of the ledger

One line per finding: what it established, and whether it is still the
authoritative read. **Read this before grepping the ledger.** Statuses:

- **standing** — still the authoritative result on its question
- **superseded** — a later finding corrects or absorbs it (named)
- **resolved** — its open work landed; kept as the record of how
- **shelved** — result stands, the work it feeds is deliberately parked
- **historical** — a completed arc step; context, not current truth

Inline `→ DONE/DECIDED/…` stamps inside each finding mark which of its Open
items landed (added at resolution time, same-commit — the anti-tail-chasing
rule). Every finding file must appear here (CI-enforced by `verify_docs`).

| Finding | One-line verdict | Status |
|---|---|---|
| `2026-06-06-coherence-is-not-plasticity` | Reframed lock-in: measure attractor *plasticity*, not the coherence value; set the 3-step probe program | historical (program executed 06-07) |
| `2026-06-06-conformity-bias-fix0b` | Reaper's coherence lean is real but small; symmetric gate safe-but-minor, not the lock lever | historical |
| `2026-06-06-expression-decollapse` | `diversity_blend` (0<b<1) restores multi-regime expression; 0 re-collapses | **standing** (CLAUDE.md invariant) |
| `2026-06-06-frame-correction` | Metastability belongs upstream (per-stage streams), never on the long-memory field | **standing** (locus invariant) |
| `2026-06-06-multilayer-lock` | First 3-lock picture (generator/gate/moat) | superseded — 06-07 arc struck/downgraded all three |
| `2026-06-06-read-side-boundary` | Accumulated feedback gates *survival* only; it never reaches generation | **standing** |
| `2026-06-07-attractor-migration` | Field RIGID under best-case surviving novelty; magnitude moat surmountable, not the locker | **standing** |
| `2026-06-07-fix0b-fullloop-validation` | Conformity lean +1.16%/lap in vivo, coherence-only lean not separable; keep asymmetric | historical |
| `2026-06-07-gate-decomposition` | The ~85% gate block was a single-source HHI artifact; diverse input passes 100% | **standing** |
| `2026-06-07-reconstruction-ablation` | **The lock is the reflective loop** — suppressing only it frees migration ~100× | **standing** (core result) |
| `2026-06-07-reflective-loop-cost` | Attenuation cost band/cliff mapped (mock-era; overstated per 06-09) | historical (numbers stand for Fix 2 revival) |
| `2026-06-08-fix2-trigger-calibration` | `coherence_delta` trigger falsified; raw-gen novelty (gnov W=10/T≈0.65) separates | shelved with Fix 2 (spec ready) |
| `2026-06-08-generator-dropout-diversity` | ~Half of apparent input diversity was dropout noise → led to the eval decision | **standing** (authoritative diversity read) |
| `2026-06-09-fix2-live-generator` | Real regimes need common-mode removal for gnov to engage (98% w/ projection) | **standing** (trigger form) |
| `_addendum-2026-06-09-migration-dim256` | dim 256 ~2× more diverse even untrained | **standing** (the documented second lever) |
| `2026-06-11-corpus-g1-pretrain` | Gate G1 PASSED: corpus coverage buys held-out generalization (eff_rank ~2.4×) | **standing** |
| `2026-06-11-trainer-gradient-path` | Trainer gradient path was broken in 2/3 trainers; repaired — training works | **standing** |
| `2026-06-12-checkpoint-registry-orphan` | `load_ecology` rebinding orphaned governance/values; in-place load + standing guard | resolved (guard live in CI) |
| `2026-06-12-engine-sidecar-instrumentation` | LAE/PLE sidecar reads the core without perturbing it; liminality confined to warm-up | **standing** |
| `2026-06-12-gain-sign-reachable-range` | §6.3 conditional verdict: no positive feedback in reachable range; low-coherence arm unreachable | **standing** (gates Fix 0-A coupling) |
| `2026-06-12-governed-feedback-first-contact` | Sister-engine outputs re-enter through the gate cleanly; participation benign | **standing** |
| `2026-06-12-phase2-fullstack-g2` | Gate G2 PASSED + **SECOND-LOCKER**: pin persists on trained input — the loop, not the generator, is the operative lock | **standing** (pivotal) |
| `2026-06-12-secondlocker-field-map` | The pin is seed-, band-, and regime-invariant (30-cell map); identity rail clean | **standing** |
| `2026-06-15-cii-ignition-decomposition` | CII≈0 at dim 64; ITG actuator built and found inert — lever is upstream | historical (dim-64 scope; ITG kept as scaffold) |
| `2026-06-15-cm-identifiability` | Cm is a saturated angular echo, not an identifying read | superseded — refined by `identifiability-suite` |
| `2026-06-15-identifiability-suite` | Regime-state labels are robust; all scalar magnitudes v0.1-fragile | **standing** (gauge caveat) |
| `2026-06-15-loop-attenuation-novelty-gate` | Novelty-gated attenuation works; 0.30 ceiling is the thin cost-clean band | **standing** (graduated 06-20; ceiling rule) |
| `2026-06-15-training-ignites-expression` | Corpus training flips expression locked→ignited (3/3 at dim 64; common-mode halved at 128) | **standing** |
| `2026-06-19-ignition-channel-build-a` | λ ignition import-isolated; writes generator weights only, gate unreachable | **standing** |
| `2026-06-19-witness-reaper-build-c` | ⊘ reads 4-dim thinness, names regions, advises non-bindingly, touches nothing | **standing** |
| `2026-06-20-build-b-solvent-and-integrity-consumer` | ⊕ gate gates composition on λ (8/8); ⊘ consumer is the first *user* (safe in `named_only`) | **standing** |
| `2026-06-20-ground-truth-pass1-compose-the-runtime` | Substrate floor real; `build_engine()` wired as the single composition point | **standing** (structural) |
| `2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain` | Generator common-mode = real floor defect; pretrain+attenuation graduated on measurement | **standing** (graduation basis) |
| `2026-06-20-lever-composition-the-allon-break` | All-ON broke `strong_values 5→0` — isolation-green is not enough | **standing** (origin of the graduation rule) |
| `2026-06-20-the-runtime-is-tier0-only` | The launchable system ran Tier 0 only; tiers lived in the test harness | resolved (fixed by pass 1 + 06-27 API fix) |
| `2026-06-21-oslash-coherence-axis-absolute-alignment` | ⊘ cc-axis dead by construction; redesigned to absolute field-alignment (spec v0.3) | **standing** |
| `2026-06-25-ground-truth-pass3-stack-evaluation` | Composed-engine evaluation before operators; surfaced the pass-3 cracks | **standing** (evaluation snapshot) |
| `2026-06-27-api-entrypoints-tier0-only` | REST/WS entry points had regressed to Tier-0; routed through `build_engine()` | resolved (smoke gap tracked, BACKLOG §7) |
| `2026-06-27-core-gate-fix-deferred-sacred-cascade` | CORE gate fix works alone but sacred promotion cascades the trust layer | deferred (BACKLOG §1 · F8) |
| `2026-06-27-floor-calibration-measurements` | Measure-before-change numbers for the pass-3 cracks (bond floor, CORE path) | **standing** (calibration basis) |
| `2026-06-28-decoder-readout` | Thoughts are readable back as a token cloud — lossy by design, right register for inner voice | **standing** |
| `2026-06-28-dream-channel` | Self-dialogue is safe, non-dominant, adversarial-gated; graduated default-ON | **standing** |
| `2026-06-28-full-system-run` | Levers validated multi-seed (metastability 0.06→0.58); F9/F8/bond gaps named | **standing** (current tuning baseline) |
| `2026-07-04-bonded-adversarial-attack-never-lands` | THE bond-betrayal experiment: attack never becomes a signal (stage-C cos ~0.98 hostile≡benign, 11 seeds) — blocked by two upstream walls: OOV attack vocabulary + pipeline re-collapse | **standing** |

## Raw-data convention (adopted 2026-07-06)

Findings commit their **report, manifest, summary, and plots**. Raw per-step
data (`.jsonl` step logs, console dumps, big `status` snapshots) above ~100 KB
is **gzipped in place** (`gunzip -k <file>.gz` to read) — or attached to a
GitHub release for anything truly huge. Never commit raw multi-MB logs
uncompressed: the 2026-06-28 run alone was 9.1 MB — two-thirds of the entire
repository — before this rule.
