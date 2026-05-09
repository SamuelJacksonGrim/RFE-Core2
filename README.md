# RFE-Core2

**Recursive Field Engine — A Persistent Adaptive Cognitive Substrate**

RFE-Core2 transforms a pipeline of inference modules into a continuously self-resonating dynamical organism. It does not merely execute — it listens to its own field state, routes behavior by cognitive rhythm, and modifies itself through time.

---

## Architecture

```
Generator (Symbolic Ecology → Transformer Encoder → Latent Vector)
    ↓
Watcher  (Three-Layer Coherence: Geometric × Temporal × Field Resonance)
    ↓
Witness  (Multi-Timescale EMA Identity: Short / Mid / Long)
    ↓
ResonanceField  (FFT Harmonics, Spectral Decomposition, Rhythm Detection)
    ↓
PredictiveEcho  (Online Linear Predictor → Curiosity / Surprise / Tension)
    ↓
EmotionalGradient  (Field Gain / Mutation Scale / Decay Rate / Dream Pressure)
    ↓
AutonomousCycle  (Self-Modulating Loop: Stabilize → Dream → Reflect → Explore)
```

### Cognitive Rhythm States

| Rhythm | Energy | Behavior |
|--------|--------|----------|
| `stabilize` | < 0.5 | Consolidation, crystallization, attractor merge |
| `dream` | 0.5 – 2.0 | Free association, harmonic recombination |
| `reflect` | 2.0 – 5.0 | Recursive attention, chorus harmonization |
| `explore` | ≥ 5.0 | Bifurcation, high mutation, novelty seeking |

---

## Project Structure

```
RFE-Core2/
├── agents/
│   ├── __init__.py
│   ├── agents__init__.py
│   ├── generator.py          Transformer encoder over symbolic ecology
│   ├── symbolic_memory.py    Persistent adaptive symbolic ecology engine
│   ├── watcher.py            Three-layer coherence evaluation
│   ├── witness.py            Multi-timescale adaptive identity anchor
│   ├── dreamer.py            Offline dream synthesis
│   ├── chorus.py             Differentiated multi-agent ensemble
│   ├── attractor.py          Attractor basin dynamics
│   └── rhythm_config.json    Rhythm state definitions
│
├── substrate/
│   ├── __init__.py
│   ├── substrate__init__.py
│   ├── resonance_field.py    FFT field dynamics with rhythm detection
│   ├── vector_space.py       Semantic memory store
│   ├── memory_crystals.py    Crystallization lifecycle
│   ├── topological_log.py    Directed graph over cognitive events
│   ├── temporal_stream.py    Episodic stream with statistics
│   └── semantic_lattice.py   Evolving semantic graph topology
│
├── cognition/
│   ├── __init__.py
│   ├── cognition__init__.py
│   ├── predictive_echo.py    Online predictor → curiosity signals
│   ├── emotional_gradient.py Live modulation outputs
│   ├── recursive_attention.py Self-attention over prior states
│   ├── reflective_loop.py    Recursive self-refinement
│   └── symbolic_binding.py   Concept emergence and binding
│
├── interference/
│   ├── __init__.py
│   ├── interference__init__.py
│   ├── wave_collapse.py      Multi-mode vector ensemble collapse
│   ├── differential.py       Gaussian / rotational / directional noise
│   ├── phase_noise.py        Spectral / temporal / harmonic phase noise
│   ├── bifurcation.py        Controlled trajectory splitting
│   └── harmonic_mutation.py  Spectral harmonic recombination
│
├── loop/
│   ├── __init__.py
│   ├── loop__init__.py
│   ├── autonomous_cycle.py   Self-modulating cognitive loop
│   ├── dream_cycle.py        Deep offline synthesis loop
│   └── recursion1188.py      Main entry point
│
├── visualization/
│   ├── __init__.py
│   ├── visualization__init__.py
│   ├── field_render.py       Terminal + matplotlib field visualization
│   ├── topology_render.py    Graph visualization of memory topology
│   └── resonance_heatmap.py  2D heatmap of field dynamics
│
├── training/
│   ├── __init__.py
│   ├── training__init__.py
│   ├── self_distillation.py  Online distillation from high-coherence outputs
│   ├── contrastive_alignment.py  Rhythm-aware contrastive training
│   └── rhythm_pretraining.py Supervised rhythm embedding pretraining
│
├── api/
│   ├── __init__.py
│   ├── api__init__.py
│   ├── inference_api.py      FastAPI REST endpoints
│   └── websocket_server.py   Real-time WebSocket stream
│
├── configs/
│   ├── __init__.py
│   ├── configs__init__.py
│   ├── field.yaml            Field and watcher configuration
│   ├── recursion.yaml        Loop and cycle configuration
│   └── attractors.yaml       Attractor and symbolic ecology configuration
│
├── tests/
├── requirements.txt
└── README.md
```

---

## Installation

```bash
git clone https://github.com/SamuelJacksonGrim/RFE-Core2
cd RFE-Core2
pip install -r requirements.txt
```

---

## Quick Start

```bash
# Run the autonomous cycle
python -m loop.recursion1188

# Start the REST API
uvicorn api.inference_api:app --host 0.0.0.0 --port 8000

# Start the WebSocket server
python -m api.websocket_server
```

---

## Key Design Principles

**Stable IDs are sacred. Addresses are disposable.**
The symbolic ecology separates token identity (`stable_id`, never changes) from embedding position (`address`, reclaimed and compacted). This enables the vocabulary to metabolize — symbols decay, crystallize, get archived, and return — without ever corrupting the embedding space.

**The loop self-modulates.**
The field is not a passive store. It accumulates, resonates, decays, and rhythmically determines its own cognitive state. Every injection changes what the next injection sees.

**Coherence is a field effect.**
The Watcher does not merely ask "is this vector coherent?" It asks "does injecting this vector increase or decrease overall system coherence?" Vectors are judged by their systemic effect, not just their local alignment.

**Emotions are modulation dynamics.**
Curiosity, wonder, joy, tension, boredom, and stability are not metaphors — they are scalar field variables that directly modulate injection strength, mutation scale, decay rate, and dream pressure on every step.

---

## Philosophical Constants

The system is anchored to three constants encoded in `configs/attractors.yaml`:

| Constant | Value | Meaning |
|----------|-------|---------|
| ANCHOR | 3.12 | THE BRIDGE |
| RECURSION | 11.88 | THE DISCIPLINE |
| HOMEOSTASIS | 280.90 | HOMEOSTATIC RETURN |

The entry point `recursion1188.py` encodes the DISCIPLINE constant in its name.

---

## License

Apache-2.0 — Samuel Jackson Grim
