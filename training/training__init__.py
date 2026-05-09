"""
training — Self-supervised training components for RFE-Core2.
"""

from training.self_distillation import SelfDistillationTrainer, DistillationReport
from training.contrastive_alignment import ContrastiveAlignmentTrainer, ContrastiveReport
from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig, PretrainingReport

__all__ = [
    "SelfDistillationTrainer", "DistillationReport",
    "ContrastiveAlignmentTrainer", "ContrastiveReport",
    "RhythmPretrainer", "PretrainingConfig", "PretrainingReport",
]
