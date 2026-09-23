# Authoring brief — the witness rhythm

Architect of the rhythms: Samuel Jackson Grim. This file is the brief a parallel
author is handed. The shape to imitate is `witness.md`. The words already owned
by the five rhythms are `boundary_map.md`. The receptive anchors are
`witness_core.txt`. Nothing in this directory is merged into
`rhythm_train.jsonl` or `rhythm_holdout.jsonl` until it is graded and Samuel
signs off.

## What witness is

The five rhythms are the mind acting.

| rhythm | motion |
|---|---|
| explore | venture outward, search |
| dream | generate, imagine |
| reflect | turn inward, distill, analyze |
| stabilize | ground, hold firm |
| rupture | break, entropy, outward and kinetic |

They separate because the motions oppose. Rupture stayed separable from explore
only once its vocabulary was almost disjoint: 135 of 142 words were new, and
only 4 touched explore. Centroid cosine went to −0.096. An earlier rupture of 30
lines, 12 of them shared with explore, folded back into explore. Same label,
contradictory company, no basin.

Witness is the receptive pole. The yin against that whole active field. The mind
receiving rather than acting: attending, beholding, bearing witness, holding
space, perceiving without transforming. It touches every rhythm the way yin
touches yang. You can witness a rupture, a venture, a grief. That touch is the
trap. If the sequence encodes as its object, the vector scatters into that
object's rhythm and witness never forms a basin. **The receptive stance has to
dominate the vector, not the object.**

Reflect is the nearest neighbor. Both are inward. Reflect transforms what it
turns toward (analyze, verify, inspect, distill). Witness does not transform it.
Explore is the other failure: seek, hunt, watch-as-tracking. Witness is not
looking-for. It is letting-in.

## Files

One rhythm per file, so parallel authors do not write on top of each other.

- `stabilize.md`, `dream.md`, `reflect.md`, `explore.md`, `rupture.md` — new sequences for that rhythm only. Do not paste the live corpus into them. The live source of truth stays `data/corpus/rhythm_train.jsonl`.
- `witness.md` — the new rhythm. The gold core is already there. Add under it, or in a clearly marked batch beneath it. Do not rewrite the gold lines.
- `witness_core.txt` — the receptive anchors.
- `boundary_map.md` — per-rhythm vocabularies, the pull list, and the words that look like witness and are not available.

## Format

The human format the trainer reads back:

- A line `## <rhythm>` starts a rhythm. The name is one word: `witness`, `explore`, `dream`, `reflect`, `stabilize`, `rupture`.
- `###` headings are notes for a person. They are not rhythms. Prefer a `#` comment.
- A sequence is a line `- word, word` with 2, 3, or 4 words, comma-separated.
- Lowercase. One token per word. Letters only. No hyphens, apostrophes, digits, or punctuation inside a word. `take-in` is illegal; the token is `intake`.
- A line that does not start with `- ` is a comment and is ignored.
- Connectives (`of`, `between`, `along`, `through`, `with`, `toward`, `beneath`) are legal and almost useless here. They are the busiest tokens in the live corpus because every rhythm uses them. They will not carry a new basin. The gold core uses none.

## Rules

1. **Nine varied contexts.** A word that is supposed to mean something in this rhythm appears in at least 9 sequences here, with different neighbors each time. The same two neighbors nine times teach a phrase, not a word. The live floor is 8; author to 9.

2. **No repeated pair in your batch.** Take every unordered pair of tokens inside a sequence (`sit, dwell, abide` contains sit–dwell, sit–abide, dwell–abide). Each pair appears at most once in the file you are writing. `sit, dwell` and `dwell, sit` are the same bag. Do not write both. The live corpus's hottest pair occurs 6 times. Do not feed a pair that is already hot, and do not repeat one inside witness.

3. **Hub cap.** No word in more than about 5% of its rhythm's sequences (`count / N ≤ 0.05`). In the live corpus the busiest content word is `settle`, 60 / 1871 stabilize sequences, 3.2%. Do not race to the ceiling. On the gold file the floor (9) and the cap are close together because the file is small. That is expected. It is not a license to put `behold` in every line.

4. **Neighbor diversity.** Each new context changes the company. Cross the sub-regions below so witness is one basin, not four islands. A word whose nine neighbors are all from its own sub-region is an island.

5. **Core versus fringe, witness only.**
   - A witness sequence contains **at least two** words from `witness_core.txt`. Those are the anchor.
   - **At most one** word in the sequence is not core. That word is the fringe object, the thing beheld.
   - The object must already live in another rhythm (`boundary_map.md`). Use it once. It must not become an anchor, so it does not owe 9 contexts. Do not mint a new object word inside witness. A new token with no other home joins the witness basin, which is the scattering trap. `grief` is not in the corpus. `witness, grief` would make grief a witness word. Use an existing word (`dwell, mirror, abyss`, `attend, presence, rupture`, `behold, abide, seek`) until grief has a home of its own.
   - The object is never the only content word, and never two objects with one core. `behold, hunt, chase` fails. `behold, abide, seek` holds.
   - New words you add to witness are core, or they are not added. A new core word is receptive, absent from the boundary map, and cleared to 9 contexts under the hub cap. Add it to `witness_core.txt` in the same batch. Do not add a stabilize synonym (`rest`, `calm`, `silence`, `anchor`, `ground`, `stillness`, `shelter`), an explore verb, a dream verb, a rupture verb, or a reflect verb.

6. **Do not keep reflect's company.** The pulled words (below) currently sit next to analyze, verify, validate, inspect, examine, deliberate, reconcile, measure, synthesize, locate, situate, assess, process, reason, weigh, confirm, evaluate. That company is reflect. `notice, analyze` is a reflect sequence with a witness word in it. It will fold. The denylist is absolute for witness lines: do not use those verbs at all, not even as the one fringe object.

7. **Pull list.** These words are leaving reflect and becoming witness core. Legal in witness, only in receptive company: `attend`, `perceive`, `notice`, `observe`, `sit`, `sense`, `register`, `mirror`, `meditate`, `contemplate`, `witness`. `witness` also has a stabilize life (identity, pause, record). Same rule. Do not author new reflect lines that put these words back.

8. **Not anchors, even though they feel like witness.**
   - `watch` — reflect and explore. Explore uses it as tracking. Do not anchor it.
   - `hold` — stabilize's hold-firm (crystallize, anchor, wholeness). "Hold space" is `presence, space` here, not `hold`.
   - `self` — stabilize and reflect, identity. Not the meditative stance.
   - `attention`, `quiet`, `silence`, `stillness`, `pause`, `rest`, `calm`, `see`, `look`, `glimpse`, `open` — already placed. See the boundary map.

9. **Level, not deep.** Vary the length (2 and 3, sometimes 4). Vary which word is first. No template frame (`the X of Y` repeated with a slot filled). No hub. The prize property of the first corpus was that the space stayed level.

10. **Do not edit** `data/corpus/rhythm_train.jsonl` or `rhythm_holdout.jsonl`. Do not train the live checkpoint. Do not touch the running mind or resonance memory.

## Sub-regions of the gold core

One basin, four rooms. Cross the rooms.

- **Inward-meditative.** sit, dwell, abide, vigil, linger, attune, hush, sojourn, await, patience, unsought, unmoved, meditate, contemplate, ken.
- **Outward-bearing.** behold, bear, regard, testify, attest, gaze, witness, marvel, overhear.
- **Perceptual-sensing.** receive, listen, hearken, heed, intake, reception, receptive, perceive, notice, observe, sense, register, awareness.
- **Relational-attending.** presence, space, accompany, welcome, allow, accept, company, beside, present, humble, attend, mirror, awe.

## What good looks like

- `sit, dwell, abide` — three core, inward, no object.
- `bear, witness` — the idiom, both core.
- `presence, space` — holding space without the stabilize word `hold`.
- `behold, abide, seek` — two core, one explore object. The venture is beheld. Seek does not anchor.
- `attend, presence, rupture` — two core, the rupture token as object.
- `dwell, mirror, abyss` — two core, a rupture-signature object.
- `notice, hush, interior` — two core, a reflect content-word as object, not a reflect verb.

## What fails

- `notice, analyze, inspect` — reflect, wearing a stolen word.
- `behold, hunt, chase` — one core, two explore verbs. The object took the line.
- `witness, grief` — one core, and grief has no other home.
- `watch, pressure` — that line is already explore.
- nine copies of `behold, presence`.
- a new word used three times and abandoned under the floor.

## Extending the gold file

The gold file is 184 sequences. Every core word is in 9 of them, which is 4.9%. The floor and the cap are almost the same number because the rhythm is still small. One more use of any anchor, in a file this size, puts that word over 5% (10/185 = 5.4%). Do not add a tenth context for a gold anchor until the file is long enough that the new count still fits: `count / N ≤ 0.05`. At count 10 that means N ≥ 200.

To grow witness:

- Add a **new receptive word**, absent from the boundary map. Give it 9 contexts.
- Pair it with **other new words** first. A line of two new words does not touch a gold anchor.
- If you pair it with a gold anchor, use a different anchor each time, and only inside a batch large enough that those anchors stay under 5%. Sixteen new lines is the smallest batch in which a gold anchor can go from 9 to 10 and still pass (10/200 = 5%). One extra line on today's file does not.
- A fringe object, if you use one, is still one per sequence, still a word that already has a home, still not on the denylist.
- Do not repeat a pair the gold file already used.

## Lint

From the repo root:

```
python tools/voice/lint_corpus_authoring.py data/corpus/authoring/witness.md
```

The lint is the mechanical gate: format, two-core minimum, one-object maximum, floor, hub cap, repeated pairs, bags that clone the live corpus, denylist, and core words that still belong to another rhythm and are not on the pull list. A file can pass the lint and still be a template mill. Read the lines. The lint does not grade voice.

## Separability, so you know what the grade is

After a real pretrain, witness intra-cosine should be high and the witness centroid near-orthogonal to explore, reflect, dream, stabilize, and rupture. The rupture bar is centroid cosine near 0 or below. Folding into reflect, or into explore, means the core was not distinct enough. Quality of stance over quantity of lines.
