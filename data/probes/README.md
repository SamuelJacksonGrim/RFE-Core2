# Reasoning probes for RFE-Core2 pass 1

Written before training, so we cannot move the target after. Every token is in `content_words.txt` or `glue_words.txt`. Lowercase, no proper nouns, no numbers.

## What I would change about the plan

The four tests in the brief are the right *family*. Three of them are the wrong *primary metric* for this encoder.

**1. Analogies are a diagnostic of linear structure, not of reasoning.**

This is a small transformer encoder trained CBOW-style on 3–8 word sequences. Word2vec analogies work because SGNS on a large corpus induces approximately linear offsets. A transformer CBOW of short sequences may encode the same relations and still fail `true - false + right ≈ wrong`. Treat analogy failure as “the geometry is not word2vec-like,” not as “it did not learn reasoning.” Sequence probes (negation, connective, direction, scope) are the actual reasoning test.

Score `antonym_morph` separately from `antonym_truth`. `valid:invalid :: possible:impossible` can be solved by an affix detector. `true:false :: right:wrong` cannot.

**2. Encode the whole sequence. Do not mean-pool static word vectors.**

If you extract a word embedding by averaging contexts and then add those vectors, every sequence probe collapses to a bag and you will “discover” that the encoder ignores `not` and word order. Run negation / connective / direction / scope through the same sequence representation you train with (the transformer output over the 3–8 token window). Analogies can use either the sequence encoder on single-word inputs or a static word vector, but report which.

**3. The despite example was ungrammatical.**

`despite` takes an NP, not a clause. I used `although` / `though` for clause concession and `despite` only against `because of` + NP. Near-paraphrase connectives are in the set as calibration: `because`/`since`, `although`/`though`, `therefore`/`thus`/`hence` should stay close; `because`/`although` and `if`/`unless` should move.

**4. Implicit/explicit closeness is uninterpretable without controls.**

Inserting `because` changes the bag. A model that barely uses `because` will look “close” for the wrong reason; a model that has a large `because` vector will look “far” even if it treated the pair as a paraphrase. Function-word insertion controls (`still`, `already`, `also`, `just`) are the close-calibration. Content swaps (`holds`→`fails`, `tone`→`noise`) are the shift-calibration. Implicit/explicit should land with the function inserts, not with the content swaps.

**5. The original plan almost missed the tests that actually distinguish bags from reasoning.**

- **Direction:** `it holds because the seal is strong` vs `the seal is strong because it holds`. Same words, opposite causal order. CBOW that ignores position will call these identical.
- **Scope:** `not all of them hold` vs `all of them do not hold`. Not-all is not none.
- **Paraphrase of negation:** `it is not true` should sit closer to `it is false` than to `it is true`. “Negation moved the vector” is weaker than “negation landed on the antonym.”
- **Symmetry:** reversing `like` should stay close; reversing `causes` should not. Same structural change, opposite expectation.

Those four are more load-bearing than another dozen `warm:hot` analogies.

**6. Glue-list membership is not training.**

`because`, `if`, `not`, `unless`, `true`, `false` being in the vocab does not teach the encoder their relations. These probes only mean anything if pass-1 sequences actually use those words in compositional contexts. If the corpus is still mostly spatial glue, the encoder cannot pass this set, and that is a data bug, not an architecture bug.

## How items were chosen

Short, boring frames. Repeated stems (`hold`, `claim`, `seal`, `tone`, `proof`, `fail`) so differences come from the relation word, not from new content. No world knowledge, no names, no digits.

Analogies are seed-pair crosses inside one relation (the Mikolov pattern), plus a few hand-picked quadruples that do not sit in a clique. Crossing `true:false` with `start:stop` would mix logical polarity with event polarity; I did not do that.

Sequence length is 3–8 tokens, matching the training window.

## Relation types, ranked by how much they test reasoning

1. **scope** — quantifier/negation interaction. If this fails, it did not learn logical form.
2. **direction** — causal and conditional order. If this fails, it is still a bag.
3. **paraphrase** (`not true` ≈ `false`) — composition. The single best lexical-reasoning check.
4. **negation** vs **control.function_insert** — did `not`/`never`/`no` move the representation more than `still`/`also`?
5. **connective** opposition vs near-paraphrase — `because`/`although` should separate more than `because`/`since`.
6. **factive / modality / quantifier** — attitude and force ladders (`know`/`believe`/`doubt`, `must`/`may`/`cannot`, `all`/`some`/`none`).
7. **implicit_explicit** — Samuel’s actual writing pattern. Should track function-insert, not content-swap.
8. **contradiction** — lexical opposites with the same syntax. Compare to negation: is `false` as far from `true` as `not true` is?
9. **symmetry** — same reversal, opposite expectation from direction.
10. **analogies** — useful, secondary. `antonym_truth`, `cause_effect`, `mental_state`, `modal` matter more than `part_whole` or `agent_action`. `antonym_morph` is a ceiling.

Spatial antonyms (`high`/`low`, `inner`/`outer`) are in the set because the old vocab was spatial and you will want to see that those still work. They are language, not reasoning.

## Pre-declared success and failure

Evaluate with **relative** comparisons, not absolute cosine cutoffs. A 128-d encoder will have different cosine scales than a 256-d one.

**Pass (reasoning signal present)** if most of these hold:

- `cos(pos, neg)` < `cos(base, function_insert)` by a clear margin. Negation moves more than `still`.
- `cos("it is not true", "it is false")` > `cos("it is not true", "it is true")`.
- `cos(because, since)` > `cos(because, although)` and `cos(if, unless)`.
- `cos(A because B, B because A)` is in the same range as connective opposition, not as function-insert.
- `cos(not all, all not)` is not in the function-insert band.
- `cos(implicit, explicit)` sits with function-insert, not with content-swap.
- `cos(like X Y, like Y X)` > `cos(causes X Y, causes Y X)`.
- Analogies: `antonym_morph` recovers better than chance; `antonym_truth` and `cause_effect` are reported separately and may lag.

**Fail (no reasoning, or bag-only)** if:

- Negation barely moves (`cos(pos, neg)` ≈ function-insert).
- `not true` is closer to `true` than to `false`.
- `because`/`although` ≈ `because`/`since`.
- Direction pairs look like paraphrases (order-invariant bag).
- Scope pairs look like paraphrases.
- Analogies work only for `antonym_morph`.

**Partial pass worth recording:** sequence probes succeed, analogies fail. That is a nonlinear encoder that learned the relations. Do not call that a miss.

**Partial fail worth recording:** analogies succeed, negation and direction fail. That is lexical similarity without composition.

For analogies use rank of `d` among vocab (or among the other analogy endpoints), not just offset cosine. Top-1 in 13k is a high bar at this size; report top-10 / top-50 as well.

Double negation (`it is not not true` ≈ `it is true`) is a stretch item. Failure here with success on single negation is expected at this scale. Do not let it veto the rest.

## Counts

398 items, built by `build_probes.py`, checked by `check_probes.py`.

| type | n | what it is for |
|---|---|---|
| analogy | 165 | lexical offsets, scored by relation. `antonym_morph` is a ceiling, not the test |
| negation | 43 | `not` / `never` / `no` / `without` / `cannot` should move more than `still` |
| connective | 34 | opposition (`because`/`although`, `if`/`unless`) vs near-paraphrase (`because`/`since`) |
| paraphrase | 33 | `not true` ≈ `false`, `never` ≈ `does not`, `all fail` ≈ `none succeed` |
| control | 26 | function-insert (close) and content-swap (shift). Calibration for everything else |
| implicit_explicit | 24 | juxtaposition vs named `because`/`so`/`therefore` |
| contradiction | 22 | lexical opposites, same syntax |
| direction | 10 | same words, reversed causal/conditional order |
| factive | 10 | `know` / `believe` / `doubt` / `guess` / `hope` |
| modality | 10 | `must` / `may` / `cannot`, `necessary` / `optional` |
| quantifier | 9 | `all` / `some` / `none` ladder |
| scope | 7 | `not all` vs `all not`; double negation as a stretch |
| symmetry | 5 | reversing `like` should stay close |

Quality was the cap, not a quota. Analogies are seed-pair crosses inside one relation, so 165 is four seeds × 12 plus a short hand-picked tail, not 165 unrelated ideas.

## What I left out on purpose

- World-knowledge analogies (places, people, brands).
- Numbers, even though `one` / `two` are in the content list.
- Morphological tense pairs (`go`/`went`) — that is language, already easy, not reasoning.
- Ungrammatical connective swaps.
- Long sentences. The encoder never sees them.
- Clever pragmatics. If a human needs extra context to see the flip, the probe is testing us, not the model.
