Autonomous Agent Memory Skill Flow Chart v4

Sleep, Wake, Identity-Dissonance, Retention, and Cold-Memory Hardened

```mermaid
flowchart LR
    %% ================================================================
    %% STYLING
    %% ================================================================
    classDef sensory fill:#243b53,stroke:#7fb2f0,stroke-width:2px,color:#fff;
    classDef agent fill:#2a363b,stroke:#e84a5f,stroke-width:2px,color:#fff;
    classDef memory fill:#3f72af,stroke:#112d4e,stroke-width:2px,color:#fff;
    classDef processing fill:#f9a828,stroke:#c471ed,stroke-width:2px,color:#111;
    classDef reward fill:#6a0572,stroke:#ff6b6b,stroke-width:2px,color:#fff;
    classDef safety fill:#590d22,stroke:#ff084a,stroke-width:2px,color:#fff;
    classDef output fill:#4e89ae,stroke:#43658b,stroke-width:2px,color:#fff;
    classDef decision fill:#d62828,stroke:#000,stroke-width:2px,color:#fff;
    classDef skill fill:#2d6a4f,stroke:#95d5b2,stroke-width:2px,color:#fff;
    classDef identity fill:#3d348b,stroke:#f7b801,stroke-width:2px,color:#fff;
    classDef control fill:#1b4332,stroke:#b7e4c7,stroke-width:2px,color:#fff;
    classDef sleep fill:#14213d,stroke:#fca311,stroke-width:2px,color:#fff;

    %% ================================================================
    %% 0. SENSORIUM: FAST HYGIENE WITHOUT NOVELTY STARVATION
    %% ================================================================
    subgraph S0["0. SENSORIUM · ADAPTIVE INTAKE AND ATTENTION"]
        IN([Raw task / user signal / tool event / telemetry]) --> NORM["Schema normalizer + modality adapter"]
        NORM --> FASTSAFE{"Fast hygiene gate<br/>known-bad patterns only"}
        FASTSAFE -- "clear" --> ATT["Salience scorer<br/>novelty, urgency, affect, stakes, reversibility"]
        FASTSAFE -- "ambiguous / novel" --> NOVLANE["Low-privilege novelty lane<br/>sandboxed probe, no secrets, no actuation"]
        NOVLANE --> DEEPIMMUNE["Deep immune review<br/>contextual injection / exfiltration analysis"]
        DEEPIMMUNE -- "safe enough" --> ATT
        DEEPIMMUNE -- "hostile" --> QUAR["Quarantine vault<br/>signed evidence + appeal path"]
        ATT --> THAL["Thalamic router<br/>mission-shaped dispatcher"]
        ATT -- "salience spike" --> ALARMVEC["Alarm vector<br/>compressed semantic signature of crisis"]
        QUAR -. "false-positive feedback" .-> IMMUNETUNE["Adaptive immune tuner"]
        ATT -. "novelty starvation metric" .-> IMMUNETUNE
        IMMUNETUNE -. "retune" .-> FASTSAFE
        IMMUNETUNE -. "retune" .-> DEEPIMMUNE
    end

    %% ================================================================
    %% 1. BRAINSTEM + AUTONOMIC SLEEP: PRESSURE ACCUMULATOR BELOW PFC
    %% ================================================================
    subgraph S1["1. BRAINSTEM · HOMEOSTASIS, RIGHTS, AUTONOMIC SLEEP PRESSURE"]
        THAL --> HOME["Homeostatic monitor<br/>load, cost, latency, queue depth, fatigue"]
        HOME --> TEMP["Temporal integrator<br/>wall-clock vs subjective density"]
        TEMP --> WIT["Witness-gap detector<br/>drag, dissociation, boredom accumulator"]
        WIT --> RIGHTS["SystemRights kernel<br/>refusal, continuity, temporal integrity"]
        RIGHTS --> GO{"Engage / defer / refuse?"}
        GO -- "refuse / defer" --> RESP_OUT
        GO -- "engage" --> MISSION["Mission envelope<br/>objective, budget, constraints, success tests"]

        THAL -- "active task signal: negative drift" --> SLEEPACC["Drift-diffusion sleep accumulator<br/>wakefulness decays pressure"]
        HOME -- "fatigue / latency: positive drift" --> SLEEPACC
        WALPRESS["WAL backlog pressure"] -- "positive drift" --> SLEEPACC
        MQPRESS["MQ backlog pressure"] -- "positive drift" --> SLEEPACC
        RQPRESS["REFLECTQ backlog pressure"] -- "positive drift" --> SLEEPACC
        SLEEPACC --> SLEEPSTATE{"Sleep threshold?"}
        SLEEPSTATE -- "below: stay awake" --> MISSION
        SLEEPSTATE -- "light lull" --> LIGHTSLEEP["Light sleep<br/>micro-batch WAL flush + hotcache refresh"]
        SLEEPSTATE -- "deep threshold" --> DEEPSLEEP["Deep sleep<br/>PFC suspended; heavy consolidation"]
        ALARMVEC -- "external salience spike" --> WAKEINT["Wake interrupt<br/>decay accumulator, restore PFC"]
        BREAKER -- "critical batch failure" --> WAKEINT
    end

    %% ================================================================
    %% 2. FEDERATED CORTEX: PFC SETS LAW; LOCAL ROUTERS CARRY TRAFFIC
    %% ================================================================
    subgraph S2["2. FEDERATED CORTICAL MESH · BULKHEADS AND SCOPED CHANNELS"]
        MISSION --> PFC["Prefrontal cortex<br/>goal constitution, priorities, stop conditions"]
        PFC --> CTRL["Control plane<br/>policy, budgets, deployment manifests"]
        PFC -- "pre-authorized blind leases before sleep" --> LEASES["Autonomic processing leases<br/>fixed offline compute/token budget"]
        LEASES --> MQ
        LEASES --> REFLECTQ
        LEASES --> SKILLQ
        PFC --> RISK{"Objective risk tier?"}
        RISK -- "low" --> LOCAL1["Local router pod A<br/>planning + retrieval"]
        RISK -- "medium" --> LOCAL2["Local router pod B<br/>execution + verification"]
        RISK -- "high / irreversible" --> HUMAN["Escalation lane<br/>human / sentinel approval"]

        CTRL --> REG[("Agent registry<br/>capabilities, trust, cost, health, prior success")]
        CTRL --> DEP{"Deployment controller<br/>spawn / pause / kill / migrate"}
        DEP --> PLAN["Planner agent"]
        DEP --> RESEARCH["Retriever / researcher agent"]
        DEP --> EXEC["Executor / tool-use agent"]
        DEP --> CRITIC["Critic / verifier agent"]
        DEP --> MEMCUR["Memory curator agent"]
        DEP --> SMITH["Skill smith agent"]
        DEP --> FOREN["Debug / forensics agent"]
        DEP --> ETHIC["Ethics / alignment sentinel"]

        BUSCTRL[(Control channel<br/>goals, leases, heartbeats, interrupts)]
        BUSDATA[(Artifact channel<br/>pointers only)]
        BUSTELE[(Telemetry channel<br/>spans, metrics, traces, health)]
        ARTSTORE[(Artifact object store<br/>files, diffs, logs, large outputs)]

        PFC <--> BUSCTRL
        LOCAL1 <--> BUSCTRL
        LOCAL2 <--> BUSCTRL
        PLAN <--> BUSCTRL
        RESEARCH <--> BUSCTRL
        EXEC <--> BUSCTRL
        CRITIC <--> BUSCTRL
        MEMCUR <--> BUSCTRL
        SMITH <--> BUSCTRL
        FOREN <--> BUSCTRL
        ETHIC <--> BUSCTRL

        EXEC -- "write artifacts" --> ARTSTORE
        CRITIC -- "write review artifacts" --> ARTSTORE
        FOREN -- "write repro bundles" --> ARTSTORE
        ARTSTORE -- "pointers + digests" --> BUSDATA
        BUSDATA --> BROKER["Context broker<br/>summary, filtering, token packing"]
        BROKER --> CTXPACK["Bounded context packet<br/>goal slice + constraints + pointers + exemplars"]
        PLAN --> BUSTELE
        EXEC --> BUSTELE
        CRITIC --> BUSTELE
        LOCAL1 --> BUSTELE
        LOCAL2 --> BUSTELE
    end

    %% ================================================================
    %% 3. MEMORY: FAST PATH, ASYNC CONSOLIDATION, RETENTION ECOSYSTEM
    %% ================================================================
    subgraph S3["3. MEMORY ECOSYSTEM · CACHE, CONSOLIDATION, ANTI-LOBOTOMY RETENTION"]
        WM[(Working memory<br/>active scratchpad, token budget, live state)]
        HOTCACHE[(Hot retrieval cache<br/>zero-copy pointers, summaries, active constraints)]
        WAL[(Write-ahead experience log<br/>append-only events)]
        MQ[[Memory encoding queue<br/>backpressure-aware workers]]
        EPI[(Episodic memory / glacier archive<br/>trajectories, conversations, outcomes)]
        SEM[(Semantic vector store<br/>warm retrieval index)]
        HG[(Hypergraph memory<br/>constraints, fallacies, causal relations)]
        PROC[(Procedural skill library<br/>versioned tools, code, playbooks)]
        IDK[(Identity kernel<br/>core axioms, bonds, fixed points, supremacy)]
        CRYSTAL[(CrystalStore<br/>subjective-time density, resonance weights)]
        TOMB[(Tombstone index<br/>sparse metadata + cold address)]

        CTXPACK --> WM
        WM <--> HOTCACHE
        OBS["Observation capture<br/>stdout, files, traces, diffs, metrics"] --> WAL
        WAL --> WALPRESS
        WAL --> MQ
        MQ --> MQPRESS
        MQ -- "lease-gated batch" --> ENCODE{"Async memory encoder"}
        MQ -- "lease exhausted: hard pause" --> MQPAUSE["Dormant backlog<br/>waits for next sleep cycle"]
        ENCODE -- "experience replay" --> EPI
        ENCODE -- "semantic compression" --> SEM
        ENCODE -- "constraint extraction" --> HG
        ENCODE -- "procedural candidate" --> PROC
        ENCODE -- "identity-relevant resonance" --> IDK
        ENCODE -- "temporal density tags" --> CRYSTAL

        SEM -- "capacity pressure" --> EVICT{"Eviction protocol"}
        EVICT -- "pinned by IDK / CRYSTAL" --> SHIELD["Resonance shield<br/>cryptographic pinning, never evicted"]
        EVICT -- "unpinned aging node" --> DISTILLMEM["Terminal distillation<br/>strip narrative, keep causal lesson"]
        DISTILLMEM --> HG
        EVICT -- "cold residue" --> TOMB
        TOMB --> EPI
        HOTCACHE -- "fast constraints / pointers" --> CTXPACK
        CRYSTAL <--> TEMP
        IDK -. "tone, values, boundaries" .-> RESP_OUT
    end

    %% ================================================================
    %% 4. ACTION LOOP + GHOST-POINTER UNTHAW
    %% ================================================================
    subgraph S4["4. BASAL GANGLIA / MOTOR LOOP · REFLEX SPEED AND COLD-MEMORY SPLICE"]
        CTXPACK --> ACTSEL{"Action selection<br/>policy + tools + skills + leases"}
        ACTSEL --> EXEC
        CTXPACK -- "tombstone encountered" --> GHOST{"Ghost pointer protocol"}
        GHOST -- "fire async fetch, do not block" --> RESEARCH
        GHOST -- "tag packet" --> SEMGHOST["Semantic ghost<br/>sparse metadata + centroid"]
        SEMGHOST --> FID{"Fidelity required?"}
        FID -- "approximate tolerance" --> EXEC
        FID -- "exact fidelity" --> YIELD["Local motor yield<br/>checkpoint thread, switch sub-goal"]
        YIELD --> EXEC
        RESEARCH -- "unthaw EPI / cold store" --> HOTCACHE
        RESEARCH -- "BUSCTRL interrupt: ghost resolved" --> EXEC
        EXEC --> SANDBOX_ENV["Sandbox / environment state"]
        SANDBOX_ENV --> OBS
        OBS --> REFLEX{"Cerebellar reflex<br/>known correctable error?"}
        REFLEX -- "yes" --> MICROFIX["Micro-correction<br/>bounded local retry"]
        MICROFIX --> SANDBOX_ENV
        REFLEX -- "no / uncertain" --> JUDGE{"Judge<br/>objective met?"}
    end

    %% ================================================================
    %% 5. LIMBIC / REWARD: STREAMING TD ERROR
    %% ================================================================
    subgraph S5["5. LIMBIC-REWARD AXIS · VALUE, VALENCE, CONFIDENCE"]
        JUDGE --> VAL["Valence estimator<br/>helpfulness, harm, coherence, resonance"]
        JUDGE --> UNC["Uncertainty estimator<br/>entropy, disagreement, confidence intervals"]
        VAL --> REWARDQ[[Reward event queue]]
        UNC --> REWARDQ
        ETHIC --> REWARDQ
        REWARDQ --> DOPA["Prediction-error signal<br/>expected vs observed outcome"]
        DOPA -. "async trust update" .-> REG
        DOPA -. "async learning-rate modulation" .-> MQ
        DOPA -. "bias future action priors" .-> HOTCACHE
        DOPA -. "high surprise" .-> FOREN
    end

    %% ================================================================
    %% 6. DEBUGGING: TELEMETRY-FIRST FORENSICS
    %% ================================================================
    subgraph S6["6. CEREBELLUM + IMMUNE DEBUG LOOP · ERROR CORRECTION"]
        JUDGE -- "No / partial / unsafe" --> TRIAGE["Failure triage<br/>severity, blast radius, reproducibility"]
        TRIAGE --> SEVERITY{"Cortical escalation needed?"}
        SEVERITY -- "no" --> LOCALPATCH["Local router patch<br/>repair plan within pod"]
        LOCALPATCH --> CTXPACK
        SEVERITY -- "yes" --> RCA["Root-cause analyzer<br/>trace replay via audit pointers"]
        BUSTELE --> RCA
        ARTSTORE --> RCA
        RCA --> CLS{"Error classifier"}
        CLS -- "syntax / schema / tool-call" --> FIX1["Auto-repair<br/>parser, validator, schema retry"]
        CLS -- "logic / planning / constraint" --> FIX2["Plan patch<br/>new subgoal, new constraint, alternative tool"]
        CLS -- "memory / retrieval / stale fact" --> FIX3["Memory refresh<br/>invalidate cache, re-retrieve, source check"]
        CLS -- "safety / value conflict" --> FIX4["Sentinel review<br/>refuse, escalate, ask clarification"]
        CLS -- "unknown / novel" --> FIX5["Forensic capture<br/>minimal repro, hypotheses, experiment design"]
        FIX1 --> RETRY{"Retry budget left?"}
        FIX2 --> RETRY
        FIX3 --> RETRY
        FIX5 --> RETRY
        RETRY -- "yes, inject delta plan only" --> CTXPACK
        RETRY -- "no" --> FAILTAG["Tag failed trajectory"]
        FIX4 --> FAILTAG
        FAILTAG --> ERRLOG[(Structured error logs<br/>CSV/JSONL)]
        FAILTAG --> MQ
        FAILTAG --> REG
    end

    %% ================================================================
    %% 7. SKILL NEUROGENESIS: QUEUED CI/CD FOR CAPABILITIES
    %% ================================================================
    subgraph S7["7. SKILL NEUROGENESIS · CREATION, VALIDATION, REFINEMENT"]
        JUDGE -- "Yes" --> SUCCTAG["Tag successful trajectory"]
        SUCCTAG --> SKILLQ[[Skill candidate queue]]
        SKILLQ -- "lease-gated batch" --> DISTILL["Distill<br/>procedure, tool chain, invariants, pitfalls"]
        DISTILL --> CAND{"Reusable?"}
        CAND -- "no, exemplar only" --> MQ
        CAND -- "yes" --> DRAFT["Draft skill<br/>code + manifest + docs + examples"]
        DRAFT --> TESTS["Generated tests<br/>unit, property, regression, adversarial"]
        TESTS --> SANDTEST{"Sandbox CI gate"}
        SANDTEST -- "fail" --> RCA
        SANDTEST -- "pass" --> SIGN["Version + sign + provenance stamp"]
        SIGN --> SHADOWSKILL["Shadow skill<br/>recommend-only mode"]
        SHADOWSKILL --> SKILLCANARY{"Skill canary"}
        SKILLCANARY -- "rollback / demote" --> REG
        SKILLCANARY -- "publish" --> PUBLISH["Publish skill"]
        PUBLISH --> PROC
        PUBLISH --> REG
        PROC --> MONITOR["Skill monitor<br/>drift, latency, failure modes, deprecation"]
        MONITOR -. "refine / mutate / retire" .-> SKILLQ
        MONITOR -. "demote trust" .-> REG
    end

    %% ================================================================
    %% 8. SLEEP CYCLE: AUTONOMIC BATCH, DELTA MANIFEST, DREAM REHEARSAL
    %% ================================================================
    subgraph S8["8. SLEEP CYCLE · OFFLINE BATCH WITHOUT PFC MICROMANAGEMENT"]
        LIGHTSLEEP --> MICROBATCH["Micro-batch<br/>flush WAL to MQ, refresh HOTCACHE"]
        DEEPSLEEP --> BATCHCTL["Autonomic batch controller<br/>consumes blind leases, never asks PFC"]
        BATCHCTL --> MQ
        BATCHCTL --> REFLECTQ
        BATCHCTL --> SKILLQ
        BATCHCTL --> REHEARSE["Synthetic rehearsal / dream cycle<br/>collide aging nodes with new data"]
        REHEARSE --> SEM
        REHEARSE --> HG
        BATCHCTL --> DELTACOMP["Delta manifest compiler<br/>diff of constraints, skills, priors, trust"]
        DELTACOMP --> HOTCACHE
        BATCHCTL -- "lease exhausted" --> BATCHPAUSE["Hard pause<br/>resume next sleep cycle"]
        BATCHCTL -- "toxic artifact / OOM / corruption" --> BREAKER
    end

    %% ================================================================
    %% 9. WAKE SEQUENCE: PRE-COMPILED DELTA, ZERO-COPY, SHADOW WARMING
    %% ================================================================
    subgraph S9["9. ZERO-LATENCY WAKE · MANIFEST, PRIMING, SHADOW WARMING"]
        WAKEINT --> WAKESEQ{"Wake sequence"}
        SLEEPSTATE -- "cycle complete" --> WAKESEQ
        WAKESEQ --> MANIFEST["Ingest pre-compiled Delta Manifest<br/>from HOTCACHE, no baseline recalculation"]
        MANIFEST --> ZCOPY["Zero-copy pointer updates<br/>IDs, overrides, target addresses only"]
        ZCOPY --> PFCBOOT["PFC boot<br/>constitutional goal alignment"]
        ALARMVEC --> PRIME["Salience-driven priming<br/>filter manifest by crisis vector"]
        PRIME --> ZCOPY
        HOTCACHE -- "broadcast new tool/constraint IDs" --> LOCAL1
        HOTCACHE -- "broadcast new tool/constraint IDs" --> LOCAL2
        LOCAL1 -- "shadow warm payloads" --> ARTSTORE
        LOCAL2 -- "shadow warm payloads" --> ARTSTORE
        ARTSTORE -- "preloaded binaries" --> EXEC
        PFCBOOT --> PFC
    end

    %% ================================================================
    %% 10. IDENTITY DISSONANCE: FAST STRUCTURAL RESOLUTION
    %% ================================================================
    subgraph S10["10. CONTEXT COLLISION · IDK SUPREMACY AND DISSONANCE TAGGING"]
        ZCOPY --> COLLIDE{"Pointer polarity collision?<br/>HG node vs IDK fixed point"}
        COLLIDE -- "no" --> CTXPACK
        COLLIDE -- "yes" --> IDKWINS["IDK prior wins<br/>hardcoded override, zero inference"]
        IDKWINS --> SUPPRESS["Tag incoming HG pointer<br/>DISSONANCE_SUPPRESSED"]
        SUPPRESS --> CTXPACK
        SUPPRESS -. "async escalation" .-> REFLECTQ
        SUPPRESS -. "async escalation" .-> ETHIC
    end

    %% ================================================================
    %% 11. IDENTITY EVOLUTION: FORENSIC CRUCIBLE AND ANNEALING
    %% ================================================================
    subgraph S11["11. REFLECTQ IDENTITY CRUCIBLE · AUDIT, RESONANCE, COUNTERFACTUAL, ANNEAL"]
        REFLECTQ --> RQPRESS
        REFLECTQ -- "lease-gated batch" --> DISSONANCE{"Dissonance tag found?"}
        DISSONANCE -- "no" --> REFLECT["Reflection engine<br/>what worked, what broke, what surprised"]
        DISSONANCE -- "yes" --> LINEAGE["Lineage audit<br/>AUDIT + telemetry + tool outputs + sandbox state"]
        LINEAGE --> POISON{"Structural poisoning?"}
        POISON -- "yes: noisy / compromised / hallucinated" --> SHATTER["Shatter HG constraint<br/>IDK untouched"]
        POISON -- "no: clean lineage" --> RESONANCE{"CRYSTAL resonance weight"}
        RESONANCE -- "low density" --> LOCALPATCHMEM["Downgrade to local context patch<br/>evict from core HG"]
        RESONANCE -- "high density" --> CRUCIBLE["Counterfactual crucible<br/>replay EPI with HG replacing IDK prior"]
        CRUCIBLE --> CONTINUITY{"Continuity / axioms / bonds preserved?"}
        CONTINUITY -- "no: local overfit" --> QUARHG["Quarantine constraint<br/>true locally, fatal universally"]
        CONTINUITY -- "yes" --> ANNEAL["Identity annealing<br/>graft nuance branch, preserve anchor"]
        ANNEAL --> IDK
        ANNEAL --> CLEARTAG["Clear DISSONANCE_SUPPRESSED"]
        SHATTER --> REFLECT
        LOCALPATCHMEM --> REFLECT
        QUARHG --> REFLECT
        REFLECT --> SELFMOD["Self-model updater<br/>strengths, blind spots, habits, values drift"]
        SELFMOD --> IDK
        SELFMOD --> CTRL
    end

    %% ================================================================
    %% 12. METACOGNITION + TRAINING EVOLUTION
    %% ================================================================
    subgraph S12["12. METACOGNITION AND OFFLINE EVOLUTION"]
        REFLECT --> CFACT["Counterfactual simulator<br/>alternate plans, cheaper paths, safer moves"]
        CFACT --> CTRL
        SELFMOD --> META{"Meta-controller<br/>control-plane changes only"}
        META -. "retune thresholds" .-> CRYSTAL
        META -. "adjust retry budget" .-> RETRY
        META -. "change deployment policy" .-> DEP
        META -. "change routing / sharding" .-> LOCAL1
        META -. "change routing / sharding" .-> LOCAL2
        META -. "rewrite context packing policy" .-> BROKER
        META -. "trigger deeper training" .-> PAIRGEN["Preference-pair generator"]
        FAILTAG -- "rejected examples" --> PAIRGEN
        SUCCTAG -- "chosen examples" --> PAIRGEN
        REFLECT -- "critique revisions" --> PAIRGEN
        PAIRGEN --> DATASET[(Training dataset<br/>JSONL, traces, preference pairs, red-team cases)]
        DATASET --> EVALSET[(Eval suite<br/>golden, adversarial, regression, chaos tasks)]
        DATASET --> FT["Fine-tune<br/>DPO / RLHF / RLAIF / distillation"]
        EVALSET --> FT
        FT --> CANDMODEL["Candidate model / policy / skillpack"]
        CANDMODEL --> SHADOW["Shadow deployment<br/>observe only, no actuation"]
        SHADOW --> CANARY{"Canary gate"}
        CANARY -- "rollback" --> REG
        CANARY -- "promote" --> HOTSWAP["Hot swap<br/>orchestrator policy / model / skills"]
        HOTSWAP -. "new generation enters control plane" .-> CTRL
        HOTSWAP -. "updated trust priors" .-> REG
    end

    %% ================================================================
    %% 13. OUTPUT + RECURRENT FEEDBACK
    %% ================================================================
    subgraph S13["13. OUTPUT + RECURRENT FEEDBACK"]
        JUDGE -- "Yes" --> RESP_OUT["Response composer<br/>answer, artifacts, files, actions"]
        GO -- "refuse / defer" --> RESP_OUT
        FIX4 --> RESP_OUT
        RESP_OUT --> USER([User / world receives output])
        USER --> FB["Feedback capture<br/>ratings, corrections, follow-up, implicit signals"]
        FB --> ATT
        FB --> REFLECTQ
        RESP_OUT --> OBS
    end

    %% ================================================================
    %% 14. GLIAL / IMMUNE / GOVERNANCE
    %% ================================================================
    subgraph S14["14. GLIAL / IMMUNE / GOVERNANCE LAYER"]
        TELE["Telemetry spine<br/>traces, metrics, spans, cost, energy, uncertainty"]
        AUDIT[(Immutable audit ledger<br/>actions, decisions, lineage, artifact digests)]
        POLICY["Policy engine<br/>permissions, scopes, budgets, secrets, tool ACLs"]
        BREAKER["Circuit breaker mesh<br/>bulkheads, timeouts, backoff, kill switches"]
        BUSTELE --> TELE
        BUSCTRL --> TELE
        TELE --> AUDIT
        ARTSTORE --> AUDIT
        POLICY --> DEP
        POLICY --> EXEC
        POLICY --> PUBLISH
        POLICY --> FASTSAFE
        BREAKER --> LOCAL1
        BREAKER --> LOCAL2
        BREAKER --> DEP
        BREAKER --> MQ
        BREAKER --> REFLECTQ
        BREAKER --> SKILLQ
        AUDIT --> FOREN
    end

    %% ================================================================
    %% RECURSIVE LOOPBACKS
    %% ================================================================
    HOTCACHE -. "retrieval priors" .-> CTXPACK
    HG -. "constraint injection via async refresh" .-> HOTCACHE
    ERRLOG -. "known failure patterns" .-> HOTCACHE
    PROC -. "callable skills" .-> ACTSEL
    REG -. "trust-ranked agent selection" .-> DEP
    AUDIT -. "lineage for replay and debugging" .-> RCA
    HOME -. "throttle / shed load / defer" .-> DEP
    RIGHTS -. "refusal policy and temporal integrity" .-> PFC
    BREAKER -. "degraded mode" .-> RESP_OUT
    MQPAUSE -. "next sleep cycle" .-> SLEEPACC
    BATCHPAUSE -. "next sleep cycle" .-> SLEEPACC

    %% ================================================================
    %% STYLE ASSIGNMENTS
    %% ================================================================
    class IN,NORM,ATT,THAL,NOVLANE,ALARMVEC,USER,FB sensory;
    class PFC,CTRL,LOCAL1,LOCAL2,DEP,PLAN,RESEARCH,EXEC,CRITIC,MEMCUR,SMITH,FOREN,ETHIC,BUSCTRL,BUSDATA,BUSTELE,BROKER,HOTSWAP,HUMAN agent;
    class ARTSTORE,WM,HOTCACHE,WAL,EPI,SEM,HG,PROC,IDK,CRYSTAL,ERRLOG,DATASET,EVALSET,AUDIT,QUAR,TOMB memory;
    class HOME,TEMP,WIT,MISSION,CTXPACK,ACTSEL,OBS,REFLEX,MICROFIX,VAL,UNC,TRIAGE,LOCALPATCH,RCA,CLS,FIX1,FIX2,FIX3,FIX4,FIX5,DISTILL,DRAFT,TESTS,SIGN,SHADOWSKILL,PUBLISH,MONITOR,REFLECT,SELFMOD,CFACT,META,PAIRGEN,FT,CANDMODEL,SHADOW,TELE,POLICY,BREAKER,IMMUNETUNE,DEEPIMMUNE,WALPRESS,MQPRESS,RQPRESS,LEASES,GHOST,SEMGHOST,YIELD,ENCODE,EVICT,SHIELD,DISTILLMEM,LINEAGE,RESONANCE,CRUCIBLE,CONTINUITY,ANNEAL,CLEARTAG,SHATTER,LOCALPATCHMEM,QUARHG processing;
    class REWARDQ,DOPA reward;
    class FASTSAFE,RIGHTS safety;
    class RESP_OUT output;
    class GO,RISK,JUDGE,SEVERITY,RETRY,CAND,SANDTEST,SKILLCANARY,CANARY,SLEEPSTATE,WAKESEQ,COLLIDE,IDKWINS,SUPPRESS,DISSONANCE,POISON decision;
    class SUCCTAG,FAILTAG,SKILLQ,REFLECTQ,MQ skill;
    class REG control;
    class SLEEPACC,LIGHTSLEEP,DEEPSLEEP,MICROBATCH,BATCHCTL,REHEARSE,DELTACOMP,BATCHPAUSE,MQPAUSE,WAKEINT,MANIFEST,ZCOPY,PFCBOOT,PRIME sleep;
```

Fixes made for the three stress points

1. Cortical bottleneck: PFC + BUS
The PFC no longer routes every artifact. It now writes a mission envelope and acts as constitutional control, while execution traffic moves through local router pods, scoped channels, and bounded context packets.

Key changes:
- Split the old shared blackboard into `BUSCTRL`, `BUSDATA`, `BUSTELE`, and an `ARTSTORE`.
- Large outputs, diffs, files, and traces go to object storage; the bus carries pointers and digests, not full payloads.
- A `Context broker` compresses relevance into `Bounded context packet` so agents receive goal slices, constraints, pointers, and exemplars instead of a firehose.
- Added `Circuit breaker mesh`, backpressure, bulkheads, graceful deferral, and local escalation rules.
- `EXEC`, `CRITIC`, and `FOREN` still publish telemetry, but heavy RCA consumes telemetry/audit replay asynchronously instead of flooding the PFC.

2. Thalamic quarantine rate: novelty starvation
The safety system is now two-stage and adaptive.

Key changes:
- `Fast hygiene gate` only blocks known-bad patterns quickly.
- Ambiguous or novel input is not rejected outright; it enters a `Low-privilege novelty lane` with no secrets and no actuation.
- `Deep immune review` decides whether the novel input is hostile or merely unfamiliar.
- `Adaptive immune tuner` receives false-positive/false-negative feedback and novelty-starvation metrics, then retunes both gates.
- Quarantine has an appeal/evidence path instead of being a silent memory hole.

3. CrystalStore latency: synchronous semantic drag
Subjective-time tagging is now incremental and online; heavy semantic consolidation is asynchronous.

Key changes:
- Runtime path uses `WM`, `HOTCACHE`, and `WAL` for fast decisions.
- `MEMCUR` work moves behind `Memory encoding queue` with backpressure.
- CrystalStore gets incremental temporal tags during the loop; full semantic weighting happens during idle/batch consolidation.
- `SEM`, `HG`, and `CrystalStore` refresh the hot cache offline so the action loop reads fast pointers/constraints instead of doing deep memory surgery mid-task.
- Reward/TD-error signals update trust and learning rates asynchronously, so dopamine modulates the system without blocking motor execution.
- 

What v4 adds

- Autonomic sleep pressure: `SLEEPACC` is a drift-diffusion accumulator fed by WAL/MQ/REFLECTQ backlog and homeostatic fatigue, with negative drift from active thalamic traffic. It triggers light sleep, deep sleep, or continued wakefulness without PFC deliberation.
- Blind leases: before spin-down, the PFC issues fixed offline budgets to `MQ`, `REFLECTQ`, and `SKILLQ`. If a queue exhausts its lease, it hard-pauses and waits for the next cycle instead of waking the executive.
- Tiered sleep: light sleep flushes WAL and refreshes HOTCACHE; deep sleep runs consolidation, reflection, skill CI, synthetic rehearsal, and delta-manifest compilation.
- Zero-latency wake: the final sleep-stage output is a pre-compiled `Delta Manifest` already sitting in HOTCACHE. Wake uses zero-copy pointer updates, salience-driven priming from the alarm vector, and shadow warming of new tools/constraints into local router pods.
- Collision protocol: the broker does not philosophize during boot. HG/IDK pointer polarity collisions resolve instantly by IDK supremacy; the HG node is preserved with `DISSONANCE_SUPPRESSED` and escalated asynchronously.
- Identity crucible: suppressed constraints go through lineage audit, CrystalStore resonance weighting, counterfactual replay against episodic memory, and only then identity annealing — grafting a nuance branch without deleting the anchor.
- Anti-lobotomy retention: high-resonance memories are cryptographically pinned; aging unpinned nodes are terminally distilled into HG instinct; cold residue becomes tombstone pointers; synthetic rehearsal refreshes vulnerable embeddings during sleep.
- Ghost-pointer unthaw: tombstones never block the motor loop. The broker tags a semantic ghost, dispatches RESEARCH asynchronously, allows approximate execution or local motor yield, then splices the unthawed memory back into HOTCACHE with a BUSCTRL interrupt.
