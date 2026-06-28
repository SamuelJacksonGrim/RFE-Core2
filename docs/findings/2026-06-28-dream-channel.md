# Governed self-dialogue (dream channel) — does the system's own voice help, or echo?

- **Date:** 2026-06-28
- **Substrate:** live (pretrained engine, dim 128, corpus v1.1.0, CPU); 2 seeds × 400 steps, p_dream=0.2
- **Probe:** `tests/diagnostic/dream_channel_probe.py` + `cognition/dream_channel.py` + `agents/decoder.py`
- **Status:** active — **validated safe + adds voice diversity; graduation to default pending an adversarial arm**
- **Depends on:** 2026-06-28-decoder-readout, 2026-06-28-full-system-run

## Question

North-Star rung 2 (self ↔ self dialogue): the Decoder reads the cycle's last expressed
vector into tokens, which re-enter as `source_dream` — one ~p_dream-weighted voice
among many, **through `arbitrate()`** (no bypass). Does hearing itself add genuine
otherness (perturbation that loosens lock-in), or does it become an echo chamber /
dominate / get rejected?

## Pre-declared signatures

- SAFE + VALUABLE: source_dream stays non-dominant (HHI low, not mass-quarantined);
  coherence does not run away upward; voice diversity ≥ dream_off.
- ECHO CHAMBER: coherence climbs toward 1.0; voice diversity collapses; source_dream
  dominates HHI.
- INERT/REJECTED: governance quarantines/floods source_dream → channel adds nothing.

## Result (observed) — dream_off vs dream_on, two seeds

| Metric | seed 42 off→on | seed 7 off→on |
|--------|----------------|---------------|
| Voice diversity (unique/total) | 0.090 → **0.1125** | 0.0775 → **0.0875** |
| HHI (dependency concentration) | 0.293 → **0.230** | 0.303 → **0.234** |
| `source_dream` decisions | allow 76 / weakened 1 / **quarantine 0** | allow 88 / weakened 1 / **quarantine 0** |
| Coherence drift (early→late) | +0.032 → +0.009 | +0.008 → +0.013 |
| Metastability (stage C) | 0.60 → 0.57 | (~same) |

The locked refrain shifts: dream_off top voice "self within into pause bind hold" →
dream_on "crystallize into self quiet through within".

## Interpretation

- **The SAFE + VALUABLE signature is met, both seeds.** Governed self-dialogue
  **increases the diversity of the system's voice** (+25% / +13% unique phrases) — real
  otherness — while staying a **non-dominant** voice (HHI *drops*) that is **cleanly
  governed** (allow-dominant, zero quarantine). All three failure modes (echo,
  dominance, rejection) stayed clear. The first rung of the self↔self loop works and is
  safe under the existing immune system, with no bypass.
- **Honest caveat:** the "reduces locking" hint is *not* robust — coherence drift went
  down on seed 42 but up on seed 7, both within noise (<0.015). So dreaming **diversifies
  expression without echoing, but does not by itself break the absolute lock.** Correct
  for its role: this is dialogue (rung 2), not a lock fix.

## Threats / confounds

- Runs: 2 seeds, 400 steps, **benign load only** — no adversary. The key open test is
  whether `source_dream` opens an attack surface or how it behaves *under* attack
  (does an attacker's content, re-dreamed, get laundered? does the dream help or hurt
  resistance?). This is the graduation gate.
- Single p_dream (0.2); diversity gain is modest though consistent. Decoder is
  bag-of-words (no order), so "voice" is a token cloud, not sentences (see decoder
  finding). Gauge magnitudes v0.1-fragile — trust the arm gap.

## Open / next

- **Adversarial arm** (graduation gate): run with a hostile source present; confirm the
  dream channel doesn't launder attacks and resistance holds.
- Sweep `p_dream`; more seeds.
- On passing the gate: wire into `loop/recursion1188.py` as a graduated default (not a
  dormant flag — graduate-or-remove), source_dream as a weighted voice.
- Then the same governed channel carries **external** dialogue (architect ↔ system,
  system ↔ other AI): decoded output to a reader, their reply re-entering as a source.
  Communication and self-modification ride this one gated mechanism (North Star).
