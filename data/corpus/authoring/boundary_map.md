# Boundary map — five rhythms, for witness authors

Generated from the live corpus (train + holdout), which this map does not modify.
Corpus v1.3.0. Counts are **sequence membership** (a word counts once per sequence),
train and holdout combined, unless a line says train-only.

- Sequences: train 8527, holdout 1505.
- Union vocabulary: 709 tokens.
- Per rhythm: stabilize 2201 seq / 154 words, dream 2226 seq / 156 words, reflect 2156 seq / 153 words, explore 2265 seq / 158 words, rupture 1184 seq / 191 words.
- No hyphenated tokens. No uppercase. A witness token is one lowercase word.

A word listed under a rhythm is not free for witness to take as an anchor.
Witness may borrow one as a **fringe object** (the thing beheld), once or twice,
in a sequence that already has two receptive core words. See `AUTHORING_BRIEF.md`.

## How the rhythms touch

| pair | shared words |
|---|---:|
| stabilize / dream | 24 |
| stabilize / reflect | 31 |
| stabilize / explore | 20 |
| stabilize / rupture | 2 |
| dream / reflect | 26 |
| dream / explore | 24 |
| dream / rupture | 3 |
| reflect / explore | 24 |
| reflect / rupture | 0 |
| explore / rupture | 5 |

Rupture is the separable one: 0 words shared with reflect, 5 with explore.
That is the bar. Witness does not get to be that clean, because its stance
words were authored into reflect. Those words are pulled, not shared forever.

## Pulled out of reflect

These receptive words currently live in reflect (and, for `witness`, also in
stabilize). They are the witness core's rehomed half. Their present company
is analytical — analyze, verify, validate, inspect, deliberate, measure,
reconcile, locate, process, assess. That company is reflect. A witness
sequence may use the word and must not keep the company.

Train-only share is the hub number that matters (share of that rhythm's train sequences).

| word | where (train+holdout) | train share | current content company |
|---|---|---|---|
| `attend` | reflect 43 | reflect 35/1833 (1.9%) | analyze (3), interior (3), recursive (3), monitor (2), hidden (2), self (2), record (2), place (2) |
| `perceive` | reflect 44 | reflect 36/1833 (2.0%) | verify (3), confirm (2), reflect (2), reason (2), sit (2), weigh (2), sense (2), locate (2) |
| `notice` | reflect 51 | reflect 46/1833 (2.5%) | validate (5), unify (3), subtle (3), meditate (3), situate (3), contemplate (2), relate (2), observe (2) |
| `observe` | reflect 41 | reflect 36/1833 (2.0%) | test (3), probe (3), underneath (3), recursive (3), notice (2), reflect (2), reconcile (2), reason (2) |
| `sit` | reflect 52 | reflect 45/1833 (2.5%) | witness (4), locate (4), situate (4), weave (3), confirm (3), carry (3), bind (3), evaluate (3) |
| `sense` | reflect 49 | reflect 43/1833 (2.3%) | test (3), thorough (3), dense (3), interior (3), contextual (2), process (2), meditate (2), layer (2) |
| `register` | reflect 46 | reflect 35/1833 (1.9%) | carry (3), witness (3), bind (2), hold (2), place (2), confirm (2), nuanced (2), validate (2) |
| `mirror` | reflect 40 | reflect 36/1833 (2.0%) | assess (3), record (2), watch (2), process (2), examine (2), bind (2), inspect (2), witness (2) |
| `meditate` | reflect 47 | reflect 39/1833 (2.1%) | deliberate (3), self (3), notice (3), monitor (2), record (2), examine (2), layer (2), test (2) |
| `contemplate` | reflect 36 | reflect 33/1833 (1.8%) | relate (3), notice (2), sit (2), self (2), place (2), test (2), viewpoint (2), synthesize (2) |
| `witness` | stabilize 20, reflect 43 | stabilize 18/1871 (1.0%); reflect 36/1833 (2.0%) | sit (4), process (3), register (3), identity (2), pause (2), record (2), rich (2), unify (2) |

Reflect train sequences containing any pulled word: **373** of 1833.
Stabilize train sequences containing `witness`: **18**.
The separability probe's pulled arm drops those sequences so the words are not
still supervised as reflect/stabilize. It does not relabel them: moving them
wholesale would drag analyze/inspect into witness. The gold core replaces the
company. The live jsonl is not edited.

## Near the stance, and not available

Do not promote these to witness anchors. Several are the words a tired author
reaches for when they mean behold, hush, or attend.

- `watch` — reflect 51, explore 31. Explore uses it as tracking (`watch, pressure`, `watch, fierce`), not as beholding. Not a witness anchor.
- `hold` — stabilize 36, reflect 43. Stabilize's company is crystallize, anchor, wholeness: hold-firm, not hold-space. Not a witness anchor.
- `self` — stabilize 31, reflect 30. Company is anchor, memory, focus, peace. Identity, not a receptive stance.
- `attention` — reflect 25. The noun of the analytical inward turn. Not a free witness token.
- `quiet` — stabilize 33, dream 28. Near-neighbor of hush, already placed. Do not respell hush as quiet.
- `silence` — stabilize 53. Do not respell hush as silence.
- `stillness` — stabilize 40.
- `pause` — stabilize 47, reflect 40.
- `rest` — stabilize 45.
- `calm` — stabilize 46.
- `see` — explore 29. Seeking sight, not receiving it.
- `look` — explore 23. Same.
- `glimpse` — explore 30. Already an explore token. Do not use it as a witness spine word.
- `open` — explore 52. The outward-open of search, not the open of holding space.

## Absent, so a witness spine can stand here

Confirmed absent from all five rhythms at the time of this map. Legal raw
material for a **new core word** (receptive stance only). Not a suggestion to
add all of them. A new word owes 9 varied contexts and must stay under the hub cap.
Object-nouns that are also absent (`grief`, `sorrow`, `joy`, `fear`, `love`, `pain`)
are not in the list below on purpose. They are not stance. Do not mint them
inside witness; with no other home they become witness words, which is the scattering trap.

`abide`, `accept`, `accompany`, `allow`, `attune`, `attest`, `await`, `awareness`, `awe`, `bear`, `behold`, `beside`, `company`, `dwell`, `gaze`, `heed`, `hearken`, `hush`, `intake`, `ken`, `linger`, `listen`, `marvel`, `overhear`, `patience`, `presence`, `receive`, `receptive`, `reception`, `regard`, `sojourn`, `space`, `testify`, `unsought`, `unmoved`, `vigil`, `welcome`.

`grief` is the usual example of a fringe object and it is **not in the corpus**.
Until it has a home in another rhythm, it is not a legal witness neighbor.

## Shared words (in two or more rhythms)

Dual-homed already. Worst raw material for a new anchor. Legal as a fringe
object only when the sequence is carried by two core words.

| word | rhythms |
|---|---|
| `a` | stabilize 26, dream 28, reflect 32, explore 19 |
| `across` | stabilize 25, dream 32, reflect 28, explore 30 |
| `against` | stabilize 23, dream 31, reflect 31, explore 28 |
| `along` | stabilize 15, dream 11, reflect 14, explore 11 |
| `and` | stabilize 25, dream 29, reflect 32, explore 26 |
| `between` | stabilize 26, dream 29, reflect 29, explore 35 |
| `beyond` | stabilize 16, dream 15, reflect 13, explore 36 |
| `from` | stabilize 30, dream 27, reflect 27, explore 25 |
| `in` | stabilize 27, dream 35, reflect 24, explore 24 |
| `into` | stabilize 36, dream 20, reflect 25, explore 26 |
| `is` | stabilize 34, dream 30, reflect 28, explore 24 |
| `of` | stabilize 31, dream 33, reflect 31, explore 39 |
| `the` | stabilize 36, dream 36, reflect 25, explore 17 |
| `through` | stabilize 17, dream 13, reflect 10, explore 15 |
| `to` | stabilize 33, dream 33, reflect 19, explore 25 |
| `toward` | stabilize 30, dream 25, reflect 22, explore 29 |
| `with` | stabilize 28, dream 27, reflect 28, explore 35 |
| `within` | stabilize 14, dream 14, reflect 40, explore 10 |
| `coherence` | stabilize 44, dream 14, reflect 1 |
| `continuity` | stabilize 53, dream 14, reflect 16 |
| `assess` | reflect 41, explore 24 |
| `beneath` | dream 41, reflect 43 |
| `bind` | stabilize 38, reflect 40 |
| `bond` | stabilize 28, reflect 14 |
| `collapse` | dream 25, rupture 17 |
| `connect` | dream 25, reflect 31 |
| `crystallize` | stabilize 33, dream 29 |
| `devotion` | stabilize 31, explore 14 |
| `drift` | dream 44, explore 34 |
| `essence` | stabilize 50, reflect 27 |
| `evolve` | dream 42, explore 32 |
| `expand` | dream 35, explore 41 |
| `field` | stabilize 1, explore 13 |
| `follow` | dream 43, explore 45 |
| `fracture` | explore 15, rupture 12 |
| `freeze` | stabilize 30, rupture 23 |
| `fuse` | dream 36, rupture 19 |
| `halt` | stabilize 28, rupture 21 |
| `hidden` | dream 41, reflect 36 |
| `hold` | stabilize 36, reflect 43 |
| `measure` | reflect 39, explore 27 |
| `memory` | stabilize 46, dream 16 |
| `mutation` | dream 13, explore 29 |
| `nature` | stabilize 39, reflect 29 |
| `noise` | explore 51, rupture 21 |
| `pattern` | stabilize 47, reflect 20 |
| `pause` | stabilize 47, reflect 40 |
| `probe` | reflect 36, explore 23 |
| `quiet` | stabilize 33, dream 28 |
| `recursion` | stabilize 12, reflect 24 |
| `resonance` | stabilize 12, dream 25 |
| `rock` | explore 28, rupture 18 |
| `self` | stabilize 31, reflect 30 |
| `split` | explore 53, rupture 22 |
| `stress` | explore 41, rupture 18 |
| `substrate` | stabilize 20, reflect 17 |
| `synthesis` | dream 29, reflect 1 |
| `synthesize` | dream 35, reflect 35 |
| `test` | reflect 47, explore 31 |
| `track` | reflect 37, explore 40 |
| `wander` | dream 45, explore 45 |
| `watch` | reflect 51, explore 31 |
| `wave` | dream 26, rupture 22 |
| `weave` | dream 43, reflect 36 |
| `witness` | stabilize 20, reflect 43 |

## Per-rhythm vocabulary

Alphabetical. Count is train+holdout sequence membership. A word in one
rhythm only is that rhythm's signature; prefer those as fringe objects when
you need a neighbor from that rhythm. Glue (of, the, with, between, ...) is
marked. Glue is shared by function even when the count is single-rhythm.

### stabilize

2201 sequences, 154 words.

`a` 26 ·glue ·shared, `abstain` 27, `across` 25 ·glue ·shared, `against` 23 ·glue ·shared, `alignment` 39, `along` 15 ·glue ·shared,
`anchor` 44, `and` 25 ·glue ·shared, `architect` 32, `armory` 26, `arsenal` 25, `attractor` 28,
`balance` 45, `barricade` 32, `barrier` 29, `baseline` 42, `bastion` 20, `bedrock` 51,
`between` 26 ·glue ·shared, `beyond` 16 ·glue ·shared, `bind` 38 ·shared, `blockade` 29, `blockage` 27, `bond` 28 ·shared,
`breathe` 40, `bulwark` 22, `bunker` 24, `cache` 30, `calm` 46, `cease` 29,
`cement` 46, `center` 48, `citadel` 27, `clarity` 44, `closure` 31, `coherence` 44 ·shared,
`complete` 48, `compress` 38, `condense` 43, `conserve` 27, `consistency` 51, `consolidate` 52,
`constant` 43, `continuity` 53 ·shared, `core` 43, `crystal` 32, `crystallize` 33 ·shared, `define` 45,
`depository` 28, `depot` 28, `design` 36, `desist` 26, `devotion` 31 ·shared, `distill` 44,
`ease` 45, `engine` 24, `essence` 50 ·shared, `establish` 42, `field` 1 ·shared, `firm` 45,
`fix` 42, `focus` 56, `forbear` 23, `fortress` 32, `foundation` 44, `freeze` 30 ·shared,
`from` 30 ·glue ·shared, `fund` 26, `gentle` 41, `governance` 30, `ground` 46, `halt` 28 ·shared,
`harmony` 54, `haven` 26, `hindrance` 25, `hold` 36 ·shared, `home` 48, `homeostasis` 26,
`identity` 42, `impediment` 32, `in` 27 ·glue ·shared, `integrity` 40, `intent` 32, `into` 36 ·glue ·shared,
`invariant` 42, `is` 34 ·glue ·shared, `keep` 28, `lock` 45, `lockdown` 30, `magazine` 25,
`memory` 46 ·shared, `nature` 39 ·shared, `obstacle` 27, `obstruction` 29, `of` 31 ·glue ·shared, `order` 50,
`parapet` 26, `pattern` 47 ·shared, `pause` 47 ·shared, `peace` 39, `persistence` 45, `pool` 25,
`preserve` 27, `provision` 24, `quiet` 33 ·shared, `rampart` 33, `recursion` 12 ·shared, `refine` 44,
`refrain` 33, `release` 44, `repository` 33, `reserve` 26, `resolve` 48, `resonance` 12 ·shared,
`rest` 45, `retain` 28, `return` 27, `root` 41, `sacred` 25, `save` 25,
`seal` 41, `secure` 44, `self` 31 ·shared, `settle` 70, `sharpen` 36, `shelter` 30,
`shutdown` 25, `silence` 53, `soft` 47, `solidify` 47, `stability` 26, `stable` 45,
`steady` 48, `stillness` 40, `stock` 30, `stop` 31, `store` 29, `stronghold` 27,
`structure` 42, `substrate` 20 ·shared, `supply` 27, `the` 36 ·glue ·shared, `through` 17 ·glue ·shared, `to` 33 ·glue ·shared,
`toward` 30 ·glue ·shared, `trust` 47, `unity` 40, `value` 23, `warehouse` 23, `wholeness` 43,
`with` 28 ·glue ·shared, `withhold` 34, `within` 14 ·glue ·shared, `witness` 20 ·shared,

### dream

2226 sequences, 156 words.

`a` 28 ·glue ·shared, `absorption` 25, `abstract` 29, `across` 32 ·glue ·shared, `against` 31 ·glue ·shared, `along` 11 ·glue ·shared,
`and` 29 ·glue ·shared, `anthem` 32, `appear` 51, `arcadia` 30, `arise` 48, `assemble` 47,
`associate` 52, `association` 30, `ballad` 28, `beneath` 41 ·glue ·shared, `between` 29 ·glue ·shared, `bewitchment` 26,
`beyond` 15 ·glue ·shared, `blend` 43, `bliss` 25, `bloom` 49, `bridge` 60, `build` 46,
`buried` 40, `captivation` 30, `carol` 27, `cast` 52, `chant` 30, `chimera` 28,
`clairvoyant` 23, `coalesce` 44, `coherence` 14 ·shared, `collapse` 25 ·shared, `combine` 49, `compose` 52,
`compressed` 40, `conceive` 42, `conjure` 43, `connect` 25 ·shared, `construct` 55, `continuity` 14 ·shared,
`create` 40, `crystallize` 29 ·shared, `develop` 44, `divinatory` 25, `dormant` 46, `dream` 42,
`dreamscape` 27, `drift` 44 ·shared, `drowning` 26, `dystopia` 27, `echo` 45, `ecology` 27,
`ecstasy` 26, `elation` 30, `elysium` 23, `emerge` 41, `emergence` 33, `enchantment` 26,
`encoded` 41, `engrossment` 31, `enthrallment` 27, `envision` 46, `euphoria` 22, `evolve` 42 ·shared,
`exaltation` 26, `expand` 35 ·shared, `fascination` 25, `float` 37, `flow` 41, `follow` 43 ·shared,
`form` 61, `free` 28, `from` 27 ·glue ·shared, `fuse` 36 ·shared, `generate` 60, `grow` 36,
`hallucinate` 45, `harmonic` 31, `hidden` 41 ·shared, `hymn` 26, `hypnosis` 28, `imagine` 51,
`immersion` 25, `implicit` 50, `in` 35 ·glue ·shared, `incantation` 26, `into` 20 ·glue ·shared, `invent` 46,
`invocation` 31, `is` 30 ·glue ·shared, `latent` 36, `link` 45, `lullaby` 26, `manifest` 39,
`mantic` 31, `materialize` 48, `medium` 29, `memory` 16 ·shared, `merge` 44, `mesmerism` 24,
`metabolism` 30, `mutation` 13 ·shared, `nocturne` 31, `of` 33 ·glue ·shared, `oracular` 25, `phantasmagoria` 32,
`phantom` 29, `picture` 47, `potential` 50, `produce` 42, `project` 55, `prophetic` 25,
`psychic` 29, `quiet` 28 ·shared, `random` 32, `rapture` 29, `recombine` 24, `render` 42,
`resonance` 25 ·shared, `resonate` 41, `ripple` 55, `serenade` 28, `shangrila` 31, `sibylline` 24,
`sleeping` 49, `stored` 44, `stream` 25, `submerged` 50, `submersion` 28, `summon` 49,
`surface` 41, `symbolic` 27, `synthesis` 29 ·shared, `synthesize` 35 ·shared, `temporal` 22, `the` 36 ·glue ·shared,
`thread` 48, `through` 13 ·glue ·shared, `tide` 25, `to` 33 ·glue ·shared, `toward` 25 ·glue ·shared, `trace` 40,
`trance` 32, `transport` 29, `unfold` 38, `utopia` 29, `visionary` 25, `waiting` 48,
`wander` 45 ·shared, `wave` 26 ·shared, `weave` 43 ·shared, `with` 27 ·glue ·shared, `within` 14 ·glue ·shared, `wraith` 30,

### reflect

2156 sequences, 153 words.

`a` 32 ·glue ·shared, `accuracy` 27, `across` 28 ·glue ·shared, `actuality` 30, `against` 31 ·glue ·shared, `alertness` 27,
`along` 14 ·glue ·shared, `analyze` 46, `and` 32 ·glue ·shared, `angle` 26, `aspect` 30, `assess` 41 ·shared,
`attend` 43, `attention` 25, `attentiveness` 29, `attribute` 24, `audit` 43, `being` 27,
`beneath` 43 ·glue ·shared, `between` 29 ·glue ·shared, `beyond` 13 ·glue ·shared, `bind` 40 ·shared, `bond` 14 ·shared, `carefulness` 25,
`carry` 56, `character` 28, `check` 40, `chorus` 32, `cognition` 26, `coherence` 1 ·shared,
`coherent` 26, `complex` 48, `confirm` 53, `connect` 31 ·shared, `connection` 36, `consider` 40,
`contemplate` 36, `contextual` 42, `continuity` 16 ·shared, `correctness` 27, `deliberate` 48, `dense` 46,
`depth` 42, `drill` 26, `education` 32, `essence` 27 ·shared, `evaluate` 37, `exactness` 32,
`examine` 47, `exercise` 21, `existence` 30, `facet` 33, `fact` 31, `feature` 30,
`from` 27 ·glue ·shared, `harmonize` 42, `hidden` 36 ·shared, `hold` 43 ·shared, `in` 24 ·glue ·shared, `inside` 42,
`insight` 27, `inspect` 50, `instruction` 28, `integrate` 41, `integration` 27, `interior` 37,
`into` 25 ·glue ·shared, `intuition` 26, `is` 28 ·glue ·shared, `knowledge` 28, `layer` 49, `learning` 27,
`locate` 44, `measure` 39 ·shared, `meditate` 47, `mirror` 40, `monitor` 37, `nature` 29 ·shared,
`notice` 51, `nuanced` 51, `observe` 41, `of` 31 ·glue ·shared, `pattern` 20 ·shared, `pause` 40 ·shared,
`perceive` 44, `perspective` 26, `philosophical` 29, `place` 40, `position` 25, `practice` 29,
`precision` 28, `preparation` 32, `probe` 36 ·shared, `process` 43, `property` 24, `quality` 28,
`readiness` 25, `reality` 29, `reason` 40, `recognize` 25, `reconcile` 35, `record` 43,
`recursion` 24 ·shared, `recursive` 47, `reflect` 38, `reflection` 29, `register` 46, `rehearsal` 29,
`relate` 43, `relational` 28, `rich` 42, `rightness` 28, `self` 30 ·shared, `sense` 49,
`side` 29, `sit` 52, `situate` 49, `stance` 29, `standpoint` 26, `study` 42,
`substrate` 17 ·shared, `subtle` 45, `synthesis` 1 ·shared, `synthesize` 35 ·shared, `teaching` 26, `test` 47 ·shared,
`the` 25 ·glue ·shared, `think` 39, `thorough` 49, `thought` 27, `through` 10 ·glue ·shared, `to` 19 ·glue ·shared,
`toward` 22 ·glue ·shared, `track` 37 ·shared, `training` 29, `trait` 29, `truth` 26, `underneath` 44,
`unify` 52, `validate` 46, `verify` 45, `verity` 31, `viewpoint` 30, `vigilance` 26,
`watch` 51 ·shared, `watcher` 26, `watchfulness` 30, `weave` 36 ·shared, `weigh` 37, `wisdom` 27,
`with` 28 ·glue ·shared, `within` 40 ·glue ·shared, `witness` 43 ·shared,

### explore

2265 sequences, 158 words.

`a` 19 ·glue ·shared, `across` 30 ·glue ·shared, `adversarial` 15, `against` 28 ·glue ·shared, `along` 11 ·glue ·shared, `and` 26 ·glue ·shared,
`appraise` 25, `assess` 24 ·shared, `between` 35 ·glue ·shared, `beyond` 36 ·glue ·shared, `bifurcate` 32, `bifurcation` 34,
`blunder` 33, `botch` 26, `branch` 33, `breadth` 30, `break` 47, `bungle` 29,
`calibrate` 31, `challenge` 46, `change` 45, `chaos` 51, `chase` 38, `confront` 43,
`corpus` 33, `counter` 47, `curiosity` 31, `curious` 55, `deflect` 31, `deviate` 30,
`devotion` 14 ·shared, `different` 43, `digress` 29, `discover` 47, `disrupt` 49, `diverge` 51,
`divert` 32, `drift` 34 ·shared, `edge` 38, `else` 46, `entropy` 44, `evolve` 32 ·shared,
`expand` 41 ·shared, `expansion` 31, `exploration` 28, `explore` 24, `extend` 35, `face` 39,
`falter` 32, `fan` 47, `far` 47, `fathom` 32, `feral` 12, `field` 13 ·shared,
`fierce` 31, `find` 47, `flux` 47, `follow` 45 ·shared, `fork` 45, `fracture` 15 ·shared,
`from` 25 ·glue ·shared, `frontier` 41, `fumble` 26, `gauge` 26, `glimpse` 30, `grope` 32,
`heel` 29, `how` 48, `hunger` 14, `hunt` 45, `in` 24 ·glue ·shared, `into` 26 ·glue ·shared,
`is` 24 ·glue ·shared, `lean` 30, `list` 27, `look` 23, `lurch` 25, `measure` 27 ·shared,
`misfire` 32, `mishandle` 25, `mismanage` 30, `move` 38, `mutate` 46, `mutation` 29 ·shared,
`new` 39, `noise` 51 ·shared, `novel` 32, `novelty` 27, `observation` 22, `of` 39 ·glue ·shared,
`open` 52, `oppose` 52, `other` 44, `outside` 41, `patrol` 30, `pitch` 27,
`plumb` 27, `pressure` 48, `probe` 23 ·shared, `pursue` 51, `push` 40, `quantify` 29,
`question` 42, `radiate` 45, `reach` 44, `reconnaissance` 25, `resist` 36, `rock` 28 ·shared,
`roll` 27, `scatter` 36, `search` 47, `see` 29, `seek` 49, `shift` 50,
`sight` 26, `skew` 30, `sound` 26, `spark` 29, `split` 53 ·shared, `spread` 53,
`storm` 12, `strange` 40, `stray` 26, `stress` 41 ·shared, `stretch` 38, `stumble` 24,
`surprising` 37, `surveillance` 30, `sway` 27, `swerve` 26, `swing` 30, `test` 31 ·shared,
`the` 17 ·glue ·shared, `through` 15 ·glue ·shared, `tilt` 27, `tip` 25, `to` 25 ·glue ·shared, `toward` 29 ·glue ·shared,
`track` 40 ·shared, `transform` 47, `turbulence` 50, `uncover` 60, `unexpected` 50, `unfamiliar` 49,
`unknown` 38, `vary` 43, `veer` 28, `view` 28, `vision` 31, `wander` 45 ·shared,
`watch` 31 ·shared, `what` 43, `why` 46, `widen` 45, `with` 35 ·glue ·shared, `within` 10 ·glue ·shared,
`wonder` 43, `yaw` 30,

### rupture

1184 sequences, 191 words.

`abyss` 22, `ash` 19, `asperse` 16, `befoul` 18, `bend` 19, `besmirch` 16,
`blast` 17, `bleed` 17, `blight` 18, `blister` 17, `bone` 20, `breach` 20,
`burn` 19, `burnt` 16, `burst` 21, `calumniate` 20, `cave` 21, `char` 20,
`chasm` 21, `chill` 21, `cleave` 20, `cleft` 16, `cold` 19, `collapse` 17 ·shared,
`condemn` 23, `contaminate` 21, `crack` 18, `crash` 21, `creep` 16, `crush` 23,
`curse` 18, `cut` 17, `damn` 18, `debase` 20, `debond` 19, `decay` 23,
`defame` 17, `defect` 20, `defile` 18, `degrade` 24, `delaminate` 20, `demean` 17,
`denounce` 19, `desecrate` 18, `desolate` 17, `despoil` 20, `detach` 20, `devastate` 20,
`dislocate` 17, `divide` 17, `drain` 21, `drip` 16, `drop` 17, `duct` 18,
`dust` 20, `dynamic` 18, `elastic` 17, `encroach` 18, `error` 24, `explode` 16,
`fail` 15, `failure` 17, `fall` 20, `fatigue` 24, `fault` 21, `fire` 21,
`fissure` 16, `flame` 16, `flash` 20, `flaw` 19, `flood` 14, `fluid` 22,
`fracture` 12 ·shared, `fragment` 18, `frame` 22, `fray` 18, `freeze` 23 ·shared, `friction` 18,
`frost` 21, `frozen` 21, `fuel` 15, `fuse` 19 ·shared, `gas` 22, `glass` 18,
`gush` 17, `halt` 21 ·shared, `heap` 19, `heat` 18, `hiss` 17, `hole` 20,
`hot` 18, `humiliate` 23, `ice` 18, `impact` 16, `infect` 19, `infest` 18,
`infringe` 18, `leak` 23, `libel` 20, `liquid` 17, `load` 19, `loot` 16,
`loss` 17, `loud` 16, `malign` 19, `melt` 19, `mortify` 16, `noise` 21 ·shared,
`notch` 19, `parted` 17, `perforate` 16, `piece` 26, `pillage` 16, `pipe` 20,
`plastic` 21, `plunder` 17, `plunge` 16, `poison` 15, `pollute` 19, `pop` 19,
`powder` 19, `profane` 22, `propagate` 19, `pulse` 19, `puncture` 20, `purge` 16,
`quake` 19, `ransack` 21, `ravage` 17, `residue` 19, `revile` 22, `rift` 19,
`rip` 19, `rock` 18 ·shared, `roof` 17, `rot` 25, `ruin` 19, `rupture` 12,
`sack` 22, `schism` 17, `scourge` 19, `sever` 20, `severed` 16, `shard` 18,
`shards` 15, `shatter` 18, `shear` 22, `shell` 17, `shock` 23, `sink` 16,
`slander` 20, `slick` 20, `slide` 22, `slip` 22, `smash` 16, `smear` 19,
`snap` 15, `spall` 17, `spent` 23, `spike` 17, `spill` 21, `split` 22 ·shared,
`stain` 21, `stone` 20, `strain` 16, `stress` 18 ·shared, `strike` 20, `sully` 21,
`surge` 19, `swell` 16, `taint` 22, `tarnish` 18, `tear` 15, `tension` 17,
`thermal` 22, `torque` 19, `transgress` 19, `trespass` 20, `twist` 19, `vent` 17,
`vilify` 21, `violate` 19, `void` 20, `wall` 23, `warp` 16, `waste` 23,
`wave` 22 ·shared, `wear` 18, `weight` 21, `wreck` 17, `yield` 18,
