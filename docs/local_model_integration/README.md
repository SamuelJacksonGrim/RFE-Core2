# Wiring a Local LLM in as the Encoder Backend

This directory answers one question: **what does it take to replace the stock
`agents/generator.py` transformer encoder with a local large model (see the
model picker below) — and what changes when you do.**

Read in order:

1. **This file** — the conceptual model, the decision, and the non-negotiables.
2. **[`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md)** — the actual build:
   adapter code, projection head, caching, quantization, training, wiring, tests.

For the surrounding "what is this system and what does the swap mean" analysis,
see [`../SYSTEM_REVIEW_2026-06-13.md`](../SYSTEM_REVIEW_2026-06-13.md).

**Where this sits in the North Star** (`../north_star.md`): this swap is the
**sensory cortex** — a better organ for *perceiving* language as vectors. Its
mirror, the **speech cortex** (an LLM decode conditioned on the thought-vector /
field state, for literal waking speech), is North-Star gap 1 and is *not* built
here — but the wrap-don't-replace pattern in this directory is the template it
will follow.

---

## The mental model in one paragraph

`Generator` is **not** a text generator. It is an *encoder*: `List[str]` tokens →
one L2-normalized `dim=128` vector. The entire RFE-Core2 organism (field,
watcher, witness, emotion, governance, values, subjective time) is a dynamical
system that runs *on those vectors*. So "wiring in a 20B model" means **replacing
the sensory cortex that turns tokens into vectors** — not adding a chatbot.
RFE-Core2 will still not emit literal language; it will *perceive* with a vastly
better sense organ. (Since 2026-06-28 the substrate does have a read-out in the
other direction — the `TokenDecoder` in `agents/decoder.py`, a lossy
bag-of-tokens word-cloud used by the waking dream channel and the dream/listen
tools. That is inner monologue and dream material, not speech; literal sentences
remain the speech-cortex mirror project.)

```
        BEFORE                                AFTER
  tokens ─► Generator ─► 128-d vec     tokens ─► LLMGenerator ──────────► 128-d vec
            (4-layer                            ├─ SymbolRegistry (kept!)   (unit)
             encoder,                           ├─ frozen LLM ─► d_model hidden
             dim=128)                           └─ Linear(d_model→128) + L2-norm
                                                    (the only trained part)
  └──────────── identical downstream ────────────────────────────────────────┘
       field · watcher · witness · emotion · governance · values · time
```

---

## The decision (and why)

**Wrap, don't replace. Keep `dim=128`. Keep the symbolic ecology. Train only a
projection head. Freeze the LLM.**

Rationale, each point load-bearing:

- **Wrap, don't replace** — the `SymbolRegistry` (stable_ids, canonicalization,
  decay/reaper, sacred symbols) is co-equal to the neural net and is wired into
  Tiers 1–3. Governance, trust, bonds, and value emergence all key off
  `stable_id`s. Delete it and the upper tiers go dark. The adapter keeps the
  registry and only changes where the `dim`-vector comes from.
- **Keep `dim=128`** — every subsystem and every baseline JSON is tuned for 128.
  Raising it re-tunes the whole stack and invalidates the regression suite. A
  `Linear(d_model→128)` projection is cheap and keeps the contract.
- **Freeze the LLM, train the projection** — you will not fine-tune 20–70B on a
  workstation, and you don't need to. The pretrained features are already rich
  (that is the entire point). The projection is the small, trainable surface that
  adapts those features to RFE's rhythm/contrastive objectives.
- **This is the roadmap's own lever, with its expectation now calibrated** — the
  original framing ("generator input diversity is the binding constraint") has
  since been refined by measurement: corpus coverage was paid (Gates G1/G2),
  eval-mode was decided, and corpus pretraining halved the generator's
  common-mode — **yet the field's coherence pin survived** (the SECOND-LOCKER
  finding: seed-, band-, and regime-invariant with real trained input). The
  operative lock is the *reflective loop*, and the novelty-gated attenuation
  that loosens it is now default-on. Adaptivity is gated by **both** input
  diversity and the loop; a pretrained LLM is the strongest possible version of
  the *input* half, tested on top of a baseline where the loop half is already
  treated.

---

## Non-negotiables (do not violate)

These come straight from `CLAUDE.md` and the code; breaking them causes silent
breakage, not loud errors:

1. **Keep the `SymbolRegistry` alive and in-place.** Never bypass
   `CanonicalizationPipeline`. Never recycle `stable_id`s. The adapter registers
   every token exactly as `Generator` does. `load_*` must mutate the registry
   **in place**, never rebind it (orphaned-subsystem guard —
   `tests/integration/checkpoint_registry_identity.py`).
2. **Output stays a unit vector.** Downstream injection assumes
   `‖vec‖ = 1`; magnitude is carried separately by `field_gain`. Project then
   `F.normalize`.
3. **`generate()` must vary with `token_class`.** Chorus differentiates its six
   agents by `token_class`; if every class returns the same vector, the Chorus
   collapses. (The guide shows how to honor this — a per-class projection bias or
   a class token prepended to the LLM input.)
4. **Do not touch Tiers 1–4 or the governance ordering.** The swap is strictly
   *upstream* of the field. `dilation_factor` / `subjective_time` stay terminal
   sinks. The 4.3 neutral-`pc=0.5` regression guard stays byte-identical.
5. **`print` is banned in library code** — use the module logger.
6. **Bounded structures only** — the LLM-encoding cache must be an LRU/bounded
   `dict` or `lru_cache(maxsize=…)`, never unbounded.

---

## What this buys you, and what it doesn't

**Buys:** genuinely high-rank, semantic input; meaningful governance signal;
real value-tension geometry; a shot at Tier 4.3's unreached chaotic regime and
at un-pinning the F9 rhythm router. Calibrate the lock-in expectation, though:
corpus-level training alone did **not** de-saturate the field (SECOND-LOCKER),
so the honest question is whether *much* richer input — on top of the
default-on loop attenuation — finally reaches the metastable mid-band. Either
answer is a first-class finding. See `../SYSTEM_REVIEW_2026-06-13.md` §6.3 and
`../../ARCHITECTURE_ANALYSIS.md` §4.

**Doesn't buy:** literal speech (the lossy `TokenDecoder` word-cloud read-out
exists, but sentences need the speech-cortex mirror — North-Star gap 1), or
freedom from the compute bill (a 70B forward pass per `generate()` × many
calls/step — caching is mandatory, not optional). See the guide's *Performance*
and *Caveats* sections.

---

## Model picker (start here)

| If you want… | Use | Why |
|---|---|---|
| Lowest friction, first proof-of-life | **GPT-OSS-20B** | Apache-2.0, ungated, MoE (~3.6B active), fits a 24 GB card |
| Best quality on one big card | **Gemma-4-31B-it** | dense 32.7B, Apache-2.0 (ungated), hidden 5376, 256K context; ~20–24 GB at 4-bit; multimodal — we use the text tower only |
| Maximum capability, you have the VRAM | **Llama-3.1-70B Q4_K_M** | ~42 GB GGUF; needs 48 GB / 2×24 GB / CPU offload |

### Lighter Gemma 4 alternatives (verified 2026-06-13) — best compute/quality

Compute, not wiring, is the real cost (see the guide §5). The Gemma 4 family ships
lighter, all-Apache-2.0 members that ease it dramatically — and Google publishes
**official QAT GGUFs** for two of them, a cleaner local path than community quants:

| Model | Params | Hidden | Notes |
|---|---|---|---|
| `google/gemma-4-26B-A4B-it` | 26B **MoE, ~4B active** | **2816** | the sweet spot — near-31B quality at ~4B active compute; official QAT q4_0 GGUF (`gemma-4-26B-A4B-it-qat-q4_0-gguf`) |
| `google/gemma-4-12B-it` | 12B dense | **3840** | fits ~16 GB / a laptop; official QAT GGUF (`gemma-4-12B-it-qat-q4_0-gguf`); `gemma4_unified` (text+vision+audio) |
| `google/gemma-4-E2B` / `-E4B` | ~2B / ~4B effective | — | tiniest; for smoke-testing the wiring before committing VRAM |

> Note (corrected 2026-06-13): `google/gemma-4-31B` **is** real — shipped Mar–Jun
> 2026, Apache-2.0 / ungated (a license win over Gemma 3). 32.7B params, hidden
> 5376, multimodal (text+image in). We feed text only, so the ~550M vision tower
> is unused weight. The whole Gemma 4 line is Apache-2.0. The projection head
> auto-sizes to whichever `hidden_size` you load, so switching family members is a
> one-line change (`LLMBackend(model_id=...)`) — no other code edits.

### Other frontier families (verified 2026-06-13)

Not the originally-named three, but worth knowing — same wrap-don't-replace
design applies unchanged, projection auto-sizes to `hidden_size`:

| Model | Params | Hidden | License | Notes |
|---|---|---|---|---|
| `Qwen/Qwen3-30B-A3B-Instruct-2507` | 30B **MoE, ~3B active** | **2048** | Apache-2.0 (ungated) | excellent local sweet spot; 256K ctx; text-only (clean encode path, no vision tower) |
| `Qwen/Qwen3-235B-A22B-Instruct-2507` | 235B **MoE, ~22B active** | (auto) | Apache-2.0 | the flagship — top general reasoning/coding in 2026 surveys; for multi-GPU rigs |
| `meta-llama/Llama-4-Scout-17B-16E-Instruct` | 109B total / **17B active** (16 experts) | **5120** | Llama 4 Community (gated; **not** standard OSS) | multimodal, very long context; license is more restrictive than Apache-2.0 |

Qwen 3's small-active MoE designs (`~3B active`) are the most compute-friendly
high-quality encoders here. Llama 4 Scout is capable but its license is the
catch — read it before relying on it. The pure-text Qwen models are the cleanest
fit because there's no unused vision tower to load.

### Re-verified 2026-07-02 (+ what shipped since)

All model IDs above were re-checked against the live Hub on 2026-07-02: every
one still exists, licenses unchanged. Newer families worth knowing, same
wrap-don't-replace design (projection auto-sizes to `hidden_size`):

| Model | Params | License | Notes |
|---|---|---|---|
| `Qwen/Qwen3.5-35B-A3B` | 36B **MoE, ~3B active** | Apache-2.0 | successor to Qwen3-30B-A3B; multimodal (`AutoModelForMultimodalLM`) — feed text only, vision tower is dead VRAM |
| `Qwen/Qwen3.5-9B` | 9.7B dense | Apache-2.0 | small, current, very well supported; multimodal, same text-only note |
| `zai-org/GLM-5.2` | 753B MoE | MIT | frontier-class and text-only, but datacenter-scale — not a workstation option; listed for completeness |

One correction surfaced by the re-check: **`openai/gpt-oss-20b` is text-only**
(`AutoModelForCausalLM`, 21.5B MoE) — an earlier note here grouped it with the
multimodal loaders; that applies to Gemma 4 / Qwen 3.5 / Llama 4, not gpt-oss.

Recommended path: **prove the loop on GPT-OSS-20B**, measure whether the field
still pins at ~0.97+ against the composed default baseline. That single number
is the highest-value readout in the project. Then scale up.
</content>
