"""
cognition/dream_channel.py — the system's own decoded thoughts re-entering as a voice.

Rung 2 of the North Star (self ↔ self dialogue). The Decoder reads the cycle's last
expressed vector into tokens; the DreamChannel hands those tokens back to a driver,
which feeds them as a normal cycle step with `source_id="source_dream"`. The dream
therefore re-enters **through `arbitrate()`**, exactly like any external source — the
trust ledger, dependency monitor (HHI), manipulation resistance, and sacred-shield
treat it the same. There is no bypass: the system can hear itself, but its own voice
gets no special authority.

Safety model (why this can't quietly become an echo chamber):
  - **One voice among many.** The dream is fed at a *weight* (like the other source
    weights), not every step; the external sources still dominate the mix.
  - **Governed.** If the dream starts flattering the field (low-novelty coherence
    flood) or a single dreamed token-set dominates, the existing immune system reacts
    (HHI / manipulation resistance / trust). The probe measures exactly this.
  - **Terminal read, governed write.** The DreamChannel only *reads* the expressed
    vector (observe-only) and proposes tokens; the *write* is an ordinary governed
    `cycle.step`. Disposition stays with governance.

This module decides *what* the system would say back to itself; *whether/when* to feed
it is the driver's policy (so the cognitive step is never self-modified in place).
"""
from __future__ import annotations

import random
from typing import List, Optional


class DreamChannel:
    """Decode the cycle's last expressed vector into a short dream utterance.

    Parameters
    ----------
    decoder : TokenDecoder
        Trained against the running engine's frozen generator.
    top_k : int
        Candidate tokens read from the expressed vector.
    n_tokens : int
        Length of the dream utterance (kept in the corpus's 2-4 range so the dream
        looks like any other source's input).
    sample : bool
        If True, sample n_tokens from the top_k by probability (a little stochasticity
        to resist fixed-point echoes); if False, take the top n_tokens deterministically.
    """

    SOURCE_ID = "source_dream"

    def __init__(self, decoder, top_k: int = 6, n_tokens: int = 3,
                 sample: bool = True, seed: int = 1188):
        self.decoder = decoder
        self.top_k = top_k
        self.n_tokens = n_tokens
        self.sample = sample
        self._rng = random.Random(seed)

    def dream_tokens(self, cycle) -> Optional[List[str]]:
        """Read `cycle._last_expressed` → a short list of tokens, or None if there is
        nothing to dream yet (e.g. before the first step)."""
        vec = getattr(cycle, "_last_expressed", None)
        if vec is None:
            return None
        cand = self.decoder.decode(vec, top_k=self.top_k)  # [(token, prob), ...]
        if not cand:
            return None
        toks, probs = [c[0] for c in cand], [max(c[1], 1e-6) for c in cand]
        n = min(self.n_tokens, len(toks))
        if self.sample:
            # weighted sample without replacement
            chosen, pool_t, pool_p = [], list(toks), list(probs)
            for _ in range(n):
                i = self._rng.choices(range(len(pool_t)), weights=pool_p)[0]
                chosen.append(pool_t.pop(i)); pool_p.pop(i)
            return chosen
        return toks[:n]
