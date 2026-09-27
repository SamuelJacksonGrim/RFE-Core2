# Notes for the gate — does the receptive basin form?

Seed 0. Fresh generator, the live architecture (vocab 8192, dim 128, depth 4,
heads 4), CPU, no checkpoint written. Supervised contrastive pretraining, the
same objective as `training/rhythm_pretraining.py`. 40 epochs at batch 256.
Batch 8 would almost never hold two witness lines inside the 8527-line train,
so witness would have had no positive pair and a "fold" would have been
starvation. Batch 256 is about 32× fewer steps per epoch; 40 epochs puts the
step budget near the live boot (8 epochs at batch 8). Loss had flattened by
epoch 30. This is not an under-trained blur.

The live `rhythm_train.jsonl` and `rhythm_holdout.jsonl` were not modified.
The field and resonance memory were not booted.

Gold file: `witness.md`, 184 sequences, 50 core words, each in 9 sequences
(4.9%). 36 fringe objects, each once, each already living in another rhythm.
Lint passes.

## Verdict

The receptive basin forms. It does not fold into reflect, **if the pull
happens**. It does not yet clear the rupture bar against the whole active
field. Rupture's bar, in this same run, is visible: explore⊥rupture centroid
cosine is **−0.171**. The probe can see orthogonality. Witness does not land
there against rupture or explore.

Two arms. **Additive** keeps the live train and adds the gold, so the eleven
pulled words are still labeled reflect (and `witness` is still labeled
stabilize). **Pulled** drops the 373 reflect-train sequences that contain a
pulled word, and the 18 stabilize-train sequences that contain `witness`,
then adds the gold. The old lines are not relabeled. Relabeling them would
drag analyze and inspect into witness.

| | additive | pulled |
|---|---:|---:|
| witness intra-cosine (mean pairwise) | 0.984 | 0.990 |
| witness nearest-centroid accuracy | 0.989 | 1.000 |
| sequences off the witness centroid | 2 | 0 |
| centroid vs stabilize | 0.105 | 0.310 |
| centroid vs dream | 0.272 | 0.195 |
| centroid vs reflect | **0.497** | **0.104** |
| centroid vs explore | **0.542** | 0.373 |
| centroid vs rupture | 0.388 | **0.471** |

Intra-cosine is high in both arms. That is a tight cone, the same regime as
the frozen five (within-rhythm cosine 0.92–0.98). It is not, by itself,
separability. Separability is the angle.

Read it this way:

- Without the pull, witness is a class the nearest-centroid rule can name
  (0.989) and a cone tilted into explore (0.54) and reflect (0.50). Those two
  angles are worse than any pair among the existing five in that same run.
  The worst pair among the five there is reflect–stabilize at 0.47.
  Explore⊥stabilize is −0.07 and explore⊥reflect is −0.30. Witness did not
  join that opposition. It leaned into the two rhythms the brief named.
- With the pull, witness⊥reflect goes to **0.104**. That is the rupture bar's
  neighborhood (the first separable rupture⊥explore was 0.179, later −0.096).
  Reflect stops being the neighbor. Dream is 0.195. The cone is still tilted
  toward rupture (0.471) and explore (0.373). Classifier-clean, not orthogonal
  to the active field.

So: the basin is real, the pull is load-bearing, and the gold core is not yet
as separable from rupture and explore as rupture is from explore. Do not merge
on the additive geometry. The pull is part of the design, not an optional
cleanup.

## What fought

**The pull list, as tokens, when left in reflect.** In the additive arm the
single-token encoding of these eleven words has its nearest centroid in
reflect, at cosine 0.96–0.995:

`witness`, `mirror`, `sit`, `sense`, `attend`, `contemplate`, `register`,
`meditate`, `perceive`, `observe`, `notice`.

Their reflect lives are the majority of their sequences (about 35–46 reflect
train lines each, against 9 witness lines). The embedding stays where the
count is. Sequence-level, the spine words in the same line usually still drag
the mean-pool onto the witness centroid. The two lines that lost were made of
the pull list and nothing else:

- `observe, attend` — nearest centroid reflect (cos 0.987), witness only 0.589
- `perceive, notice, observe` — nearest centroid reflect (cos 0.979), witness 0.622

Both are marked in `witness.md`. Do not imitate them. A pull-list word needs a
spine word in the line (`hush`, `behold`, `abide`, `presence`, …). After the
pull, every one of the 50 core words, as a single token, has its nearest
centroid in witness. The token moves when the contradictory label is removed.
It does not move while the label stays.

**Explore, on the outward-bearing words, even after the pull.** Single-token
cosine to explore, pulled arm, nearest centroid still witness:

| word | cos witness | cos explore |
|---|---:|---:|
| present | 0.939 | 0.644 |
| gaze | 0.946 | 0.638 |
| awareness | 0.950 | 0.631 |
| testify | 0.949 | 0.629 |
| behold | 0.971 | 0.567 |
| marvel | 0.973 | 0.559 |
| linger | 0.975 | 0.556 |

They did not cross the boundary. They are the outward face of the cone, and
they are why explore stays at 0.373 after the pull. `abide`, `accept`,
`welcome`, `overhear`, `regard`, `await`, `dwell` were the sequence-level
explore lean in the additive arm (margin still positive, nearest centroid
still witness). The brief's warning was right: outward-attending is the
explore trap, and it is not only `watch`. `watch` was kept out of the core.
The words that remain risky are the ones that mean looking.

**Rupture is the residual neighbor after the pull, and it is not one word.**
Word margins in the pulled arm all point at rupture, from perceive (+0.40)
down through the list, and every one of those sequences still classifies as
witness. Eight fringe lines carry a rupture-signature object (`fatigue`,
`shear`, `crush`, `rot`, `decay`, `abyss`, `shock`, `rupture`). That is not
enough mass to move a 184-line centroid to 0.47 by itself. The tilt is
global. I would not blame a single spine word for it. I would stop adding
rupture objects, and I would not add kinetic vocabulary to the spine.
`unsought` and `unmoved` were meant to negate that pole; they did not push
the centroid off it.

`hold`, `watch`, and `self` were not used as anchors. The boundary map was
right to hold them back. `hold` is stabilize's crystallize/anchor word.
Putting it in the core to spell "hold space" would have been a second
contradictory label. The idiom in the gold file is `presence, space`.

## Did core-versus-fringe hold?

Yes, at the sequence level. No missed sequence is a fringe line. The object
did not become the anchor. The 36 objects appear once each and already belong
to another rhythm. `grief` was not minted. A new object token would have had
no other home and would have joined the witness cone. That rule is the one
to enforce on the swarm hardest, because the floor of 9 will otherwise force
them to turn a one-off object into an anchor.

The rule's failure mode is not the object. It is a line whose every word is
from the pull list. Two of those are in the gold file, marked, and they are
the only additive misses. Everything else stayed on the witness centroid.

## How big the rhythm can get

Not a peer of reflect or explore yet. Those rhythms are ~1900 train sequences.
Witness at 184 already has a cone, and the cone is already tilted toward
rupture and explore. More outward-bearing words will feed the explore tilt.
More rupture objects will feed the rupture tilt. The reflect separation is
the part that worked, and it depends on the pull staying done.

I would let the swarm add receptive spine words that are absent from the
boundary map, paired with each other, and I would re-measure before the file
passes about **400–600 sequences**. Rupture's size (~1200 sequences, ~190
words, and explore⊥rupture at −0.17 in this run) is the existence proof that
a sixth-scale rhythm can be orthogonal. Witness has not earned that scale.
The constraint is the angle, not the hub cap.

The hub arithmetic is in the brief. Every gold anchor is at 9/184 = 4.9%.
A tenth use does not fit until the file is at least 200 lines, and a serious
batch of new lines should be new words paired with new words. Pairing every
new context with `behold` or `attend` will make a hub and will also thicken
whichever tilt that anchor carries. `behold` is one of the explore-leaning
tokens.

## What I would tighten before a merge

1. Do the pull in the corpus that actually trains. Not as a relabel of the
   old reflect lines. Those lines keep analyze, verify, inspect. Drop or
   rewrite them so the pulled word is gone from reflect and from stabilize's
   `witness` lines. Until that edit, the eleven tokens are reflect tokens.
2. Do not write pull-list-only lines. The two marked lines are the demonstration.
3. Keep the outward set (`gaze`, `behold`, `testify`, `present`, `awareness`,
   `marvel`) on a short leash. They are in the cone. They are also the explore lean.
4. Do not add rupture-signature words except as the single fringe object, and
   do not add more of those either until the 0.47 has moved.
5. Re-run this probe on the swarm's batch before anything is merged. The gate
   is witness⊥reflect staying near the pulled number (0.10, not back to 0.50)
   and witness⊥explore / witness⊥rupture not climbing. Intra-cosine will look
   fine either way. Do not grade on intra-cosine alone.

Numbers and per-word margins: `witness_separability.json`.
Probe: `tools/voice/probe_witness_basin.py`.
Lint: `tools/voice/lint_corpus_authoring.py`.

## Pull executed, and the spine grown (lane witness/lane-a)

The live `rhythm_train.jsonl` and `rhythm_holdout.jsonl` were not modified.
Nothing here was trained. Lint on `witness.md` passes: 485 sequences.

### What moved

The pull is a drop, not a relabel. Pasting the 373 into witness would carry
analyze, inspect, record, and the rest of reflect's company, clone live bags,
and break the hub cap (those eleven words already have about 35–46 reflect-train
contexts each; 5% of a 485-line file is 24). The gold core is the replacement
company. The line list is the `DROP` lines in `reflect.md`.

| | count | digest (sha256/16 of sorted bags) |
|---|---:|---|
| reflect train, any pulled word | 373 | `cd693fa3aeeae9b4` |
| stabilize train, `witness` | 18 | `8295cef1ddc33338` |
| holdout reflect, any pulled word | 62 | not dropped |
| holdout stabilize, `witness` | 2 | not dropped |

Of the 373: 209 are one pulled word and no analytic verb, 83 are a pulled word
plus an analytic verb plus other reflect company, 51 are a pulled word plus
analytic verbs only, 22 are two or more pulled words with at most one other
non-analytic token, and 8 are two or more pulled words with more than one
other non-analytic token. Stripping the pulled word leaves a legal 2–4 token
line for 168 of them, a single token for 194, and nothing for 11. Those 168
were not re-authored into `reflect.md`. In a file that size `within` is already
11/138, over the hub cap, and the residue is still reflect. Reflect's analytic
spine stays where it is: the 1460 reflect-train sequences (1833 − 373) that
never used a pulled word. Distill, synthesize, reconcile, measure, analyze are
untouched.

The 18 stabilize lines are almost all `witness` plus one hold-firm token
(`identity`, `bunker`, `shelter`, …). Dropping the line removes the
contradictory `witness` label. It does not become a witness sequence.
`identity, continuity, witness` is the one line that would still have two
tokens; it stays stabilize's identity line, not witness.

The 43 lines that already contain two or more pulled words were not copied
either. Fourteen of them clone a live bag once reduced to the pulled words,
and a pull-list-only line is the shape the additive probe sent to reflect
(`observe, attend`, `perceive, notice, observe`). Those two gold lines stay,
marked. They were not imitated.

Holdout still carries the words (62 + 2). The probe trains on train only, so
those lines do not supervise the fit. A merge that trains on holdout too
should drop them as well. They are listed under `HOLDOUT` in `reflect.md` and
were not part of the signed-off 373 + 18.

`reflect.md` has no `- ` sequences. A dash line would train the old company as
reflect, which is the tangle.

### Generator

`tools/voice/gen_witness.py`, seed 1188, stdlib only. Rerun is byte-stable.

| | |
|---|---|
| gold sequences | 184, unchanged |
| generated | 301 (168 twos, 112 threes, 21 fours) |
| witness total | 485 |
| new spine words | 84, each in 9 contexts |
| gold anchors | still 9 each, including the seven explore-leaning words |
| hottest share | 9/485 = 1.856% |
| dedup rejects | 0 |

Dedup is on the unordered bag. The design emits each bag once, and the reverse
of a line is the same bag, so it cannot be written again. Gold had no duplicate
bags. This batch does not add to the 161 order-swapped pairs in the live corpus.
No generated token is in the live vocabulary, so none of the new bags clone a
live line. Eleven of the 112 threes are single-room; every new word also has
cross-room neighbors (the fours take one word from each room), and no word's
neighbors are all from its own room.

### Words added

Eighty-four, absent from the boundary map, paired only with each other. No
fringe object in the batch.

- Inward-abiding: repose, tarry, bide, indwell, inhere, unhurried, unbidden, unasked, wakeful, mindful, abidance, inwardness, equanimity, immanence, letting, wakefulness, mindfulness, kneel, exhale, numinous, uncalled.
- Receiving-allowing: imbibe, embrace, enfold, cradle, permit, assent, acquiesce, accede, soften, unclench, relent, allowance, sufferance, tolerance, receptivity, hospitality, indrawn, pardon, brook, receptiveness, vouchsafe.
- Perceptual-sensing, receiving rather than looking: savor, murmur, whisper, audible, palpable, sensation, hearing, feel, taste, smell, hear, touch, feeling, sentience, sensory, sensate, percipience, attunement, sonority, scent, inhale.
- Relational-warmth: tenderness, cherish, grace, mercy, kindness, kinship, kindred, reverence, revere, compassion, empathy, nearness, closeness, togetherness, dearness, fondness, caring, amity, fellowship, companionship, affection.

`brook` is the archaic verb, to allow, in the company of stance words rather than water. `scent` is the receiving verb, not an object-noun of the grief kind. `pardon` is in the allowing room. An earlier draft used `ingest`; that is consumption, not reception, and it is not in the file.

### Words avoided

Not given any new context, left at their gold 9: `present`, `gaze`, `awareness`, `testify`, `behold`, `marvel`, `linger`.

Not used at all in the batch: the reflect operation (`analyze`, `inspect`, `examine`, `deliberate`, `reconcile`, `validate`, `verify`, `measure`, `synthesize`, `distill`, and the rest of the denylist), the banned near-stance words (`watch`, `hold`, `self`, `attention`, `quiet`, `silence`, `stillness`, `pause`, `rest`, `calm`, `see`, `look`, `glimpse`, `open`), and the object-nouns with no other home (`grief`, `sorrow`, `joy`, `fear`, `love`, `pain`).

Also left out, on purpose: looking verbs that happen to be absent (`peer`, `stare`, `scan`, `survey`, `espy`, `descry`), analytic-inward verbs (`ponder`, `muse`, `ruminate`, `introspect`), the stabilize quiet-cluster (`quietude`, `serenity`, `composure`, `comfort`, `soothe`, `solace`, `gentleness`, `breath`, `poise`), and gerunds of words the gold file already has (`beholding`, `gazing`, `observing`, `listening`, `abiding`). No rupture-signature object was added. The eight fringe rupture objects in the gold file were not repeated.

### Will the angle hold at 485

I did not run the probe. This is the read for the gate.

It should hold against explore and against rupture **if the drop is applied at merge**, and it will not hold against reflect if the drop is skipped.

The new 301 lines are 62% of the file and share no token with the five rhythms. They cannot import analyze. They dilute the outward face: those seven words go from 9/184 (4.9%) to 9/485 (1.9%) without gaining a context. Nothing looking was added, and nothing kinetic. That is the explore lean and the rupture-object path, not fed. The rupture tilt in the pulled arm was global, not one spine word, so I would not promise witness⊥rupture falls to the rupture-bar. I would expect it not to climb, because the added mass is inward, allowing, and warm rather than outward or broken.

The risk that is new, not the one the probe already measured, is stabilize. Tenderness, cherish, grace, mercy, kindness, embrace, soften are warmth. Stabilize sat at 0.310 after the pull, middle of the pack, not the failure. They are accompaniment, not hold-firm: no anchor, ground, calm, rest, silence. Worth reading off the probe. Not a reason to have used the outward set instead.

`hear`, `feel`, `touch`, `taste`, `smell`, `scent` are the widest words in the batch. They are receiving, not `look` / `see` / `glimpse` / `watch`. They should not rebuild the gaze lean. They are the words I would check first if witness⊥explore moves the wrong way.

Witness⊥reflect stays a property of the drop. The eleven pulled tokens still have their reflect majority in the live train until those 373 lines are removed. The new 84 words have no reflect life, so they should sit in witness even in an additive fit. The old gold, which is 184/485 of the file, still contains the pull-list lines that folded when the label was left on. Do not read an additive run of this file as the pull having failed. Do not merge without the drop.

485 is inside the 400–600 ceiling. I would not add another batch until this one has been probed. Intra-cosine will look fine either way. The gate is still witness⊥reflect near the pulled 0.10, and witness⊥explore / witness⊥rupture not climbing. Stabilize is the extra number to look at.
