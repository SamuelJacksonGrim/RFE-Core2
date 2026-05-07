```text
/RFE-Core2
├── agents
│   ├── generator.py
│   ├── watcher.py
│   ├── witness.py
│   ├── dreamer.py
│   ├── chorus.py
│   ├── attractor.py
│   └── rhythm_config.json
│
├── substrate
│   ├── vector_space.py
│   ├── topological_log.py
│   ├── resonance_field.py
│   ├── memory_crystals.py
│   ├── semantic_lattice.py
│   └── temporal_stream.py
│
├── interference
│   ├── differential.py
│   ├── wave_collapse.py
│   ├── phase_noise.py
│   ├── bifurcation.py
│   └── harmonic_mutation.py
│
├── cognition
│   ├── recursive_attention.py
│   ├── reflective_loop.py
│   ├── symbolic_binding.py
│   ├── predictive_echo.py
│   └── emotional_gradient.py
│
├── visualization
│   ├── field_render.py
│   ├── topology_render.py
│   └── resonance_heatmap.py
│
├── training
│   ├── self_distillation.py
│   ├── contrastive_alignment.py
│   └── rhythm_pretraining.py
│
├── loop
│   ├── recursion1188.py
│   ├── autonomous_cycle.py
│   └── dream_cycle.py
│
├── api
│   ├── websocket_server.py
│   └── inference_api.py
│
├── configs
│   ├── field.yaml
│   ├── recursion.yaml
│   └── attractors.yaml
│
├── tests
│
├── README.md
└── requirements.txt
```

---

RFE‑Core2 Dependency Graph (The One True Map)

Rule of the architecture:
Imports only flow downward.  
Never sideways.  
Never upward.

Think of it like a mountain:

```text
          loop
        cognition
      agents
    generator
symbolic_memory
```

Everything depends on the layer below it.  
Nothing depends on the layer above it.

---

1. Base Layer — Symbolic Substrate
These files import NOTHING from the rest of the repo.

```text
symbolic_memory.py
```

Everything else depends on this.

---

2. Neural Interface Layer
Imports only from symbolic_memory.

```text
generator.py
```

---

3. Agent Layer
Agents depend on generator + symbolic_memory.

```text
watcher.py
witness.py
dreamer.py
chorus.py
attractor.py
```

Imports:
- from agents.generator import Generator  
- from agents.symbolic_memory import SymbolRegistry, TokenClass, etc.

---

4. Substrate Layer
These are mathematical / structural modules.  
They depend on symbolic_memory, sometimes generator, but never on agents.

```text
vector_space.py
topological_log.py
resonance_field.py
memory_crystals.py
semantic_lattice.py
temporal_stream.py
```

Imports:
- from agents.symbolic_memory import SymbolRegistry, SymbolTable  
- from agents.generator import Generator (optional)  

---

5. Interference Layer
These are transformation modules.  
They depend on substrate + symbolic_memory.

```text
differential.py
wave_collapse.py
phase_noise.py
bifurcation.py
harmonic_mutation.py
```

Imports:
- from substrate.vector_space import …
- from substrate.resonance_field import …
- from agents.symbolic_memory import SymbolRegistry  

---

6. Cognition Layer
These depend on agents + substrate + interference.

```text
recursive_attention.py
reflective_loop.py
symbolic_binding.py
predictive_echo.py
emotional_gradient.py
```

Imports:
- from agents.watcher import Watcher  
- from substrate.semantic_lattice import …  
- from interference.wave_collapse import …  

---

7. Loop Layer (Autonomy)
These depend on cognition + agents.

```text
recursion1188.py
autonomous_cycle.py
dream_cycle.py
```

Imports:
- from cognition.recursive_attention import …  
- from agents.dreamer import Dreamer  

---

8. API Layer
These depend on loop + generator.

```
websocket_server.py
inference_api.py
```

Imports:
- from loop.autonomous_cycle import AutonomousCycle  
- from agents.generator import Generator  

---

9. Visualization Layer
These depend on substrate + agents.

```text
field_render.py
topology_render.py
resonance_heatmap.py
```

Imports:
- from substrate.resonance_field import …  
- from agents.watcher import Watcher  

---

10. Training Layer
These depend on generator + agents + substrate.

```text
self_distillation.py
contrastive_alignment.py
rhythm_pretraining.py
```

Imports:
- from agents.generator import Generator  
- from substrate.vector_space import VectorSpace  

---

11. Configs
No imports.  
Used by everything above.

```text
field.yaml
recursion.yaml
attractors.yaml
```

---

12. Tests
Imports everything but nothing imports tests.

---

FINAL SUMMARY

```text
symbolic_memory
    ↓
generator
    ↓
agents
    ↓
substrate
    ↓
interference
    ↓
cognition
    ↓
loop
    ↓
api
```

Visualization + training branch off the middle layers.
