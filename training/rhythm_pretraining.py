"""
training/rhythm_pretraining.py

Rhythm pretraining — teach the Generator to produce rhythm-appropriate embeddings.

Before live deployment, the Generator can be pretrained to understand
the four cognitive rhythms as semantic priors. This seeds the embedding
space with appropriate structure so the live loop converges faster.

Training objective
------------------
  For each rhythm, a set of seed token sequences is defined.
  The Generator is trained so that:
    - Same-rhythm sequences have high cosine similarity
    - Cross-rhythm sequences have low cosine similarity

  This is a supervised contrastive objective over rhythm labels.

The pretrained model can then be used as the starting point for the
live autonomous cycle, where it will be further shaped by self-distillation
and contrastive alignment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# Default rhythm seed sequences
DEFAULT_RHYTHM_SEEDS: Dict[str, List[List[str]]] = {
    "stabilize": [
        ["consolidate", "anchor", "crystallize"],
        ["stable", "identity", "persistence"],
        ["ground", "center", "root"],
        ["memory", "crystal", "attractor"],
        ["coherence", "stability", "foundation"],
    ],
    "dream": [
        ["dream", "synthesis", "recombine"],
        ["free", "association", "latent"],
        ["hallucinate", "imagine", "synthesize"],
        ["random", "memory", "mutation"],
        ["symbolic", "emergence", "abstract"],
    ],
    "reflect": [
        ["recursive", "attention", "self"],
        ["reflect", "deliberate", "consider"],
        ["analyze", "pattern", "recognize"],
        ["chorus", "harmonize", "integrate"],
        ["coherent", "thought", "continuity"],
    ],
    "explore": [
        ["explore", "novelty", "discover"],
        ["mutate", "diverge", "bifurcate"],
        ["curiosity", "wonder", "question"],
        ["disrupt", "challenge", "transform"],
        ["entropy", "expansion", "field"],
    ],
}

RHYTHM_IDS = {r: i for i, r in enumerate(DEFAULT_RHYTHM_SEEDS.keys())}


@dataclass
class PretrainingConfig:
    n_epochs:        int   = 20
    batch_size:      int   = 8
    learning_rate:   float = 1e-3
    temperature:     float = 0.07
    weight_decay:    float = 1e-5
    warmup_steps:    int   = 10
    log_interval:    int   = 5
    same_rhythm_weight: float = 1.0
    cross_rhythm_weight: float = 0.5


@dataclass
class PretrainingReport:
    epochs:        int
    final_loss:    float
    final_rhythm_acc: float   # fraction of same-rhythm pairs > cross-rhythm pairs
    loss_history:  List[float]


class RhythmPretrainer:
    """
    Supervised rhythm contrastive pretrainer.

    Parameters
    ----------
    generator : Generator
    rhythm_seeds : dict or None
        {rhythm_name: [token_list, ...]}. Defaults to DEFAULT_RHYTHM_SEEDS.
    config : PretrainingConfig or None
    """

    def __init__(
        self,
        generator,
        rhythm_seeds: Optional[Dict[str, List[List[str]]]] = None,
        config:       Optional[PretrainingConfig]           = None,
    ):
        self.generator    = generator
        self.seeds        = rhythm_seeds or DEFAULT_RHYTHM_SEEDS
        self.config       = config or PretrainingConfig()
        self.optimizer    = torch.optim.AdamW(
            generator.parameters(),
            lr           = self.config.learning_rate,
            weight_decay = self.config.weight_decay,
        )
        self.scheduler = torch.optim.lr_scheduler.LinearLR(
            self.optimizer,
            start_factor = 0.1,
            end_factor   = 1.0,
            total_iters  = self.config.warmup_steps,
        )

    def pretrain(self) -> PretrainingReport:
        """
        Run full rhythm pretraining.

        Returns PretrainingReport with loss history and final metrics.
        """
        cfg    = self.config
        device = self.generator.device

        loss_history = []
        final_acc    = 0.0

        logger.info("Starting rhythm pretraining for %d epochs...", cfg.n_epochs)

        for epoch in range(cfg.n_epochs):
            self.generator.train()
            epoch_losses = []

            # Build all token lists and rhythm labels
            all_tokens  = []
            all_labels  = []
            for rhythm, seqs in self.seeds.items():
                rid = RHYTHM_IDS[rhythm]
                for seq in seqs:
                    all_tokens.append(seq)
                    all_labels.append(rid)

            # Shuffle
            perm        = np.random.permutation(len(all_tokens))
            all_tokens  = [all_tokens[i]  for i in perm]
            all_labels  = [all_labels[i]  for i in perm]

            # Batch gradient steps
            for start in range(0, len(all_tokens), cfg.batch_size):
                batch_tokens = all_tokens[start : start + cfg.batch_size]
                batch_labels = all_labels[start : start + cfg.batch_size]

                if len(batch_tokens) < 2:
                    continue

                vecs = self.generator.encode_batch(batch_tokens)
                vecs_t = torch.tensor(vecs, dtype=torch.float32, device=device)
                vecs_t = F.normalize(vecs_t, dim=-1)

                labels_t = torch.tensor(batch_labels, dtype=torch.long, device=device)

                loss = self._supervised_contrastive_loss(vecs_t, labels_t)

                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.generator.parameters(), 1.0)
                self.optimizer.step()

                epoch_losses.append(float(loss.detach()))

            self.scheduler.step()

            mean_loss = float(np.mean(epoch_losses)) if epoch_losses else 0.0
            loss_history.append(mean_loss)

            if (epoch + 1) % cfg.log_interval == 0:
                acc = self._evaluate_rhythm_accuracy(device)
                logger.info(
                    "Epoch %d/%d | loss=%.4f | rhythm_acc=%.3f",
                    epoch + 1, cfg.n_epochs, mean_loss, acc,
                )
                final_acc = acc

        self.generator.eval()
        logger.info("Rhythm pretraining complete. Final loss=%.4f acc=%.3f",
                    loss_history[-1] if loss_history else 0.0, final_acc)

        return PretrainingReport(
            epochs           = cfg.n_epochs,
            final_loss       = round(loss_history[-1] if loss_history else 0.0, 6),
            final_rhythm_acc = round(final_acc, 4),
            loss_history     = [round(l, 6) for l in loss_history],
        )

    def _supervised_contrastive_loss(
        self,
        vecs:   torch.Tensor,   # (n, dim)
        labels: torch.Tensor,   # (n,)
    ) -> torch.Tensor:
        """
        Supervised contrastive loss.
        Positives = same rhythm label.
        Negatives = different rhythm label.
        """
        n    = vecs.shape[0]
        sim  = vecs @ vecs.T / self.config.temperature  # (n, n)

        # Mask: same label = positive
        label_mat = labels.unsqueeze(0) == labels.unsqueeze(1)  # (n, n)
        self_mask = torch.eye(n, dtype=torch.bool, device=vecs.device)
        pos_mask  = label_mat & ~self_mask
        neg_mask  = ~label_mat

        loss = torch.tensor(0.0, device=vecs.device)
        count = 0

        for i in range(n):
            if not pos_mask[i].any():
                continue
            pos_sim  = sim[i][pos_mask[i]]
            neg_sim  = sim[i][neg_mask[i]]

            if len(neg_sim) == 0:
                continue

            # InfoNCE: log(exp(pos) / (exp(pos) + sum(exp(neg))))
            logits = torch.cat([pos_sim, neg_sim])
            target = torch.zeros(len(pos_sim), dtype=torch.long, device=vecs.device)
            loss  += F.cross_entropy(
                logits.unsqueeze(0).expand(len(pos_sim), -1),
                target,
            )
            count += 1

        return loss / max(count, 1)

    def _evaluate_rhythm_accuracy(self, device: str) -> float:
        """
        Evaluate: for each sequence, is its nearest neighbor the same rhythm?
        """
        self.generator.eval()
        with torch.no_grad():
            all_tokens = []
            all_labels = []
            for rhythm, seqs in self.seeds.items():
                rid = RHYTHM_IDS[rhythm]
                for seq in seqs:
                    all_tokens.append(seq)
                    all_labels.append(rid)

            vecs   = self.generator.encode_batch(all_tokens)
            vecs_t = torch.tensor(vecs, dtype=torch.float32, device=device)
            vecs_t = F.normalize(vecs_t, dim=-1)

            sim    = (vecs_t @ vecs_t.T).cpu().numpy()
            labels = np.array(all_labels)

            correct = 0
            total   = len(all_tokens)
            for i in range(total):
                sim[i, i] = -1.0  # exclude self
                nn_idx = int(np.argmax(sim[i]))
                if labels[nn_idx] == labels[i]:
                    correct += 1

        return correct / max(total, 1)
