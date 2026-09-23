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
