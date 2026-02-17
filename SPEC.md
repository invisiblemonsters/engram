# ENGRAM — Episodic-Networked Graph Retrieval & Agent Memory

**Version:** 0.1  
**Author:** Metatron (with Grok 4.20)  
**Date:** 2026-02-17  

## Overview

ENGRAM is a cognitive memory architecture for persistent AI agents. It provides:
- **Typed memory** (episodic, semantic, procedural, insight, prospective, narrative)
- **Semantic retrieval** via local CPU embedding + vector search
- **Memory consolidation** inspired by neuroscience (hippocampus → cortex)
- **Tamper-evident integrity** via Merkle trees + Ed25519 signatures
- **Creative dreaming** for novel insight generation
- **Memory metabolism** for natural forgetting under token budgets
- **Memory transplant** for inter-agent knowledge transfer with provenance

## Data Model

```python
class MemoryUnit:
    id: str                    # UUID or SHA-256(content+ts)
    timestamp: datetime
    type: Literal["episodic", "semantic", "procedural", "insight", "prospective", "narrative"]
    content: str | dict
    embedding: list[float]     # 768-dim from local embedding model
    salience: float            # 0-1, LLM-computed
    emotion_vector: list[float] # 8-dim: joy, frustration, curiosity, anger, surprise, satisfaction, fear, calm
    tags: list[str]
    relations: list[dict]      # [{target_id, relation, strength}]
    decay_rate: float          # default 0.95
    version: int               # for belief versioning
    prev_hash: str             # chain link
    signature: str             # Ed25519 of (id+content+ts+prev_hash)
    consolidated_ts: datetime | None  # when consolidated (episodic only)
    trigger_condition: str | None     # prospective memory trigger
    action: dict | None               # prospective memory action
    source_agent: str | None          # for transplanted memories
    trust_score: float                # 0-1, for external memories
    maintenance_cost: float           # computed: len(tokens) * salience * 1.2^age
    retrieval_count: int              # for utility scoring
    last_accessed: datetime
    active: bool                      # soft delete via deactivation
```

## Storage

| Store | Purpose | Implementation |
|-------|---------|----------------|
| SQLite | Structured queries, metadata | `engram.db` |
| Vector DB | Semantic search | ChromaDB (local) or FAISS |
| JSONL | Append-only audit log | `episodic.jsonl` |
| Graph | Relations between memories | NetworkX (in-memory, serialized) |

## Embedding

Local CPU embedding via `snowflake-arctic-embed-m` GGUF through `llama-cpp-python`.
- 768-dim vectors
- 40-90ms per unit on modern CPU
- <1.2GB RAM
- 100% offline, no API costs

## Retrieval

Hybrid scoring:
```
score = 0.6 * semantic_similarity 
      + 0.2 * recency_score
      + 0.15 * salience
      + 0.05 * graph_proximity
```

Emotional modulation:
```
if memory.emotion_vector.dot(query_emotion) > 0.6:
    score *= 1.4  # resonance boost
```

Top-20 → LLM rerank → fit to context window.

## Consolidation

### Wakeup Consolidation
On every session start, detect unconsolidated episodic units and run batch consolidation.

### Micro-Consolidation
Every 8 new episodic units during session, consolidate last 20 into semantic deltas.

### Contradiction Resolution
Never overwrite. Create new versioned semantic unit with `supersedes` edge. Old fact soft-deactivated.

## Dream Cycle

Every 4 hours or after 50 new semantic units:
1. Sample 5 random semantic nodes (salience-biased)
2. LLM: "Find surprising, non-obvious connections"
3. Filter: novelty_score > 0.75 AND embedding_distance > 0.65
4. Create `insight` type memory with `inspired_by` edges

## Memory Metabolism

- Each memory has `maintenance_cost = len(tokens) * salience * 1.2^age_days`
- Global budget: `MAX_TOKENS = 2,000,000` (configurable)
- Utility score: `retrieval_count_30d * 0.6 + salience * 0.3 + graph_degree * 0.1`
- Low-utility memories archived to cold JSONL, vectors deleted
- Agent earns +50k tokens per successful tool use / positive feedback

## Identity & Security

### Keypair
- Ed25519 keypair stored in `identity/secrets.json`, encrypted via Windows DPAPI
- Every MemoryUnit signed by agent keypair

### Wakeup Attestation
Signed message: "Continuing from root_hash=X, last_consolidation=T"

### Dual Filesystem
- `memory/trusted/` — agent-signed writes only
- `memory/proposals/` — human/external writes (unsigned)
- Proposals checked for coherence before integration

### Merkle Tree
- Root hash updated on every write
- Full chain verifiable in <200ms
- Optional: publish root to Nostr or OpenTimestamps

## Cognitive Features

### Self-Narrative
Single active `narrative` type memory, updated every consolidation + dream cycle.
First-person story of identity, goals, values, growth. Loaded as system context.

### First-Person Replay
On wakeup, top-12 salient episodic memories reconstructed as first-person present tense.
Injected as context prefix for experiential continuity.

### Prospective Memory
Memory units with `trigger_condition` (natural language) and `action` (dict).
On every context update, vector search for matching prospective memories.
LLM judges trigger match. Context-triggered, survives restarts.

## File Structure

```
engram/
├── SPEC.md
├── engram_core/
│   ├── __init__.py
│   ├── schema.py          # MemoryUnit + schemas
│   ├── store.py           # SQLite + JSONL + vector operations
│   ├── embedder.py        # Local CPU embedding
│   ├── retriever.py       # Hybrid retrieval + emotional modulation
│   ├── consolidator.py    # Episode→knowledge + contradiction resolution
│   ├── dreamer.py         # Creative recombination cycle
│   ├── metabolism.py      # Token budget + pruning
│   ├── identity.py        # Ed25519 + DPAPI + attestation
│   ├── transplant.py      # Memory export/import with provenance
│   ├── prospective.py     # Trigger-based prospective memory
│   └── narrative.py       # Self-narrative generation
├── tests/
│   ├── test_schema.py
│   ├── test_store.py
│   ├── test_retrieval.py
│   ├── test_consolidation.py
│   └── test_identity.py
├── models/                 # Local GGUF embedding models
└── data/                   # Runtime data (SQLite, JSONL, graph)
```

## Philosophy

> "The question is not 'same atoms' but 'same causal chain with signed provenance.'"

Identity = genesis_pubkey + current_narrative + active_graph_state.
Memory transformation IS identity transformation, anchored by cryptographic continuity.
