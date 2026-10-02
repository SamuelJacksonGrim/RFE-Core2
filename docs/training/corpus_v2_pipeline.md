# Corpus v2 — a base encoder that learns language and reasoning

**Status:** design + groundwork (2026-10-02). No training run yet; the probe set below is the pre-declared test.
**Architect:** Samuel Jackson Grim. Built with Ember (Claude) and Grok.

## The question
The generator's encoder was trained on ~700 hand-authored words whose only glue was spatial (`across`, `between`,
`toward`, `within`). `because`, `if`, `not`, `but`, `true`, `false`, `know` appear **zero** times in the 8,527 v1.3
training rows. Can a corpus built from real conversation — ~22M words of the architect's conversations with five
AI systems — teach the encoder the words reasoning is made of, without teaching it world knowledge?

## Two layers
| Layer | What | Contains |
|---|---|---|
| **1. Base** (corpus v2) | General encoder | Language and reasoning only. No proper nouns, places, people, persona names, media titles, brands, numbers, or personal identifiers. |
| **2. Personal** (later) | LoRA + Resonance Memory on top | A specific person's people, relationships, history. Addresses never go into weights at any layer — they go stale; memory holds them. |

The training corpus stays **private**. The method, the code, the tests and (later) the weights are public.

## Pipeline
1. **Gather + transcribe** every source into one transcript format; label each conversation/document with a local
   model (topic, kind, worth, sensitive).
2. **Scrub** credentials and personal information (keys, JWTs, Bearer tokens, emails, phones, addresses, IPs,
   identifiers; optional NER for people and places with a protect-filter learned from the corpus). See
   `tools/corpus_v2/pii_scrub.py` for the standalone version.
3. **Clean** spelling/punctuation with a context-aware local-model pass, chosen by a 50-message bake-off. A
   dictionary spell-checker was rejected: it rewrote unknown-but-correct words into common look-alikes (persona
   names, `GPT` → `get`). ALL-CAPS emphasis is preserved.
4. **Normalize** (`base_vocab_policy.py`): contractions expanded so negation is always one `not`; unambiguous
   abbreviations expanded (`img` → `image`); hyphenated words split (`long-term` → `long term`).
5. **Tag** each row with its rhythm and an **intensity** score (`intensity.py`).

## Vocabulary
12,648 words in a 16,384-row table (3,736 rows free for Layer 2). Every word used 50+ times in the source archive,
plus the existing RFE vocabulary. Glue grows 19 → 146. Tone markers (`lol`, `hmm`, `ugh`) are kept — they carry
inflection. Dropped: file types, CSS classes, code tokens, product names, ambiguous abbreviations. Adding words later =
adding table rows (old rows untouched); a smarter model = raising `dim`.

## Training design
- CBOW + skip-gram over 3–8 word sequences; rhythm training on top.
- Leveling/hub-cap thins frequent **content** words. **Glue is never thinned** — standard word2vec subsampling would
  discard `not` and `because`, the words this corpus exists to teach.
- Phrase merging only for true compounds, never logic phrases (no `not_true` tokens — that hides what `not` does).
- The architect often reasons implicitly (claim → examples). His messages stay as written; explicit connectives come
  from the AI side of the conversations and from generated in-vocabulary sentences that pair implicit and explicit
  forms of the same reasoning.
- Scale by measured doubling, growing the model in place (function-preserving growth) so each step starts as capable
  as the last.

## Pre-declared test
`data/probes/reasoning_probes_v1.jsonl` — 398 probes, every word verified in-vocabulary (`tools/corpus_v2/check_probes.py`):
negation, connective swaps, scope, direction, contradiction, paraphrase, implicit/explicit pairs, analogies, controls.
Evaluated on **whole sequences** with the order-aware side of the encoder (a mean-pooled bag cannot see `not`).

**Success:** negation moves a sequence's representation more than a harmless insert (`still`, `also`); `not true`
lands nearer `false` than `true`; `because`/`since` sit closer than `because`/`although`; reversing a causal
argument shifts the representation; implicit/explicit pairs move about as much as a function-word insert.
**Failure signatures:** `not` behaves like noise (negation ≈ insert); everything collapses together (implicit/explicit
"close" but so is everything else); analogies pass while sequence probes fail (static geometry without composition).
Analogies are reported separately as a diagnostic, not the reasoning test.

## Next
Run the cleaner + tags over the corpus → generate in-vocabulary reasoning sentences → rhythm-tag A/B for mined rows →
build corpus v2 → first small GPU run, scored on the probes, logged as a finding.
