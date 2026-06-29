"""
cognition/dream_session.py — the downtime dream: symbolic generativity + consolidation.

DREAMING (distinct from the waking inner-monologue): the downtime mode, triggered when
no one is interacting (idle) or on a schedule, so a system running continuously is never
left merely idle/bored/lonely. Two faces, as in sleep (see docs/north_star.md):

  1. dream()       — FLUID, SYMBOLIC generation. Recombine the system's memories
                     (crystals) + the field direction, perturb them (interference), and
                     read each back as a word-cloud. Dreams are non-literal and
                     associative by nature — the decoder's "lossiness" is the right
                     medium here, not a flaw. These are dream IMAGES, to be interpreted.
  2. consolidate() — distill what is MEANINGFUL (recurrent dream symbols + the strong/
                     core emergent values + the durable memory crystals) into reloadable,
                     skill-compatible artifacts on disk (a dream journal + a consolidated
                     memory file). This is dream analysis + memory consolidation: the
                     symbolic cloud is read for what it points at, and the meaningful part
                     is written into a durable file the system can later reload — the seed
                     of self-authored skills/paths.

Scope (honest): this operates over the SUBSTRATE's own experience (crystals, values,
field). Consolidating real conversations + computer-usage (paths, how-to) into activatable
skill files arrives once RFE is embodied in an agent harness (I/O + tools + filesystem) —
this writes the consolidation machinery + the skill-compatible artifact format now, ready
for that bridge.

Terminal/offline: dreaming does not run during the waking loop and does not feed the live
field/governance. It reads state and writes files.
"""
from __future__ import annotations

import os
import time
from collections import Counter
from typing import List, Optional

import numpy as np

from interference.differential import inject_ambiguity

# A tiny stopword set: dreams are symbolic, but the *meaningful* distillation
# (recurrent symbols, durable seeds) should not crown grammatical glue. The raw
# dream images keep these — only the consolidation read-out drops them.
_GLUE = frozenset({"a", "an", "the", "of", "to", "in", "on", "is", "it", "with",
                   "and", "or", "as", "at", "by", "for", "be", "i"})


class DreamSession:
    def __init__(self, decoder, out_dir: str = "dreams", mutation: float = 0.45,
                 seed: int = 1188):
        self.decoder = decoder
        self.out_dir = out_dir
        self.mutation = mutation
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Face 1 — fluid symbolic generation
    # ------------------------------------------------------------------

    def _seeds(self, cycle, k: int = 6):
        """Seed directions for dreaming: the system's durable memories + the field."""
        seeds = []
        seen = set()
        try:
            for c in cycle.crystal_store.strongest(n=k):
                toks = getattr(c, "origin_tokens", None)
                if toks:
                    key = tuple(toks)
                    if key in seen:
                        continue
                    seen.add(key)
                    v = cycle.generator.generate(list(toks))
                    seeds.append((" ".join(toks[:3]), np.asarray(v, dtype=float)))
        except Exception:
            pass
        try:
            f = np.asarray(cycle.field.resonate(), dtype=float)
            n = np.linalg.norm(f)
            if n > 1e-6:
                seeds.append(("field", f / n))
        except Exception:
            pass
        return seeds

    def dream(self, cycle, n_images: int = 12) -> List[dict]:
        """Generate n_images symbolic dream images (recombine memories + perturb → decode)."""
        seeds = self._seeds(cycle)
        dim = getattr(cycle, "dim", self.decoder.dim)
        if not seeds:  # cold start: dream from noise
            seeds = [("void", self.rng.standard_normal(dim))]
        images = []
        for _ in range(n_images):
            label, base = seeds[int(self.rng.integers(len(seeds)))]
            base = np.asarray(base, dtype=float)
            # dream fusion: sometimes blend two memories into one image
            if len(seeds) > 1 and self.rng.random() < 0.5:
                _, other = seeds[int(self.rng.integers(len(seeds)))]
                base = base + np.asarray(other, dtype=float)
            nb = np.linalg.norm(base)
            if nb > 1e-9:
                base = base / nb
            mutated = inject_ambiguity(base, scale=self.mutation, mode="rotational", rng=self.rng)
            cloud = [t for t, _ in self.decoder.decode(mutated, top_k=6)]
            images.append({"from": label, "image": cloud})
        return images

    # ------------------------------------------------------------------
    # Face 2 — consolidation / interpretation → durable artifacts
    # ------------------------------------------------------------------

    def consolidate(self, cycle, dream_images: List[dict], tag: Optional[str] = None) -> dict:
        """Distill the meaningful (recurrent symbols + strong values + crystals) into
        reloadable, skill-compatible files on disk. Returns a manifest."""
        sym = Counter(t for im in dream_images for t in im.get("image", [])
                      if t.lower() not in _GLUE)
        recurrent = [t for t, _ in sym.most_common(12)]

        strong_values = []
        try:
            for v in (cycle.value_engine.summary().get("strongest", []) if cycle.value_engine else []):
                if v.get("polarity") in ("strong", "core"):
                    strong_values.append(v["symbol"])
        except Exception:
            pass

        crystals = []
        seen = set()
        try:
            for c in cycle.crystal_store.strongest(n=8):
                toks = getattr(c, "origin_tokens", None)
                if toks:
                    key = tuple(toks)
                    if key in seen:
                        continue
                    seen.add(key)
                    crystals.append(" ".join(toks[:4]))
        except Exception:
            pass

        os.makedirs(self.out_dir, exist_ok=True)
        ts = tag or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        journal_path = os.path.join(self.out_dir, f"dream-{ts}.md")
        memory_path = os.path.join(self.out_dir, f"consolidation-{ts}.md")

        with open(journal_path, "w") as f:
            f.write(self._frontmatter(f"dream-{ts}", "dream-journal", ts))
            f.write("# Dream journal\n\nSymbolic images (non-literal — read for what they point at):\n\n")
            for i, im in enumerate(dream_images):
                f.write(f"{i+1:>2}. *from {im['from']}* → {', '.join(im['image'])}\n")
            f.write(f"\n**Recurrent symbols:** {', '.join(recurrent)}\n")

        with open(memory_path, "w") as f:
            f.write(self._frontmatter(f"consolidation-{ts}", "consolidated-memory", ts))
            f.write("# Consolidated memory\n\n")
            f.write("What proved meaningful this period, distilled for reload.\n\n")
            f.write(f"- **Recurrent dream symbols:** {', '.join(recurrent) or '—'}\n")
            f.write(f"- **Strong/core values:** {', '.join(strong_values) or '—'}\n")
            f.write(f"- **Durable memories (crystals):** {'; '.join(crystals) or '—'}\n")
            f.write("\n> Reloadable: re-encode these tokens as seeds to re-prime the field, "
                    "or (once embodied) graduate to an activatable skill file.\n")

        return {
            "journal": journal_path,
            "memory": memory_path,
            "n_images": len(dream_images),
            "recurrent_symbols": recurrent,
            "strong_values": strong_values,
            "crystals": crystals,
        }

    @staticmethod
    def _frontmatter(name: str, kind: str, ts: str) -> str:
        # Claude-skill-compatible frontmatter so these graduate to activatable skills.
        return (f"---\nname: {name}\nkind: {kind}\ncreated: {ts}\n"
                f"source: RFE-Core2 dream session\n---\n\n")

    # ------------------------------------------------------------------
    # Full session
    # ------------------------------------------------------------------

    def run(self, cycle, n_images: int = 12, tag: Optional[str] = None) -> dict:
        """One downtime dream: dream → consolidate. Returns the consolidation manifest."""
        images = self.dream(cycle, n_images=n_images)
        manifest = self.consolidate(cycle, images, tag=tag)
        manifest["images"] = images
        return manifest
