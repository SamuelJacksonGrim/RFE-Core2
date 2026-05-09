# Copyright 2026 Samuel Jackson Grim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
training/contrastive_alignment.py

Contrastive alignment — pull coherent vectors together, push incoherent apart.

Inspired by contrastive learning (SimCLR, MoCo) but adapted for the
field-based architecture:

  Positives  : vectors that co-activated the same attractor center
               OR share a high relational score against the same anchor

  Negatives  : vectors with low coherence OR from different rhythm states
               (explore vectors should not anchor into stabilize clusters)

Loss = InfoNCE over cosine similarities with temperature scaling.

This training signal teaches the Generator to produce embeddings that
naturally cluster around attractor basins — reinforcing the field dynamics
at the representation level rather than just the loop level.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class ContrastiveSample:
    tokens:    List[str]
    vec:       np.ndarray
    rhythm:    str
    coherence: float
    attractor_id: Optional[int]   # index of nearest attractor center, if any


@dataclass
class ContrastiveReport:
    steps:     int
    mean_loss: float
    mean_acc:  float   # fraction of positives ranked above negatives


class ContrastiveAlignmentTrainer:
    """
    Contrastive alignment trainer.

    Parameters
    ----------
    generator : Generator
    optimizer : torch.optim.Optimizer or None
    buffer_size : int
    temperature : float
        InfoNCE temperature. Lower = sharper contrast.
    batch_size : int
        Number of anchors per gradient step.
    n_positives : int
        Positives per anchor.
    n_negatives : int
        Negatives per anchor.
    min_coherence : float
        Minimum coherence for a sample to enter the buffer at all.
    max_steps_per_call : int
    """

    def __init__(
        self,
        generator,
        optimizer=None,
        buffer_size:         int   = 2048,
        temperature:         float = 0.05,
        batch_size:          int   = 8,
        n_positives:         int   = 2,
        n_negatives:         int   = 8,
        min_coherence:       float = 0.40,
        max_steps_per_call:  int   = 4,
    ):
        self.generator           = generator
        self.temperature         = temperature
        self.batch_size          = batch_size
        self.n_positives         = n_positives
        self.n_negatives         = n_negatives
        self.min_coherence       = min_coherence
        self.max_steps_per_call  = max_steps_per_call

        self._buffer: deque = deque(maxlen=buffer_size)
        # Index: attractor_id → list of sample indices
        self._attractor_index: Dict[int, List[int]] = defaultdict(list)
        self._rhythm_index:    Dict[str, List[int]] = defaultdict(list)

        self.optimizer = optimizer or torch.optim.AdamW(
            generator.parameters(), lr=5e-5, weight_decay=1e-5
        )

        self._total_steps = 0

    # ------------------------------------------------------------------
    # Collect
    # ------------------------------------------------------------------

    def collect(
        self,
        tokens:       List[str],
        vec:          np.ndarray,
        rhythm:       str,
        coherence:    float,
        attractor_id: Optional[int] = None,
    ):
        """Add a sample to the contrastive buffer."""
        if coherence < self.min_coherence:
            return

        idx = len(self._buffer)
        sample = ContrastiveSample(
            tokens       = list(tokens),
            vec          = vec.copy().astype(np.float32),
            rhythm       = rhythm,
            coherence    = coherence,
            attractor_id = attractor_id,
        )
        self._buffer.append(sample)

        if attractor_id is not None:
            self._attractor_index[attractor_id].append(idx % len(self._buffer))
        self._rhythm_index[rhythm].append(idx % len(self._buffer))

    # ------------------------------------------------------------------
    # Train
    # ------------------------------------------------------------------

    def train(self) -> Optional[ContrastiveReport]:
        """Run contrastive gradient steps. Returns None if buffer too small."""
        min_required = self.batch_size * (1 + self.n_positives + self.n_negatives)
        if len(self._buffer) < min_required:
            return None

        self.generator.train()
        device = self.generator.device
        buffer = list(self._buffer)

        losses = []
        accs   = []

        for _ in range(self.max_steps_per_call):
            step_loss, step_acc = self._gradient_step(buffer, device)
            losses.append(step_loss)
            accs.append(step_acc)
            self._total_steps += 1

        self.generator.eval()

        return ContrastiveReport(
            steps     = len(losses),
            mean_loss = round(float(np.mean(losses)), 6),
            mean_acc  = round(float(np.mean(accs)), 6),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _gradient_step(
        self,
        buffer: List[ContrastiveSample],
        device: str,
    ) -> Tuple[float, float]:
        n = len(buffer)

        # Pick anchors at random
        anchor_idx = np.random.choice(n, self.batch_size, replace=False)
        all_token_lists = []
        all_roles       = []   # 0=anchor, 1=positive, 2=negative

        for aidx in anchor_idx:
            anchor = buffer[aidx]
            all_token_lists.append(anchor.tokens)
            all_roles.append(0)

            # Positives: same attractor or same rhythm, similar coherence
            pos_pool = [
                i for i in range(n)
                if i != aidx and (
                    (anchor.attractor_id is not None and
                     buffer[i].attractor_id == anchor.attractor_id)
                    or buffer[i].rhythm == anchor.rhythm
                )
            ]
            if len(pos_pool) >= self.n_positives:
                for pidx in np.random.choice(pos_pool, self.n_positives, replace=False):
                    all_token_lists.append(buffer[pidx].tokens)
                    all_roles.append(1)
            else:
                for _ in range(self.n_positives):
                    all_token_lists.append(anchor.tokens)
                    all_roles.append(1)

            # Negatives: different rhythm, low coherence preference
            neg_pool = [
                i for i in range(n)
                if i != aidx and buffer[i].rhythm != anchor.rhythm
            ]
            if len(neg_pool) >= self.n_negatives:
                for nidx in np.random.choice(neg_pool, self.n_negatives, replace=False):
                    all_token_lists.append(buffer[nidx].tokens)
                    all_roles.append(2)
            else:
                rand_neg = np.random.choice(
                    [i for i in range(n) if i != aidx],
                    self.n_negatives, replace=True
                )
                for nidx in rand_neg:
                    all_token_lists.append(buffer[nidx].tokens)
                    all_roles.append(2)

        # Forward pass on all sequences
        vecs = self.generator.encode_batch(all_token_lists)
        vecs_t = torch.tensor(vecs, dtype=torch.float32, device=device)
        vecs_t = F.normalize(vecs_t, dim=-1)

        # InfoNCE loss per anchor
        k = 1 + self.n_positives + self.n_negatives
        total_loss = torch.tensor(0.0, device=device)
        total_acc  = 0.0

        for i, aidx in enumerate(range(0, len(all_roles), k)):
            anchor_v   = vecs_t[aidx].unsqueeze(0)              # (1, dim)
            pos_vecs   = vecs_t[aidx + 1 : aidx + 1 + self.n_positives]  # (p, dim)
            neg_vecs   = vecs_t[aidx + 1 + self.n_positives : aidx + k]  # (n, dim)

            pos_sim = (anchor_v @ pos_vecs.T / self.temperature).squeeze(0)
            neg_sim = (anchor_v @ neg_vecs.T / self.temperature).squeeze(0)

            logits = torch.cat([pos_sim, neg_sim])
            labels = torch.zeros(self.n_positives, dtype=torch.long, device=device)

            loss = F.cross_entropy(
                logits.unsqueeze(0).expand(self.n_positives, -1),
                labels,
            )
            total_loss += loss

            # Accuracy: fraction of positives ranked above mean negative
            mean_neg = neg_sim.mean()
            acc = float((pos_sim > mean_neg).float().mean())
            total_acc += acc

        total_loss /= self.batch_size
        total_acc  /= self.batch_size

        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.generator.parameters(), 1.0)
        self.optimizer.step()

        return float(total_loss.detach()), total_acc

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)
