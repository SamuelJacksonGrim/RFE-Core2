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
cognition/predictive_echo.py

Predictive echo engine — the system's anticipatory cognition layer.

Conscious-like systems are fundamentally predictive. This module
maintains a running model of the system's own state trajectory and
generates learning pressure from prediction error.

Architecture
------------
  A lightweight online linear predictor trained on the system's own
  vector sequence. At each step:
    1. Predict next state from recent history (linear extrapolation)
    2. Observe actual next state
    3. Compute prediction error
    4. Update predictor weights
    5. Derive curiosity, surprise, and tension signals

Prediction error drives
-----------------------
  curiosity    high error → explore more
  surprise     sudden spike → attention flag
  tension      sustained error → instability signal
  boredom      sustained low error → seek novelty

These feed directly into EmotionalGradient's modulation outputs.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class EchoReport:
    prediction_error: float   # L2 distance between prediction and reality
    curiosity:        float   # normalized prediction error ∈ [0, 1]
    surprise:         float   # sudden spike above rolling mean ∈ [0, 1]
    tension:          float   # sustained high error ∈ [0, 1]
    boredom:          float   # sustained low error ∈ [0, 1]
    prediction:       np.ndarray  # what the system expected


class PredictiveEcho:
    """
    Online linear predictor over the system's latent state trajectory.

    Parameters
    ----------
    dim : int
        Vector dimensionality.
    history_len : int
        Length of state history used for prediction.
    lr : float
        Base learning rate for weight updates.
    surprise_threshold : float
        Error multiplier above rolling mean that triggers surprise.
    error_history_len : int
        Window for rolling statistics (tension, boredom, surprise baseline).
    """

    def __init__(
        self,
        dim:                int   = 128,
        history_len:        int   = 8,
        lr:                 float = 0.05,
        surprise_threshold: float = 2.5,
        error_history_len:  int   = 32,
    ):
        self.dim                = dim
        self.history_len        = history_len
        self.lr                 = lr
        self.surprise_threshold = surprise_threshold

        # State history
        self._history: collections.deque = collections.deque(maxlen=history_len)

        # Prediction weights: (history_len, dim) → (dim,)
        # Initialized to "predict next = last seen" (identity on most recent)
        self._weights = np.zeros((history_len, dim), dtype=np.float64)
        if history_len > 0:
            self._weights[-1] = np.eye(dim)[0]  # weak identity bias on last step

        # Rolling error statistics
        self._error_history: collections.deque = collections.deque(
            maxlen=error_history_len
        )
        self._step = 0

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def predict(self) -> np.ndarray:
        """
        Generate a prediction of the next state from current history.

        Returns zeros (neutral) when history is insufficient.
        """
        if len(self._history) < 2:
            return np.zeros(self.dim, dtype=np.float32)

        # Pad history to history_len if needed
        history = list(self._history)
        while len(history) < self.history_len:
            history.insert(0, np.zeros(self.dim))

        H = np.stack(history[-self.history_len:])  # (history_len, dim)
        prediction = (self._weights * H).sum(axis=0)

        norm = np.linalg.norm(prediction)
        if norm > 1e-8:
            prediction = prediction / norm

        return prediction.astype(np.float32)

    def update(self, vec: np.ndarray) -> EchoReport:
        """
        Observe actual next state, compute error, update weights.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)
            The actual observed state.

        Returns
        -------
        EchoReport
        """
        prediction = self.predict()

        # Prediction error
        error = float(np.linalg.norm(vec.astype(np.float64) - prediction.astype(np.float64)))

        # Update predictor weights via online gradient descent
        if len(self._history) >= 2:
            self._update_weights(vec, prediction)

        # Update error history
        self._error_history.append(error)

        # Derive cognitive signals
        curiosity = self._compute_curiosity(error)
        surprise  = self._compute_surprise(error)
        tension   = self._compute_tension()
        boredom   = self._compute_boredom()

        # Commit new state to history AFTER computing prediction
        self._history.append(vec.copy().astype(np.float32))
        self._step += 1

        return EchoReport(
            prediction_error = round(error, 6),
            curiosity        = round(curiosity, 6),
            surprise         = round(surprise, 6),
            tension          = round(tension, 6),
            boredom          = round(boredom, 6),
            prediction       = prediction,
        )

    # ------------------------------------------------------------------
    # Signal computations
    # ------------------------------------------------------------------

    def _compute_curiosity(self, error: float) -> float:
        """
        Curiosity = normalized prediction error.
        High error → strong curiosity → explore.
        Uses a soft sigmoid normalization.
        """
        return float(1.0 / (1.0 + np.exp(-3.0 * (error - 0.5))))

    def _compute_surprise(self, error: float) -> float:
        """
        Surprise = how much this error exceeds the rolling mean.
        A spike well above baseline = genuine surprise.
        """
        if len(self._error_history) < 4:
            return 0.0
        baseline = float(np.mean(list(self._error_history)[-16:]))
        if baseline < 1e-8:
            return 0.0
        ratio    = error / (baseline + 1e-8)
        surprise = float(np.clip((ratio - 1.0) / (self.surprise_threshold - 1.0 + 1e-8), 0.0, 1.0))
        return surprise

    def _compute_tension(self) -> float:
        """
        Tension = sustained high prediction error.
        High tension = the system is in an unstable or novel regime.
        """
        if len(self._error_history) < 8:
            return 0.0
        recent = list(self._error_history)[-16:]
        mean_e = float(np.mean(recent))
        return float(np.clip(mean_e / 2.0, 0.0, 1.0))

    def _compute_boredom(self) -> float:
        """
        Boredom = sustained low prediction error + low variance.
        The system is accurately predicting itself → seek novelty.
        """
        if len(self._error_history) < 8:
            return 0.0
        recent   = list(self._error_history)[-16:]
        mean_e   = float(np.mean(recent))
        var_e    = float(np.var(recent))
        # Low mean AND low variance = boredom
        boredom  = float(np.clip((1.0 - mean_e) * (1.0 - min(var_e * 10, 1.0)), 0.0, 1.0))
        return boredom

    # ------------------------------------------------------------------
    # Weight update
    # ------------------------------------------------------------------

    def _update_weights(self, actual: np.ndarray, predicted: np.ndarray):
        """
        Online gradient step: minimize ||W·H - actual||².
        Adaptive learning rate: error-scaled (high error → larger update).
        """
        error_vec = actual.astype(np.float64) - predicted.astype(np.float64)
        error_mag = float(np.linalg.norm(error_vec))

        if error_mag < 1e-10:
            return

        history = list(self._history)
        while len(history) < self.history_len:
            history.insert(0, np.zeros(self.dim))
        H = np.stack(history[-self.history_len:]).astype(np.float64)

        # Adaptive lr: scale by error magnitude (larger errors → faster correction)
        adaptive_lr = self.lr * float(np.clip(error_mag, 0.1, 3.0))

        # Gradient: outer product of error and history
        grad = np.outer(np.ones(self.history_len), error_vec) * H
        self._weights += adaptive_lr * grad

        # Normalize rows to prevent weight explosion
        row_norms = np.linalg.norm(self._weights, axis=1, keepdims=True)
        self._weights /= np.clip(row_norms, 1.0, None)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def rolling_stats(self) -> dict:
        if not self._error_history:
            return {"mean_error": 0.0, "var_error": 0.0}
        errs = list(self._error_history)
        return {
            "mean_error": round(float(np.mean(errs)), 6),
            "var_error":  round(float(np.var(errs)), 6),
            "max_error":  round(float(np.max(errs)), 6),
            "step":       self._step,
        }
