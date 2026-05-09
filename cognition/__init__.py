"""
cognition — Higher-order cognitive processes for RFE-Core2.
"""

from cognition.predictive_echo import PredictiveEcho, EchoReport
from cognition.emotional_gradient import EmotionalGradient, EmotionalState
from cognition.recursive_attention import RecursiveAttention
from cognition.reflective_loop import ReflectiveLoop, ReflectionResult
from cognition.symbolic_binding import SymbolicBinding, ConceptBinding

__all__ = [
    "PredictiveEcho", "EchoReport",
    "EmotionalGradient", "EmotionalState",
    "RecursiveAttention",
    "ReflectiveLoop", "ReflectionResult",
    "SymbolicBinding", "ConceptBinding",
]
