# Wiring a Local LLM in as the Encoder Backend

This directory answers one question: **what does it take to replace the stock
`agents/generator.py` transformer encoder with a local large model
(GPT-OSS-20B, Gemma-3-27B, or Llama-3.1-70B-Instruct-Q4_K_M) — and what changes
when you do.**

Read in order:

1. **This file** — the conceptual model, the decision, and the non-negotiables.
2. **[`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md)** — the actual build:
   adapter code, projection head, caching, quantization, training, wiring, tests.

For the surrounding "what is this system and what does the swap mean" analysis,
see [`../SYSTEM_REVIEW_2026-06-13.md`](../SYSTEM_REVIEW_2026-06-13.md).

---

## The mental model in one paragraph

`Generator` is **not** a text generator. It is an *encoder*: `List[str]` tokens →
one L2-normalized `dim=128` vector. The entire RFE-Core2 organism (field,
watcher, witness, emotion, governance, values, subjective time) is a dynamical
system that runs *on those vectors*. So "wiring in a 20B model" means **replacing
the sensory cortex that turns tokens into vectors** — not adding a chatbot.
RFE-Core2 will still not emit language; it will *perceive* with a vastly better
sense organ.

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
- **This is the roadmap's own lever** — `ROADMAP.md` states generator input
  diversity is the binding constraint on adaptivity and that "raising dim,
  training, and the eval-decision are the more upstream lever." A pretrained LLM
  is the strongest possible version of that lever.

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

**Buys:** genuinely high-rank, semantic input — the condition under which the
documented 0.998 coherence lock-in may finally loosen; meaningful governance
signal; real value-tension geometry; a shot at Tier 4.3's unreached chaotic
regime. See `../SYSTEM_REVIEW_2026-06-13.md` §6.3.

**Doesn't buy:** a voice (no decode path exists), or freedom from the compute
bill (a 70B forward pass per `generate()` × many calls/step — caching is
mandatory, not optional). See the guide's *Performance* and *Caveats* sections.

---

## Model picker (start here)

| If you want… | Use | Why |
|---|---|---|
| Lowest friction, first proof-of-life | **GPT-OSS-20B** | Apache-2.0, ungated, MoE (~3.6B active), fits a 24 GB card |
| Best quality on one big card | **Gemma-4-31B-it** | dense 32.7B, Apache-2.0 (ungated), hidden 5376, 256K context; ~20–24 GB at 4-bit; multimodal — we use the text tower only |
| Maximum capability, you have the VRAM | **Llama-3.1-70B Q4_K_M** | ~42 GB GGUF; needs 48 GB / 2×24 GB / CPU offload |

> Note (corrected 2026-06-13): `google/gemma-4-31B` **is** real — it shipped
> 3 Jun 2026 and is Apache-2.0 / ungated (a license win over Gemma 3). 32.7B
> params, hidden size 5376, multimodal (text+image in). We feed text only, so
> the ~550M vision tower is unused weight. The guide uses it as the Gemma
> representative.

Recommended path: **prove the loop on GPT-OSS-20B**, measure whether the field
still pins at ~0.998. That single number is the highest-value readout in the
project. Then scale up.
</content>
