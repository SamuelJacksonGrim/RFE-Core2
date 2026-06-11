"""
training/self_distillation.py

Online self-distillation — the system learns from its own high-coherence outputs.

Rather than requiring labeled external data, the system uses its own
crystal-bound and attractor-aligned vectors as soft training targets.
High-coherence outputs become teachers; lower-coherence outputs become students.

This creates a self-improving loop:
  1. Autonomous cycle produces vectors
  2. High-coherence vectors are collected as teacher targets
  3. Lower-coherence vectors from similar tokens are trained toward them
  4. Generator embeddings are updated via gradient descent
  5. The ecology benefits: better embeddings → higher coherence → more crystals

Architecture
------------
  SelfDistillationTrainer collects (student_tokens, teacher_vec) pairs,
  batches them, and runs gradient steps on the Generator's projection head
  and encoder. Embeddings are updated in-place.

  Loss = cosine similarity loss between student output and teacher target.
  Temperature scaling controls how sharply the student is pulled.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F

from training.encode import encode_grad

logger = logging.getLogger(__name__)


@dataclass
class DistillationPair:
    tokens:      List[str]
    teacher_vec: np.ndarray
    coherence:   float


@dataclass
class DistillationReport:
    steps:        int
    mean_loss:    float
    mean_sim:     float
    pairs_used:   int


class SelfDistillationTrainer:
    """
    Online self-distillation trainer.

    Parameters
    ----------
    generator : Generator
        The model being trained.
    optimizer : torch.optim.Optimizer or None
        If None, one is created (AdamW, lr=1e-4).
    buffer_size : int
        Max number of distillation pairs retained.
    coherence_threshold : float
        Minimum coherence for a vector to qualify as a teacher.
    batch_size : int
        Number of pairs per gradient step.
    temperature : float
        Temperature for cosine similarity target sharpening.
    max_steps_per_call : int
        Gradient steps per train() call.
    """

    def __init__(
        self,
        generator,
        optimizer=None,
        buffer_size:         int   = 1024,
        coherence_threshold: float = 0.80,
        batch_size:          int   = 16,
        temperature:         float = 0.07,
        max_steps_per_call:  int   = 4,
    ):
        self.generator           = generator
        self.coherence_threshold = coherence_threshold
        self.batch_size          = batch_size
        self.temperature         = temperature
        self.max_steps_per_call  = max_steps_per_call

        self._buffer: deque = deque(maxlen=buffer_size)

        self.optimizer = optimizer or torch.optim.AdamW(
            generator.parameters(), lr=1e-4, weight_decay=1e-5
        )

        self._total_steps = 0
        self._total_loss  = 0.0

    # ------------------------------------------------------------------
    # Collect
    # ------------------------------------------------------------------

    def collect(
        self,
        tokens:    List[str],
        vec:       np.ndarray,
        coherence: float,
    ):
        """
        Add a (tokens, vec) pair to the distillation buffer if coherence
        exceeds threshold.
        """
        if coherence >= self.coherence_threshold:
            self._buffer.append(DistillationPair(
                tokens      = list(tokens),
                teacher_vec = vec.copy().astype(np.float32),
                coherence   = coherence,
            ))

    # ------------------------------------------------------------------
    # Train
    # ------------------------------------------------------------------

    def train(self) -> Optional[DistillationReport]:
        """
        Run up to max_steps_per_call gradient steps on buffered pairs.
        Returns None if buffer is too small.
        """
        if len(self._buffer) < self.batch_size:
            return None

        # The live-loop dropout policy (train vs eval) is an open architect
        # decision (2026-06-08-generator-dropout-diversity.md) — restore the
        # caller's mode on exit rather than deciding it here.
        was_training = self.generator.training
        self.generator.train()
        device = self.generator.device

        losses = []
        sims   = []

        for _ in range(self.max_steps_per_call):
            # Sample batch
            indices = np.random.choice(len(self._buffer), self.batch_size, replace=False)
            batch   = [list(self._buffer)[i] for i in indices]

            token_lists   = [p.tokens for p in batch]
            teacher_vecs  = np.stack([p.teacher_vec for p in batch])

            # Student forward pass — must be grad-enabled; encode_batch() is
            # @torch.no_grad() and would sever the graph (backward() fails).
            student_t   = encode_grad(self.generator, token_lists)
            teacher_t   = torch.tensor(teacher_vecs, dtype=torch.float32, device=device)

            # Cosine similarity loss (maximize similarity to teacher)
            sim  = F.cosine_similarity(student_t, teacher_t, dim=-1)
            loss = (1.0 - sim / self.temperature).mean()

            self.optimizer.zero_grad()
            loss.backward()

            torch.nn.utils.clip_grad_norm_(self.generator.parameters(), 1.0)
            self.optimizer.step()

            losses.append(float(loss.detach()))
            sims.append(float(sim.mean().detach()))
            self._total_steps += 1

        self.generator.train(was_training)

        report = DistillationReport(
            steps      = len(losses),
            mean_loss  = round(float(np.mean(losses)), 6),
            mean_sim   = round(float(np.mean(sims)), 6),
            pairs_used = len(self._buffer),
        )

        logger.debug(
            "Distillation: steps=%d loss=%.4f sim=%.4f buffer=%d",
            report.steps, report.mean_loss, report.mean_sim, report.pairs_used,
        )

        return report

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    @property
    def total_steps(self) -> int:
        return self._total_steps
