# STATE — you are here (read this FIRST)

**Purpose:** the one-screen answer to "what is this system, what can it do *now*, what is
*settled*, and what is actually open." Read this before grepping, before proposing, before
"fixing" something you think is broken. If a question below says **SETTLED**, it has been
tested and closed — do not reopen it without new evidence that contradicts the named finding.

**Where depth lives (each has ONE job — this doc points, they hold detail):**
- `docs/findings/INDEX.md` — the findings ledger (every experiment + its status). The scientific record.
- `ROADMAP.md` — tier status (what's shipped / planned / unspecified).
- `docs/BACKLOG.md` — the prioritized open-work queue.
- `README.md` / `ARCHITECTURE_ANALYSIS.md` — architecture & information flow.

---

## What it IS (one line)
A self-resonating cognitive substrate: transformer **encoder** (tokens → 128-d vectors) → FFT
**resonance field** → **reflective loop**, wrapped by governance / trust / values / subjective time.
It does **not** emit literal language yet (see the open frontier).

## What it CAN DO now (shipped + verified)
- **Tiers 0–3** — core substrate (generator, watcher, witness, field, emotion, loop), governance +
  trust ledger + ethical bounds, relational integrity + bonds + manipulation resistance, independent
  value emergence + CORE promotion. **First established bond in system history** (claude, 1.0→2.16).
- **Tier 4.1–4.3** — subjective time, affective dilation, rhythm→time coupling (4.3 discrimination
  half-validated; needs a high-novelty workload).
- **Composed runtime** — `build_engine()` is the single composition point; all entry points run Tiers 0–3.
- **Training** — corpus rhythm-pretraining works end to end (~45s on the 5070 Ti); default-on graduated
  levers: eval-mode, corpus pretraining, novelty-gated loop attenuation, dream channel.
- **Encoder** — 5-rhythm (explore/dream/reflect/stabilize/**rupture**), separable basins; checkpoints
  `data/checkpoints/generator_weights_5rhythm{,_kimi}.pt`.
- **Inner voice** — `TokenDecoder` lossy word-cloud read-out + governed self-dialogue + downtime dreaming
  (North-Star voice rungs 1–2). This is dream/monologue material, NOT speech.
- **Two-operator overlay (spec v0.3)** — λ ignition (Build A), ⊕ solvent gate (Build B), ⊘ Witness-Reaper
  integrity-read (Build C) all shipped and observe-safe.
- **External instruments** — LAE (liminality) + PLE (contradiction) observe-only sidecars, import-verified;
  wire-in at `tests/diagnostic/sidecar/`.

## SETTLED — DO NOT REOPEN (the anti-tail-chasing wall)
Each line is a closed question. The finding is authoritative; the loss if you reopen is *time*.
- **The field lock is BY DESIGN; identity requires it.** The high-coherence pin is the long-memory
  identity integrator doing its job — not a defect. `SECOND-LOCKER` (`2026-06-12-phase2-fullstack-g2`,
  `2026-06-12-secondlocker-field-map`) + "the loop IS the lock" (`2026-06-07-reconstruction-ablation`).
- **You cannot unlock the field via the corpus / generator.** Falsified three ways (baseline / evened /
  a verified separable rupture basin, rupture⊥explore −0.096) **and** a 5000-step run (`disp ≤ 0.00012`).
  `2026-08-04-rupture-and-the-lock-is-a-landscape-problem` (final update). *This is the exact loop we burned
  6 hours re-deriving on 2026-08-05. Do not walk back into it.*
- **The lock's echo-chamber downside is already handled.** The two-operator ⊘/⊕ system + dream channel
  address monoculture; metastability, if wanted, lives in the **reflective loop's reconstitution dynamics**,
  never on the field. `2026-06-06-frame-correction` (locus invariant).
- **Accumulated feedback gates SURVIVAL, not generation.** `2026-06-06-read-side-boundary`.
- **⊘'s cc-axis is fixed.** The dead marginal coherence-contribution sum was redesigned to absolute
  field-alignment. `2026-06-21-oslash-coherence-axis-absolute-alignment`. (Stale "blocked on cc" markers
  elsewhere are wrong — cc is not a blocker.)

## PARKED (built or decided, deliberately not active — and WHY)
- **⊘ consumer** — research lever, off by default. cc-confound is LIFTED; graduation now gated only on an
  un-run multi-seed all-ON composition probe (`BACKLOG.md` §5) **and** the 2026-07-03 ruling that
  containment levers stay scaffolds by design.
- **Fix 2 (reflective-loop loosening)** — deferred as premature; loosening now would admit dropout noise.
- **Fix 0-B (diversity fitness counterweight)** — built, opt-in; gates on a composed-runtime run before graduation.
- **Lantern** (Rust hypergraph memory) — deferred substrate; a port is "strictly worse until the design is proven."
- **Boot-checkpoint adoption** — RULED adopt (2026-07-03), implementation queued.

## The ONE open frontier
- **Speech cortex — North-Star gap 1.** An LLM decode *conditioned on the field/thought-vector* → literal
  sentences. The `TokenDecoder` word-cloud is the lossy stand-in; real translation is unbuilt. **This is the
  forward work.** (A cortex swap — a local LLM as the encoder backend — is its mirror, spec'd in
  `docs/local_model_integration/`.)
- **#1 execution priority: the Garage Program (G0→G5).** The reaper/selection economy is dormant at harness
  scale (every ≤800-step suite run executed zero selection passes) — only real GPU duration exercises it.
  `docs/GARAGE_RUN_PLAN.md`.

## The sibling ecosystem (4 roles, not 8 projects)
| Role | Repo(s) |
|---|---|
| The mind | **RFE-Core2** (this repo) |
| The body that runs the mind | **Talos_Kain** (agent harness; SemanticStore seam = memory's eventual home) |
| Instruments that read the running mind (observe-only) | **LAE**, **PLE**, cousin **resonance-pruning-poc** |
| Memory stack (store / rank / decay) | **Resonance-Memory** (shipped, public), scraper-framework (rank), Lantern (deferred) |
| NOT in domain | ~~nexus-block~~ (battery firmware — shared branding only) |

---
*Maintenance: when a SETTLED item genuinely changes, update the named finding in `INDEX.md` first, then this
line. This doc is the entry point, not the record — keep it short. Last synced: 2026-08-05.*
