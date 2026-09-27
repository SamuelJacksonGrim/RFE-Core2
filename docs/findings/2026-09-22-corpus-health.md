# Corpus health — the levelness gate for growth

- **Date:** 2026-09-22
- **Branch:** `experiment/legibility-fit`
- **Corpus:** v1.3.0. Train 8527, holdout 1505, vocab 709. 239 of those tokens have no row in the frozen ecology. 4507 / 8527 train sequences are clean (every token already has a row). The other half carries an orphan and sits outside the cones.
- **Code:** `tools/voice/corpus_health.py`. Numbers in `2026-09-22-corpus-health-metrics.json`.
- **Status:** measured. The thresholds below are a proposal. Samuel rules.

The property being protected is the one from the first corpus: the space stays level. No redundant phrasing, no deep basin, no hub, spread kept. The field lock is not a lever here and was not touched. The gate reference is the **frozen** 5-rhythm checkpoint. The legible checkpoint is a second column, because a fit is allowed to move and the admission rule has to have a fixed ruler.

"Clean" below means the 4507 sequences whose tokens are in the frozen ecology. That is the cone. Full-train numbers mix in the orphan half and are in the json under the same keys without `clean`.

## 1. Redundancy — what not to add more of

Ordered duplicates inside train: **0**. That is the existing integrity check, and it passes.

Exact bags, ignoring order: **161 groups, 322 sequences**. Every group is a pair. They are the same two tokens swapped (`sleeping hidden` / `hidden sleeping`). There is no fuzzy band under that: the fraction of sequences whose within-rhythm nearest neighbor has Jaccard ≥ 0.80 is 0.0368, and the fraction whose neighbor has Jaccard = 1 is also 0.0368. p90 of that nearest-neighbor Jaccard is 0.67. p50 is 0.33.

Rupture has none of these pairs (max within-rhythm Jaccard 0.67). The other four rhythms each have a 3–5% permutation rate.

Cross-rhythm exact clones: **4 pairs**, all closed-class.

| bag | rhythms |
|---|---|
| a, memory | dream / stabilize |
| and, coherence | dream / stabilize |
| in, nature | reflect / stabilize |
| between, track | explore / reflect |

Repeated phrasing is not the problem. The hottest unordered pair in the whole train is `conjure` + `crystallize`, **6 times**, all in dream. The hottest ordered bigram is `soft bedrock`, 4 times. Nothing is a template.

Holdout is not clean of this either. 57 / 1505 holdout sequences have a train neighbor at Jaccard 1. The ordered-tuple leakage check does not see an order swap. That is a mild stain on Gate G1, not something this pass edited.

The 5 canonical seeds: 19 / 25 are in train under their rhythm. Missing: reflect `analyze pattern recognize`, and all five rupture seeds (`fracture spall delaminate`, `fatigue creep yield`, `fissure crack rift`, `sever cleave split`, `collapse rupture burst`). The rupture words are in the vocab. Those five lines are not.

## 2. Hubs — counts, then the table

Context counts on train: min 10, median 26, max **114**. The floor of 8 holds (0 tokens under it). max/median is 4.4.

The max is not a content word. The busiest twelve are `of` 114, `against` 101, `the` 100, `between` 100, `with` 99, `across` 98, `is` 95, `and` 95, `to` 94, `a` 93, `toward` 92, `into` 92. Closed-class glue, spread across rhythms.

Inside one rhythm the busiest content token is `settle` in stabilize: 60 / 1871 = **3.2%**. Then `generate` in dream 2.9%, `carry` in reflect 2.7%, `uncover` in explore 2.7%. No token is a cone.

On the embedding table (709 corpus rows, frozen): max nearest-neighbor indegree is **7** (`shift`, `rest`, `homeostasis`, `center`), and the neighbors that point at them sit at cosine ~0.45–0.54. Median indegree is 1. That is not a magnet. The legible table's max is 8 (`drip`), neighbors at cosine ~0.55. Same fact.

Sequence nearest-neighbor indegree, clean cloud: max **5** frozen and **5** legible. Mean is 1, because each point has one neighbor. The top 1% of points collect under 4% of the arrows. Nobody is a hub.

## 3. Levelness — the sheet, and what the fit did to it

Participation ratio and effective rank are of the centered cloud. A single direction scores 1. Five tight cones score near 4. Depth gap is p95 − p50 of cosine-to-own-centroid: a flat sheet scores ~0, a few points sunk into a hole scores large.

Clean train, frozen vs legible:

| | frozen | legible |
|---|---:|---:|
| participation ratio | 3.26 | 10.11 |
| effective rank | 3.70 | 13.77 |
| within cosine, five rhythms | 0.92–0.98 | 0.42–0.60 |
| centroid-cosine p50 | 0.997 | 0.763 |
| depth gap (p95 − p50) | **0.002** | **0.116** |
| 8-neighbor cosine, p50 | 0.9999 | 0.982 |
| density entropy (normalized) | 0.003 | 0.027 |
| nearest neighbor at cosine ≥ 0.95 who shares Jaccard < 0.50 | 97.7% | 91.8% |
| same, but the neighbor shares Jaccard ≥ 0.80 | 0.6% | 2.1% |
| sequence-hub max indegree | 5 | 5 |
| token-hub max indegree | 7 | 8 |

Per rhythm, clean within cosine and within-cone participation ratio:

| rhythm | frozen within | legible within | frozen PR | legible PR | legible 8-NN p50 |
|---|---:|---:|---:|---:|---:|
| stabilize | 0.950 | 0.591 | 2.25 | 5.93 | 0.983 |
| dream | 0.943 | 0.596 | 3.54 | 5.38 | 0.985 |
| reflect | 0.917 | 0.578 | 2.08 | 4.79 | 0.986 |
| explore | 0.937 | 0.589 | 2.49 | 6.56 | 0.982 |
| rupture | 0.980 | 0.422 | 1.51 | 7.17 | 0.947 |

The frozen cone is level in the sense that was prized. It is a sheet. Depth gap 0.002 means there is no deeper hole inside the hole. Rupture is the tightest sheet (within 0.98, PR 1.5) and the most even. Hubs are absent. The low effective rank is the sheet: five directions, not a failed corpus.

The legible fit did **not** dig a hub and did **not** spend the spread. Effective rank went 3.7 → 13.8. Sequence-hub indegree did not rise. Token-hub indegree went 7 → 8.

What it cost is the flatness. The sheet is now a shell about 0.12 thick. That is the same opening the mouth was bought with (clean within 0.96 → 0.58). It is not a new abyss: p95 of centroid cosine is 0.879 against a median of 0.763, not a spike at 0.99 with a halo at 0.4. Rupture's shell is the thickest (gap 0.129) and the only neighborhood that actually loosened (8-neighbor cosine 0.95; the other four are still ≥ 0.98).

The local neighborhood did not become a token code. 92% of clean points still have a nearest neighbor at cosine ≥ 0.95 who shares less than half their bag. That is why the 30-epoch fit raised holdout recall@8 from 0.355 to 0.417 and left within-cone neighbor Jaccard at 0.10. The Jaccard term is an average over random pairs inside a 32-wide batch, so it moves the bulk of the cone (mean within-cosine 0.95 → 0.58) and barely moves whoever ends up nearest (8-neighbor cosine 1.00 → 0.98). It does not single out that neighbor.

So: still level as a landscape of hubs, more spread than the frozen sheet, less flat, and still locally collapsed. The number to watch on the next fit is the depth gap, not the mean within-cosine. Mean within-cosine falling is the mouth. Depth gap rising past the shell, or neighbor cosine staying at 0.98 while a few points pull away, is a basin.

## 4. The proposal

Not a law. Three stages. `corpus_health.py --batch some.jsonl` scores A and B against the absolute block in the metrics json.

**A. Before any training. A batch is refused if any of these fail.**

| check | cap | why this number |
|---|---|---|
| exact token sequence already in train | 0 | existing integrity rule |
| exact bag already in train, order ignored | 0 | the 161 swapped pairs are a debt, not a budget. The measured 3.7% is not a license to add another 3.7% |
| Jaccard ≥ 0.80 against a different rhythm | 0 | the 4 closed-class clones are the whole of this failure today |
| new token's contexts in train+batch | ≥ 8 | existing floor |
| any token's context count | ≤ 114 | held by `of`. This is what stops more glue |
| any token's share of one rhythm | ≤ 0.0321 | held by `settle`. This is the cone hub cap |
| any unordered pair's count | ≤ 6 | held by `conjure`+`crystallize` |

**B. Encode train+batch with the frozen checkpoint. Clean sequences only** (a new word's sequences are not in that slice; they are gated by the floor and by token-hub indegree after registration).

| check | cap |
|---|---|
| participation ratio | ≥ 3.1955 |
| effective rank | ≥ 3.6283 |
| depth gap | ≤ 0.022 |
| sequence-hub max indegree | ≤ 6 |
| token-hub max indegree | ≤ 7 |

Nearest-neighbor cosine and density entropy are **not** in this gate. On the frozen encoder they are a spike at cosine 1 and an entropy of ~0. "Do not get tighter than 1" cannot fail. Using them as an admission rule would be a dead gauge.

**C. After a growth fit, against the legible clean column.** This is where a neighborhood can retighten, so neighbor cosine becomes a real check. In the json as `post_fit_watch`.

| check | cap |
|---|---|
| participation ratio | ≥ 9.9099 |
| effective rank | ≥ 13.4931 |
| depth gap | ≤ 0.1363 |
| 8-neighbor cosine, p50 | ≤ 0.9923 |
| sequence-hub max indegree | ≤ 6 |
| token-hub max indegree | ≤ 8 |
| unjustified-collapse rate | ≤ 0.9181 |

C is not required to admit the text. It is the check that training on the admitted text did not dig the hole A and B cannot see.

## Notes for the gate

- The corpus is already the level thing, with two debts: order-swapped bags, and a closed-class tail (`of`/`the`/`and`) that is how the four cross-rhythm clones happen. Growth that adds more glue will hit the context cap immediately. That is intentional.
- Do not gate on "keep within-cosine at 0.96." That freezes the cone collapse. Gate on depth gap, hub indegree, and participation ratio.
- The legible space is not less level as a hub story. It is less flat. Local neighbors did not open. If the next corpus is grown to buy coherence, the fit that follows has to be checked on neighbor cosine and neighbor Jaccard, not only on recall.
- Half the train sequences contain an orphan token. Any growth pass that "fills the 239" is changing half the cloud's membership in the clean slice. Run this script before and after, on the same mask, or the participation-ratio delta is not a delta.
- Nothing here steps the field or writes either checkpoint.
