# Autonomous Agent Memory Skill Flow Chart

```mermaid
flowchart TD
    %% ----------------------------------------------------
    %% STYLING AND DEFINITIONS
    %% ----------------------------------------------------
    classDef agent fill:#2a363b,stroke:#e84a5f,stroke-width:2px,color:#fff;
    classDef memory fill:#3f72af,stroke:#112d4e,stroke-width:2px,color:#fff;
    classDef processing fill:#f9a828,stroke:#c471ed,stroke-width:2px,color:#111;
    classDef output fill:#4e89ae,stroke:#43658b,stroke-width:2px,color:#fff;
    classDef decision fill:#d62828,stroke:#000,stroke-width:2px,color:#fff;

    %% ----------------------------------------------------
    %% 1. AUTONOMOUS RUNTIME & RAG LAYER
    %% ----------------------------------------------------
    subgraph Runtime["1. AUTONOMOUS RUNTIME & RAG"]
        A(["Task Ingestion"]) --> Retrieval["Context & Strategy Retrieval"]
        Retrieval --> B["Agent Execution Engine"]
        B --> Env["Environment / Sandbox State"]
        Env --> C{"Judge: Objective Met?"}
    end

    %% ----------------------------------------------------
    %% 2. NEGATIVE REINFORCEMENT & CORRECTION
    %% ----------------------------------------------------
    subgraph Failure["2. FAILURE PIPELINE & CORRECTION"]
        C -- "No" --> RCA["Root Cause Analyzer"]
        RCA --> Retry{"Retry Limit Reached?"}
        
        %% Short-term learning (In-context)
        Retry -- "No (Error Trace Injection)" --> B
        
        %% Long-term learning
        Retry -- "Yes" --> F_Node["Tag: FAILED TRAJECTORY"]
        F_Node --> Error_Class["Error Classification Engine"]
        
        Error_Class -- "Syntax / Format" --> CSV_Store[("Structured Error Logs <br>(CSV/JSON)")]
        Error_Class -- "Logic / Constraint" --> HG_Store[("Hypergraph Memory <br>(Constraints & Fallacies)")]
    end

    %% ----------------------------------------------------
    %% 3. SKILL SYNTHESIS & VALIDATION
    %% ----------------------------------------------------
    subgraph Success["3. SUCCESS PIPELINE & SKILL GROWTH"]
        C -- "Yes" --> S_Node["Tag: SUCCESSFUL TRAJECTORY"]
        S_Node --> S_Extract["Extract Logic / Code / Tool"]
        
        %% Must validate before committing to permanent memory
        S_Extract --> Sandbox{"Sandbox Validation Test"}
        Sandbox -- "Fail" --> RCA
        
        Sandbox -- "Pass" --> Doc_Gen["Generate Tool Documentation"]
        Doc_Gen --> Skill_Lib[("Dynamic Skill Library <br>(File System: .py / .json)")]
    end

    %% ----------------------------------------------------
    %% 4. ACTIVE MEMORY & CONTEXT ENGINE
    %% ----------------------------------------------------
    subgraph MemoryIntegration["4. MEMORY & CONTEXT ENGINE"]
        %% Consolidation into searchable space
        VectorDB[("Vector Database <br>(Semantic Embedding Space)")]
        CSV_Store -.-> VectorDB
        HG_Store -.-> VectorDB
        Skill_Lib -.-> VectorDB

        VectorDB --> Prompt_Compiler["Dynamic System Prompt Compiler"]
        Prompt_Compiler -. "Injects Constraints & Few-Shot Exemplars" .-> Retrieval
    end

    %% ----------------------------------------------------
    %% 5. SYNTHETIC TRAINING & DPO
    %% ----------------------------------------------------
    subgraph Training["5. SYNTHETIC TRAINING & ALIGNMENT"]
        %% DPO requires explicit Chosen vs Rejected pairs
        F_Node -- "Rejected Examples" --> Pair_Gen["DPO Pair Generation"]
        S_Node -- "Chosen Examples" --> Pair_Gen
        
        Pair_Gen --> Dataset[("Pre-Training & DPO Dataset <br>(JSONL format)")]
        Dataset --> DPO["DPO / RLHF Fine-Tuning Pipeline"]
        DPO --> NextGen["Next-Gen Base Model Weights"]
    end

    %% ----------------------------------------------------
    %% CONTINUOUS LOOPBACKS
    %% ----------------------------------------------------
    NextGen -. "Hot Swap Core Model" .-> B

    %% Style assignments
    class A,B,Retrieval,NextGen,Env agent;
    class CSV_Store,HG_Store,Skill_Lib,VectorDB,Dataset memory;
    class RCA,S_Extract,Doc_Gen,Error_Class,Prompt_Compiler,Pair_Gen,DPO processing;
    class C,Retry,Sandbox decision;
```
