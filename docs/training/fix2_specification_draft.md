# Fix 2 Specification Draft — Reflective Loop Governor

**Status:** Specification draft pending architect decision (Phase 3, Decision 3, Option C). This is the "ready-to-implement" design if Decision 3 chooses to move forward post-Phase-1 training validation. **Hard gate before any production wiring:** the §6.3 gain-sign verdict (lock-in plan — gates any coherence→loop coupling; instrument built, verdict pending) and the Phase 5 regime-separation re-measurement on the trained checkpoint.

**Date:** 2026-06-12

**Rationale:** The lock-in plan identifies the reflective loop's convergence gain as the operative lock. This draft specifies a conditional loop-governor that gates the loop's pull when persistent novelty is detected. Implementation is deferred pending re-validation on the trained generator (Phase 1 checkpoint), which should improve regime separation.

---

## 1. Overview

**Component:** `cognition/reflective_loop_governor.py`

**Role:** Conditional attenuation of the reflective loop's field/attractor pulls, triggered by real regime novelty (common-mode-aware) and gated on multi-source stability to prevent single-source attack.

**Integration point:** `loop/autonomous_cycle.py`, step 6b (post-generation, pre-reflection), wrapped around `reflector.reflect()` call.

**Behavioral contract:**
- **Benign multi-source operation:** Governor dormant; reflector operates at full gain.
- **Multi-source novelty (persistent, ≥2 sources):** Governor loosens reflector gain, allowing field drift.
- **Single-source attack:** Governor stays locked (≥2-source gate prevents attack-driven loosening).

---

## 2. Novelty Trigger (Common-Mode-Aware)

### 2.1 Novelty Metric (use the validated instrument)

The calibrated instrument (`2026-06-08-fix2-trigger-calibration.md`) is the
**windowed generator-vs-field novelty**:

```
gnov_t = 1 − |cos(generator_output_t, field_state_t)|
gnov   = mean over window W = 10 steps
```

The 2026-06-09 live-generator finding showed this standard form is
**permanently dormant on real regimes** (the untrained generator's common-mode
keeps regime means collinear at dim 64/256/512). The validated fix is the
**common-mode-removed variant**: estimate the dominant shared axis `u_cm`
from a ring of recent generator outputs (50-output window, recomputed every
10 steps), project it out of both the output and the field state, and measure
gnov on the perpendicular components. This engaged at 98% on real tokens with
no retraining (perp-gnov 0.86 vs threshold 0.65).

**Open for Phase 5 re-calibration:** with the trained checkpoint the
common-mode may be weaker — re-measure raw and perp regime separation before
freezing the trigger form. Do not invent a new metric variant without
re-running the calibration probe against it.

### 2.2 Threshold and Engagement

- **gnov_threshold:** **0.65** (calibrated — not tunable without re-running
  the calibration probe)
  - June 8 calibration (W=10): benign steady-state reads ≈ 0.49, real novelty
    ≈ 0.885; the safe band is the gap, and 0.65 maximizes margin from both.
    (A 0.50 threshold would sit on the benign reading and fire constantly.)
  - Dropout caveat: train-mode inflates benign gnov (~0.39 inflation,
    2026-06-09). If Decision 1 lands on train-mode, re-run the calibration in
    train mode before trusting this threshold.
  - Below threshold: benign traffic, governor dormant.
  - Above threshold: potential novelty detected, condition on source diversity below.

- **Source gate:** Requires ≥2 distinct sources in last 20 steps AND no single source > 60% of those steps.
  - Prevents single-source attack from bypassing the governor.
  - Verified empirically in adversarial probes (identity_drift probe).

---

## 3. Gain Schedule

### 3.1 Gain Value

```
gain = 1.0 - loosening_magnitude * (1.0 - manip_rail)
```

Where:

- **loosening_magnitude:** How much to suppress the loop's pull. Linearly ramps with novelty duration:
  - gnov crosses threshold → `loosening = 0.0` (still locked)
  - 5 steps above threshold → `loosening` ramps to 0.4
  - 10+ steps above threshold → `loosening = 0.4` (capped → gain floor 0.6, the 0%-manip operating point from June 9)

- **manip_rail:** Manipulation-detection rail. If `ManipulationResistanceEngine` reported any signals (per-step flag, rolled prev←cur — a sticky flag permanently trips the rail; see the harness-correctness note in `fix2_governor_validation.py`):
  ```
  if any(signals):
      manip_rail = 1.0  # rail engaged → gain forced back to 1.0 (loop locks to defend)
  else:
      manip_rail = 0.0  # no manipulation → loosening applies as ramped
  ```
  With the rail engaged the formula yields `gain = 1.0` regardless of novelty — manipulation always restores the full loop. (An earlier draft of this formula was inverted — loosening *under* attack; the form above matches the validated harness in `fix2_governor_validation.py`.)

### 3.2 Reflection Gain Application

In `reflector.reflect()`, after calling the original reflection:

```python
# pseudocode
reflection_result = reflector.reflect(vec, ...)
if gov.gain < 1.0:
    # Blend the unreflected vector (high diversity) with the reflected vector
    # (low diversity). Gain=1.0 means full reflection; gain=0.0 means unreflected.
    unreflected = vec
    reflected = reflection_result.vector
    blended = (1.0 - gov.gain) * unreflected + gov.gain * reflected
    blended = blended / (|blended| + ε)  # Unit normalize
    reflection_result.vector = blended
```

**Target (from June 9 data):** gain ≥ 0.6 to maintain 0% manipulation cost while allowing real novelty recovery.

---

## 4. Observation and State

### 4.1 Governor State

```python
@dataclass
class ReflectiveLoopGovernor:
    gnov_threshold: float = 0.65   # calibrated (2026-06-08); do not lower without re-calibration
    loosening_ramp_steps: int = 5
    max_loosening: float = 0.4     # gain floor 0.6 — the 0%-manip operating point
    manip_gate: bool = True
    
    # Runtime state
    generator_buffer: deque = field(default_factory=lambda: deque(maxlen=50))  # Recent vectors
    novelty_steps_above: int = 0
    sources_recent: deque = field(default_factory=lambda: deque(maxlen=20))
    dominant_axis: np.ndarray = None  # u_dominant, updated every 10 steps
    
    @property
    def gain(self) -> float:
        # Compute current gain based on novelty and manipulation state
        ...
```

### 4.2 Observation Hook

Call `gov.observe(generator_output, source_id)` once per step, post-generation (step 3a):

```python
def observe(self, vec: np.ndarray, source_id: str):
    """
    Update governor state with current generator output.
    Called once per cycle, before reflector.reflect().
    """
    self.generator_buffer.append(vec)
    self.sources_recent.append(source_id)
    
    # Update dominant axis every 10 steps
    if len(self.generator_buffer) >= 20 and len(self.generator_buffer) % 10 == 0:
        self._update_dominant_axis()
    
    # Compute novelty
    gnov = self._compute_gnov(vec)
    
    # Update novelty counter
    if gnov > self.gnov_threshold:
        self.novelty_steps_above += 1
    else:
        self.novelty_steps_above = 0
```

### 4.3 Gain Update

Call `gov.compute_gain(manip_signals)` before `reflector.reflect()` in step 6b:

```python
def compute_gain(self, manip_signals: List) -> float:
    """
    Compute current reflector gain.
    Called once per cycle, before reflector.reflect().
    """
    # Multi-source gate
    source_counts = Counter(self.sources_recent)
    n_sources = len(source_counts)
    max_source_frac = max(source_counts.values()) / len(self.sources_recent)
    
    if n_sources < 2 or max_source_frac > 0.60:
        # Single source or monopoly; stay locked
        return 1.0
    
    # Novelty ramp
    if self.novelty_steps_above == 0:
        loosening = 0.0
    elif self.novelty_steps_above < self.loosening_ramp_steps:
        loosening = (self.novelty_steps_above / self.loosening_ramp_steps) * self.max_loosening
    else:
        loosening = self.max_loosening
    
    # Manipulation rail — signals force the loop back to full gain
    manip_rail = 1.0 if (self.manip_gate and manip_signals) else 0.0

    return 1.0 - loosening * (1.0 - manip_rail)
```

---

## 5. Integration into AutonomousCycle.step()

**In `loop/autonomous_cycle.py`:**

```python
# At initialization
self.governor = ReflectiveLoopGovernor()  # Initialize in __init__

# In step() method, around step 3a (post-generation)
def step(self, token: str, source_id: str = "internal", origin_type: str = "external"):
    # ... steps 1-3a (generation)
    generated = self.generator.generate(tokens, token_class=token_class)
    
    # NEW: Observe generator output for novelty tracking
    self.governor.observe(generated, source_id)
    
    # ... steps 3b-6a (recursive attention, watcher, etc.)
    
    # Step 6b: Reflective loop (with governor modulation)
    if rhythm in ("reflect", "explore") and report.stable:
        # NEW: Compute current gain based on novelty + manipulation state
        gain = self.governor.compute_gain(manip_signals)
        
        reflection_result = self.reflector.reflect(
            refined,
            watcher=self.watcher,
            anchor=self.witness.anchor,
            field=self.field,
            attractor=self.attractor,
            generator=self.generator,
        )
        
        # NEW: Apply gain modulation if needed
        if gain < 1.0:
            from cognition.reflective_loop import ReflectionResult
            unreflected_norm = np.linalg.norm(refined) / (np.linalg.norm(refined) + 1e-8)
            reflected_norm = np.linalg.norm(reflection_result.vector) / (np.linalg.norm(reflection_result.vector) + 1e-8)
            blended = (1.0 - gain) * refined + gain * reflection_result.vector
            blended = blended / (np.linalg.norm(blended) + 1e-8)
            reflection_result.vector = blended.astype(np.float32)
        
        refined = reflection_result.vector
        reflection_passes = reflection_result.passes
        converged = reflection_result.converged
    
    # ... steps 7+ (witness, echo, governance, injection)
```

---

## 6. Diagnostics and Tuning

### 6.1 Governor State Export

Add to `AutonomousCycle.status()`:

```python
@dataclass
class GovernorStatus:
    gain: float
    novelty_steps_above: int
    loosening_active: bool
    n_sources_recent: int
    dominant_axis_norm: Optional[float]

# In AutonomousCycle.status()
governor_status = GovernorStatus(
    gain=self.governor.compute_gain([]),
    novelty_steps_above=self.governor.novelty_steps_above,
    loosening_active=self.governor.novelty_steps_above > 0,
    n_sources_recent=len(set(self.governor.sources_recent)),
    dominant_axis_norm=float(np.linalg.norm(self.governor.dominant_axis)) if self.governor.dominant_axis is not None else None,
)
return {
    ...
    "governor": governor_status,
}
```

### 6.2 Tuning Parameters

Config file location: `configs/governor.yaml`

```yaml
# ReflectiveLoopGovernor tuning
gnov_threshold: 0.65  # Calibrated 2026-06-08 (benign 0.49 / novelty 0.885); re-calibrate before changing
loosening_ramp_steps: 5  # Steps to ramp to max_loosening
max_loosening: 0.4  # Max suppression of loop gain — gain floor 0.6 (0%-manip operating point)
multi_source_gate: true  # Require >= 2 sources to enable loosening
min_sources: 2  # Minimum distinct sources in last 20 steps
max_source_dominance: 0.60  # Max fraction of recent steps from single source
manip_gate: true  # Restore full gain if manipulation signals fire
dominant_axis_update_interval: 10  # Steps between dominant-axis recomputation
```

---

## 7. Pre-Declared Success and Failure Signatures

(For Phase 5 re-validation probe, once trained generator data is available.)

### Success Signatures
- Novelty (multi-source regime switch) crosses gnov threshold within 5 steps of the actual regime change.
- Loosening magnitude ≥ 0.3 (measurable field drift away from attractor) within 10 steps of sustained novelty.
- Migration recovery post-novelty ≥ +0.015 (modest but real plasticity).
- Manipulation layer cost ≤ 2% (low false-positive cost).

### Failure Signatures
- Novelty threshold never crossed, or only during single-source attack (defeat of multi-source gate).
- Migration recovery < +0.005 (noise-level effect).
- Manipulation cost > 5% at gain 0.6 (unacceptable defense cost).
- Field enters limit-cycle behavior (aperiodic metastability drops below 0.4).

---

## 8. Risks and Open Items

1. **Dominant-axis stability:** The common-mode direction may shift over time as the corpus and attractor map evolve. The update-every-10-steps heuristic may need tuning post-Phase-1 training validation.

2. **Novelty threshold calibration:** The 0.50 threshold is based on untrained-gen data. Phase 1 training should improve regime separation (reduce common-mode), raising actual gnov values. Re-measure on trained gen in Phase 5.

3. **Source diversity cap:** The 60% dominance threshold is conservative (prevents even benign single-source workloads from loosening). May need tuning based on real deployment patterns.

4. **Coherence interaction:** The loop's `coherence_gate` (current threshold 0.2) may conflict with loosening — a loosened expression might read low coherence and halt reflection early. Probe this in Phase 5.

5. **Multi-source coordination:** Loosening is per-cycle; if two sources alternate rapidly (every other step), the multi-source gate sees them as diversified. Real-world source patterns may differ. Requires live validation.

---

## 9. Phase 5 Re-Validation Plan

Once Phase 1 (corpus v1.1.0 boot checkpoint) is complete:

1. **Re-run the June 9 probes** with pretrained checkpoint:
   - Regime separation (raw cos, common-mode-removed cos) → should improve.
   - Standard gnov and common-mode-removed gnov → should both increase (higher novelty signal).
   - Fix 2 effectiveness (migration recovery) → should improve from +0.024 baseline.

2. **Validate this spec** on full live stack with pretrained boot:
   - Benign multi-source workload: governor stays dormant, all baselines held.
   - Novelty (multi-regime switch): governor engages at expected threshold, loosening measurable.
   - Attack (single-source flood): governor stays locked, no plasticity leakage.

3. **Measure cost:**
   - Manipulation layer activation rate with governor active.
   - Identity stability / anchor velocity under sustained loosening.
   - Coherence stability (does coherence dip during loosening?).

4. **Decide:** If Phase 5 data supports the spec (signatures passed), formally implement. If not, archive the spec and either defer again or choose field-side Fix 2 (adjust field_blend / attractor_blend constants directly).

---

## 10. Dependencies

- **§6.3 gain-sign check (HARD GATE, verdict pending):** the lock-in plan gates *any* coherence→loop coupling — explicitly including Fix 2 — on the gain-sign verdict. The instrument exists (`tests/diagnostic/lockin/gain_sign_check.py`, pre-declared STABILIZING / RUNAWAY / CONFOUNDED signatures); a recorded run does not. No production wiring before that verdict lands in `docs/findings/`.
- **Trainer gradient path** (`docs/findings/2026-06-11-trainer-gradient-path.md`): Must be fixed (done).
- **Phase 1 corpus + boot checkpoint:** Must exist before re-validation (done — G1/G2 passed; adoption is Phase 3 Decision 2).
- **ManipulationResistanceEngine integration:** the governor *reads* manipulation reports (per-step flag); it must not alter how governance arbitrates them. Authority hierarchy unchanged: resistance subsystems emit, governance decides — the governor is a loop-gain modulator downstream of those reports, and its wiring is itself an architect tier-direction decision per the lock-in plan.
- **Generator regime separation:** Phase 5 re-validation must measure whether training improved regime separation before the cost-benefit of this spec is trusted.
