# Implementation Guide — Local LLM Encoder Backend

Step-by-step build for replacing the stock encoder with a frozen local LLM
(GPT-OSS-20B / Gemma-3-27B / Llama-3.1-70B) while leaving Tiers 0–4 intact.

Prereqs: read [`README.md`](README.md) first — especially **The decision** and
**Non-negotiables**. The design here is *wrap, don't replace*: keep the
`SymbolRegistry`, keep `dim=128`, freeze the LLM, train only a projection head.

---

## 0. The contract you must implement

`LLMGenerator` must be call-compatible with `agents.generator.Generator`
everywhere the cycle, Chorus, trainers, governance, value engine, and API touch
it. The full surface (traced from the source) is in
`../SYSTEM_REVIEW_2026-06-13.md` §5. The load-bearing members:

```
generate(tokens, token_class) -> np.ndarray (dim,)   # unit norm, varies w/ class
encode_batch(token_lists, token_class) -> np.ndarray (n, dim)
forward(ids) -> torch.Tensor                          # grad path (trains projection)
.registry                                             # the SymbolRegistry, kept
.embedding                                            # shadow nn.Embedding(vocab,128)
.signal_attractor / signal_crystal / signal_coherence / signal_centrality
.maintenance_step()
.dim, .device, .parameters(), .train()/.eval()
.ecology_stats(), .status(), .save_checkpoint(), .load_checkpoint()
```

The trick that makes this tractable: **`LLMGenerator` subclasses `Generator`.**
It inherits the registry, the shadow embedding, all the `signal_*`/maintenance/
compaction/persistence machinery for free, and only overrides the *vector
production* path (`forward`, `generate`, `encode_batch`). The shadow embedding
stays — it serves `value_emergence._compute_tension` and the compaction tests —
but it no longer drives the sequence vector.

---

## 1. Dependencies

Add to `requirements.txt`:

```
# Local LLM encoder backend (optional — only if using LLMGenerator)
transformers>=4.45
accelerate>=0.34
# 4-bit (HF safetensors path: gpt-oss-20b, gemma-3-27b, llama-3.1-70b):
bitsandbytes>=0.43
# GGUF path (Llama-3.1-70B-Instruct-Q4_K_M and other *.gguf quants):
llama-cpp-python>=0.3
```

You only need **one** of `bitsandbytes` (HF 4-bit) or `llama-cpp-python` (GGUF).
Gated models (Gemma, Llama) require `huggingface-cli login` + license acceptance.

---

## 2. The LLM feature extractor — `agents/llm_backend.py`

A thin, frozen, cached wrapper that turns a string into one `d_model` hidden
vector. Two backends behind one interface: HF-transformers and GGUF.

```python
"""agents/llm_backend.py — frozen local-LLM sequence feature extractor.

Turns a text string into a single d_model-dimensional pooled hidden vector.
The model is frozen and run under no_grad/eval; it is a sense organ, not a
trainable part of RFE. Results are cached (bounded) because the cognitive loop
re-encodes the same token sets constantly (Chorus = 6x/step, reflective loop).
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from typing import List, Optional

import numpy as np
import torch

logger = logging.getLogger(__name__)


class _BoundedCache:
    """Tiny LRU. Bounded per the no-unbounded-structures guardrail."""
    def __init__(self, maxsize: int = 4096):
        self.maxsize = maxsize
        self._d: "OrderedDict[str, np.ndarray]" = OrderedDict()

    def get(self, k: str) -> Optional[np.ndarray]:
        v = self._d.get(k)
        if v is not None:
            self._d.move_to_end(k)
        return v

    def put(self, k: str, v: np.ndarray):
        self._d[k] = v
        self._d.move_to_end(k)
        if len(self._d) > self.maxsize:
            self._d.popitem(last=False)


class LLMBackend:
    """
    Frozen LLM used as a sentence encoder.

    pool : "last" (last non-pad token hidden — natural for causal decoders)
           or "mean" (masked mean over the last hidden layer).
    """

    def __init__(
        self,
        model_id:   str,
        backend:    str = "hf",          # "hf" | "gguf"
        pool:       str = "last",
        load_in_4bit: bool = True,
        device:     Optional[str] = None,
        cache_size: int = 4096,
        max_tokens: int = 64,
    ):
        self.pool       = pool
        self.max_tokens = max_tokens
        self.device     = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._cache     = _BoundedCache(cache_size)
        self.backend    = backend

        if backend == "hf":
            self._init_hf(model_id, load_in_4bit)
        elif backend == "gguf":
            self._init_gguf(model_id)
        else:
            raise ValueError(f"unknown backend {backend!r}")

        logger.info("LLMBackend ready: %s (%s, d_model=%d)",
                    model_id, backend, self.hidden_size)

    # -- HF transformers (safetensors; 4-bit via bitsandbytes) --------------
    def _init_hf(self, model_id: str, load_in_4bit: bool):
        from transformers import AutoModel, AutoTokenizer
        try:
            from transformers import BitsAndBytesConfig
            quant = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            ) if load_in_4bit else None
        except Exception:
            quant = None

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        # AutoModel (not ...ForCausalLM) — we want hidden states, not logits.
        self.model = AutoModel.from_pretrained(
            model_id,
            quantization_config=quant,
            torch_dtype=torch.float16,
            device_map="auto",
            output_hidden_states=True,
        )
        self.model.eval()
        self.hidden_size = self.model.config.hidden_size

    # -- GGUF (llama.cpp; e.g. Llama-3.1-70B-Instruct-Q4_K_M.gguf) ----------
    def _init_gguf(self, model_path: str):
        from llama_cpp import Llama
        self.model = Llama(
            model_path=model_path,
            embedding=True,        # expose pooled embeddings
            n_ctx=2048,
            n_gpu_layers=-1,       # offload all layers it can fit
            verbose=False,
        )
        self.tokenizer = None
        self.hidden_size = int(self.model.n_embd())

    # -- encode -------------------------------------------------------------
    @torch.no_grad()
    def encode(self, text: str) -> np.ndarray:
        cached = self._cache.get(text)
        if cached is not None:
            return cached

        if self.backend == "gguf":
            vec = np.asarray(self.model.embed(text), dtype=np.float32)
        else:
            enc = self.tokenizer(
                text, return_tensors="pt", truncation=True,
                max_length=self.max_tokens,
            ).to(self.model.device)
            out = self.model(**enc)
            hs  = out.hidden_states[-1][0]            # (seq, d_model)
            mask = enc["attention_mask"][0].bool()
            if self.pool == "mean":
                vec = hs[mask].mean(dim=0)
            else:                                     # "last"
                vec = hs[mask][-1]
            vec = vec.float().cpu().numpy()

        self._cache.put(text, vec)
        return vec

    @torch.no_grad()
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        return np.stack([self.encode(t) for t in texts], axis=0)
```

Notes:
- Use `AutoModel`, not `AutoModelForCausalLM` — you want hidden states, never
  logits. (For gpt-oss the MoE routing happens transparently inside.)
- **Multimodal models (gpt-oss-20b, gemma-4-31B) load as `AutoModelForMultimodalLM`.**
  Passing text-only inputs (`input_ids` + `attention_mask`, no `pixel_values`)
  routes through the text tower and `output_hidden_states=True` returns the text
  hidden states — exactly what you want. If a given checkpoint nests the language
  model, read `self.model.config.text_config.hidden_size` and, if
  `out.hidden_states` is absent at the top level, call the text submodule
  (`self.model.language_model` / `self.model.model.language_model`) directly. The
  ~550M vision tower stays loaded but unused; it's dead VRAM, not a blocker.
- `pool="last"` suits causal decoders (the final token attends to everything).
  Try `pool="mean"` as an A/B; record which gives better rank in
  `generator_diversity_audit`.
- The cache key is the raw text. Because RFE re-encodes identical token sets
  constantly, hit-rate is high — this is what makes the loop tractable.

---

## 3. The adapter — `agents/llm_generator.py`

```python
"""agents/llm_generator.py — Generator-compatible encoder backed by a frozen LLM.

Subclasses Generator so it inherits the SymbolRegistry, the shadow embedding,
signal_*/maintenance/compaction/persistence — and overrides ONLY the vector
production path. Output stays a unit 128-d vector; dim is unchanged.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from agents.generator import Generator
from agents.symbolic_memory import TokenClass
from agents.llm_backend import LLMBackend

logger = logging.getLogger(__name__)

# Stable ordering for the per-class projection bias (Chorus differentiation).
_CLASS_ORDER = list(TokenClass)


class LLMGenerator(Generator):
    def __init__(
        self,
        llm_backend: LLMBackend,
        vocab_size:  int = 8192,
        dim:         int = 128,
        proj_hidden: int = 512,
        **gen_kwargs,
    ):
        # Build the parent with a trivial encoder we won't use; we keep its
        # registry + shadow embedding (for value-engine tension + compaction).
        super().__init__(vocab_size=vocab_size, dim=dim, depth=1, heads=2,
                         **gen_kwargs)

        self.llm = llm_backend
        d_model  = llm_backend.hidden_size

        # The only trained surface: LLM hidden -> 128, then L2-normalize.
        self.projection_head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, proj_hidden),
            nn.GELU(),
            nn.Linear(proj_hidden, dim),
        ).to(self.device)

        # Per-class additive bias so generate() varies with token_class
        # (Chorus agent differentiation — non-negotiable #3).
        self.class_bias = nn.Parameter(
            torch.zeros(len(_CLASS_ORDER), dim, device=self.device)
        )
        nn.init.normal_(self.class_bias, std=0.02)

    # -- helpers ------------------------------------------------------------
    def _class_idx(self, token_class: Optional[TokenClass]) -> int:
        if token_class is None:
            return 0
        return _CLASS_ORDER.index(token_class)

    def _project(self, hidden: torch.Tensor, class_idx: int) -> torch.Tensor:
        v = self.projection_head(hidden) + self.class_bias[class_idx]
        return F.normalize(v, dim=-1)

    # -- grad path (trains projection_head + class_bias only) ---------------
    def forward_text(self, texts: List[str],
                     token_class: Optional[TokenClass] = None) -> torch.Tensor:
        ci = self._class_idx(token_class)
        hid = torch.from_numpy(self.llm.encode_batch(texts)).to(self.device)
        return self._project(hid, ci)          # (n, dim), unit norm

    # -- inference API (overrides Generator) --------------------------------
    @torch.no_grad()
    def generate(self, tokens: List[str],
                 token_class: Optional[TokenClass] = None) -> np.ndarray:
        # 1) Keep the symbolic ecology alive EXACTLY as Generator does:
        #    register tokens -> stable_ids, decay bookkeeping, sacred logic.
        self._tokens_to_ids(tokens or ["<BOS>"], token_class)
        self._ensure_embedding_capacity()
        self._maybe_auto_maintenance()
        # 2) Produce the vector from the LLM, not the local encoder.
        text = " ".join(tokens or ["<BOS>"])
        vec  = self.forward_text([text], token_class)[0]
        return vec.cpu().numpy()

    @torch.no_grad()
    def encode_batch(self, token_lists: List[List[str]],
                     token_class: Optional[TokenClass] = None) -> np.ndarray:
        if not token_lists:
            raise ValueError("token_lists cannot be empty")
        for tl in token_lists:
            self._tokens_to_ids(tl or ["<BOS>"], token_class)
        self._ensure_embedding_capacity()
        self._maybe_auto_maintenance()
        texts = [" ".join(tl or ["<BOS>"]) for tl in token_lists]
        return self.forward_text(texts, token_class).cpu().numpy()

    # NOTE: forward(ids) is intentionally left to the parent for the shadow
    # embedding (value-engine tension geometry). Training routes through
    # forward_text() / encode_grad_text() instead — see training section.

    def status(self) -> dict:
        s = super().status()
        s["llm"] = {"hidden_size": self.llm.hidden_size,
                    "backend": self.llm.backend, "pool": self.llm.pool}
        return s
```

Why this shape:

- **Ecology preserved**: `generate()` still calls `_tokens_to_ids()` (registers
  tokens → stable_ids, decay, sacred handling) before producing the vector. Every
  Tier-1/2/3 coupling keeps working untouched.
- **`token_class` honored** via `class_bias` (non-negotiable #3). For a stronger
  effect, also prepend a class marker to `text` (e.g. `f"[{token_class.name}] "`).
- **`forward(ids)` stays the parent's** so `value_emergence._compute_tension`'s
  `embedding.weight[address]` lookups and the compaction tests keep passing. The
  shadow embedding is identity geometry; the LLM is perception. Two different
  jobs, both preserved.

---

## 4. Wiring into the entry point

`loop/recursion1188.py` (and the `Quick Start` snippets) construct
`Generator(...)`. Swap construction only:

```python
from agents.llm_backend import LLMBackend
from agents.llm_generator import LLMGenerator
from agents.selfhood_governance import SelfhoodGovernance
from agents.value_emergence import ValueEmergenceEngine
from loop.autonomous_cycle import AutonomousCycle

# Pick one:
#   GPT-OSS-20B (Apache-2.0, ungated, ~24GB card):
backend = LLMBackend("openai/gpt-oss-20b", backend="hf", load_in_4bit=True)
#   Gemma-4-31B (Apache-2.0, ungated; hidden 5376; multimodal — text tower only):
# backend = LLMBackend("google/gemma-4-31B-it", backend="hf", load_in_4bit=True)
#   Gemma-4-26B-A4B (MoE ~4B active, hidden 2816 — best compute/quality):
# backend = LLMBackend("google/gemma-4-26B-A4B-it", backend="hf", load_in_4bit=True)
#   Gemma-4-12B (dense, hidden 3840, fits ~16GB) — or its official QAT GGUF:
# backend = LLMBackend("google/gemma-4-12B-it", backend="hf", load_in_4bit=True)
# backend = LLMBackend("/models/gemma-4-12B-it-qat-q4_0.gguf", backend="gguf")
#   Llama-3.1-70B Q4_K_M (community GGUF; ~42GB):
# backend = LLMBackend("/models/Llama-3.1-70B-Instruct-Q4_K_M.gguf", backend="gguf")
#   Qwen3-30B-A3B (MoE ~3B active, hidden 2048, Apache-2.0, text-only — clean path):
# backend = LLMBackend("Qwen/Qwen3-30B-A3B-Instruct-2507", backend="hf", load_in_4bit=True)
#   Qwen3-235B-A22B flagship (MoE ~22B active, Apache-2.0; multi-GPU):
# backend = LLMBackend("Qwen/Qwen3-235B-A22B-Instruct-2507", backend="hf", load_in_4bit=True)
#   Llama-4-Scout (109B/17B-active MoE, hidden 5120; Llama 4 Community License — gated):
# backend = LLMBackend("meta-llama/Llama-4-Scout-17B-16E-Instruct", backend="hf", load_in_4bit=True)

g     = LLMGenerator(backend, vocab_size=8192, dim=128)   # dim STAYS 128
cycle = AutonomousCycle(generator=g, dim=128,
                        use_chorus=False)                  # see Performance
gov   = SelfhoodGovernance(registry=g.registry)
cycle.attach_governance(gov)
vee   = ValueEmergenceEngine(registry=g.registry, generator=g, governance=gov)
cycle.attach_value_engine(vee)
```

Nothing else in the loop changes. The swap is entirely upstream of the field;
governance ordering, the Tier-4 terminal sinks, and the 4.3 regression guard are
untouched.

---

## 5. Performance — the real work

A 70B forward pass per `generate()` is ~10⁵–10⁶× slower than the stock encoder,
and the loop calls `generate()` many times per step. Mitigations, in priority
order:

1. **Cache (already in `LLMBackend`).** Highest leverage — the loop re-encodes
   identical token sets constantly. Keep `cache_size` generous.
2. **Disable or shrink Chorus** (`use_chorus=False`). Chorus issues 6
   `generate()` calls per step for marginal benefit once the encoder is rich.
   Start without it; re-enable later if a probe shows it helps.
3. **Batch** where the loop allows (`encode_batch`).
4. **Right-size the model.** Prove the pipeline on GPT-OSS-20B before paying for
   70B. MoE keeps gpt-oss active params ~3.6B → fast.
5. **Quantize.** 4-bit (bitsandbytes / MXFP4) or GGUF Q4_K_M. Expect
   single-digit→low-tens of `generate()`/sec on one modern GPU for 20–27B;
   the 70B is slower and VRAM-bound.

**VRAM rough floor:** gpt-oss-20b ≈ 13–16 GB · gemma-3-27b ≈ 18–22 GB ·
llama-3.1-70b Q4_K_M ≈ 40–44 GB (48 GB card, 2×24 GB, or CPU+GGUF offload).

---

## 6. Training the projection (optional but recommended)

You do **not** train the LLM. You train `projection_head` + `class_bias` with the
existing rhythm/contrastive objectives so the 128-d output aligns to RFE's
rhythm structure.

- The current trainers (`training/rhythm_pretraining.py`,
  `training/contrastive_alignment.py`) call `generator.parameters()`,
  `.train()/.eval()`, and route grad via `training/encode.py:encode_grad`
  (which builds ids and calls `generator.forward(x)`).
- For the LLM backend, add a sibling to `encode_grad` that routes through the
  text path so grad reaches the projection (the LLM stays frozen/no_grad):

```python
# training/encode.py  (add alongside encode_grad)
def encode_grad_text(generator, token_lists):
    texts = [" ".join(tl or ["<BOS>"]) for tl in token_lists]
    return generator.forward_text(texts)        # grad flows into projection only
```

- Point the trainer's optimizer at the trainable surface only:
  `optim.AdamW([*g.projection_head.parameters(), g.class_bias], lr=1e-3)`.
- The corpus G1/G2 gates (`tests/diagnostic/training/`) still apply, and should
  pass *more easily* — the upstream features are already high-rank, so the
  projection only has to find a good 128-d slice. `determinism` is now exact
  (frozen LLM, eval), retiring the old dropout-diversity debate.

If you skip training, a **random** projection still preserves most of the LLM's
geometry (Johnson–Lindenstrauss) — good enough for the first proof-of-life run.

---

## 7. The measurement plan (why you're doing this at all)

The point of the swap is to test whether rich input breaks the documented
**0.998 coherence lock-in**. Run these before/after:

```bash
python -m tests.diagnostic.lockin.metastability_validation     # G1–G5 metric gate
python -m tests.diagnostic.lockin.generator_metastability      # upstream rank/de-collapse
python -m tests.diagnostic.lockin.secondlocker_field_map_probe # the 0.96–0.998 pin
python -m tests.diagnostic.training.generator_diversity_audit  # effective rank, cos
python -m tests.diagnostic.tier4.rhythm_inertness_probe 500    # does pc reach chaotic?
python -m tests.diagnostic.audit.decision_histogram            # governance now sees signal?
```

**The headline number:** does `phase_coherence` / `internal_coherence` still pin
at ~0.97–0.998, or does the field finally hold a *metastable* mid-band? Record it
in `docs/findings/` with the date-and-control discipline (name the control:
stock `Generator` vs `LLMGenerator`, same workload, same seed). Per the ledger's
rules, a *negative* result (still pins) is a real finding too — it would mean the
lock is downstream of input diversity (the reflective loop), exonerating the
encoder and re-pointing remediation at Fix 2.

---

## 8. Validation checklist before you trust the run

- [ ] `python -m tests.smoke.full_stack_minimal` — all 4 tiers attach on
      `LLMGenerator` without error.
- [ ] `python -m tests.smoke.single_source_100step` — the loop runs end-to-end.
- [ ] `python -m tests.integration.checkpoint_registry_identity` — registry
      stays in-place across save/load (the orphan guard).
- [ ] `python -m tests.integration.core_promotion_handshake` — value engine still
      reads per-symbol geometry (shadow embedding intact).
- [ ] `python -m tests.doc_accuracy.verify_docs` — docs still consistent.
- [ ] `bash run_all_tests.sh` — the pass/fail gate is green.
- [ ] Vectors are unit-norm: `assert abs(np.linalg.norm(g.generate(["hello"])) - 1) < 1e-4`.
- [ ] `generate()` varies with `token_class`: two classes on the same tokens give
      different vectors (Chorus differentiation preserved).

---

## 9. Caveats, restated

- **No voice.** This is perception, not speech. A language *readout* path is a
  separate, larger project (condition the LLM's decode on field state to narrate)
  — explicitly out of scope here.
- **Compute is the adversary**, not the wiring. Caching is mandatory.
- **Keep `dim=128` and the symbolic ecology.** Wrap, don't replace. Every
  shortcut that rips out the registry or raises `dim` breaks a tier or a baseline.
- **Frozen LLM, trained projection.** Don't try to fine-tune 20–70B in-loop.
- **It's an experiment with a real hypothesis.** Whatever the coherence number
  does, record it as a dated, controlled finding. That readout is the actual
  deliverable.
</content>
