# ENGRAM

**Episodic-Networked Graph Retrieval & Agent Memory**

A cognitive memory architecture for persistent AI agents. Works with any model, any platform.

## What is this?

AI agents wake up with no memory. ENGRAM gives them a brain.

- **6 memory types** — episodic, semantic, procedural, insight, prospective, narrative
- **Semantic retrieval** — hybrid scoring (vector similarity + recency + salience + graph + emotion)
- **Consolidation** — hippocampus-inspired episode→knowledge distillation
- **Dream cycles** — creative recombination finding novel cross-domain connections
- **Memory metabolism** — token budget with natural forgetting pressure
- **Identity continuity** — Ed25519 signed memories, Merkle tree, wakeup attestation
- **Ground-truth anchoring** — prevents bias drift in self-referential LLM loops
- **Memory transplant** — signed inter-agent knowledge transfer
- **Prospective memory** — context-triggered "when I see X, do Y"

## Install

```bash
pip install engram-memory[all]
```

Or minimal (no LLM, hash embeddings):
```bash
pip install engram-memory
```

Or from source:
```bash
git clone https://github.com/invisiblemonsters/engram.git
cd engram
pip install -e ".[all]"
```

## Quick Start

```python
from engram import Engram

e = Engram()  # auto-discovers config from engram.yaml or env vars
e.remember("Deployed v1.0 today", type="episodic", tags=["milestone"], salience=0.9)
results = e.recall("What did I deploy?", top_k=5)
print(e.status())
```

## Configuration

ENGRAM loads config from `engram.yaml` (if present), then environment variables override.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGRAM_DATA_DIR` | `./engram_data` | Storage directory |
| `ENGRAM_EMBEDDING_PROVIDER` | `sentence-transformers` | `sentence-transformers`, `openai`, `ollama`, `huggingface` |
| `ENGRAM_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model name |
| `ENGRAM_LLM_PROVIDER` | `none` | `openai`, `anthropic`, `ollama`, `none` |
| `ENGRAM_LLM_MODEL` | | LLM model name |
| `ENGRAM_LLM_API_KEY` | | API key |
| `ENGRAM_LLM_BASE_URL` | | Custom endpoint URL |
| `ENGRAM_AGENT_NAME` | `Agent` | Name used in narrative generation |
| `ENGRAM_MAX_TOKENS` | `2000000` | Memory metabolism budget |

### engram.yaml

```yaml
data_dir: ./engram_data
embedding_provider: sentence-transformers
embedding_model: BAAI/bge-small-en-v1.5
llm_provider: ollama
llm_model: llama3.2
agent_name: MyAgent
```

### Constructor Overrides

```python
e = Engram(
    data_dir="./my_data",
    embedding_provider="openai",
    embedding_model="text-embedding-3-small",
    llm_provider="openai",
    llm_model="gpt-4o-mini",
    llm_api_key="sk-...",
)
```

## Provider Examples

### No LLM (embeddings only)
```python
e = Engram()  # works out of the box with sentence-transformers
e.remember("fact", type="semantic")
e.recall("query")
```

### OpenAI
```python
e = Engram(
    embedding_provider="openai",
    llm_provider="openai",
    llm_model="gpt-4o-mini",
    llm_api_key="sk-...",
)
```

### Anthropic
```python
e = Engram(
    llm_provider="anthropic",
    llm_model="claude-haiku-4-20250414",
    llm_api_key="sk-ant-...",
)
```

### Ollama (fully local)
```python
e = Engram(
    embedding_provider="ollama",
    embedding_model="nomic-embed-text",
    llm_provider="ollama",
    llm_model="llama3.2",
)
```

### HuggingFace / Sentence-Transformers
```python
e = Engram(
    embedding_provider="sentence-transformers",
    embedding_model="BAAI/bge-small-en-v1.5",
)
```

## API Reference

### `Engram(data_dir=None, config_path=None, **kwargs)`
Create an ENGRAM instance. Config from yaml → env vars → kwargs.

### `e.remember(content, type="episodic", tags=None, salience=0.5, emotion=None) → MemoryUnit`
Store a memory. Types: episodic, semantic, procedural, insight, prospective, narrative.

### `e.recall(query, top_k=10, type_filter=None, emotion=None) → list[MemoryUnit]`
Retrieve memories by semantic similarity with hybrid scoring.

### `e.sleep() → dict`
End-of-session: consolidate, dream, update narrative, metabolize.

### `e.wakeup() → dict`
Start-of-session: verify chain, consolidate, check anchoring, load context.

### `e.dream() → list[MemoryUnit]`
Run creative dream cycle (requires LLM).

### `e.intend(trigger, action, content=None) → MemoryUnit`
Create a prospective memory triggered by future context.

### `e.status() → dict`
Full system status: memory counts, metabolism, identity, anchoring.

### `e.export_memories(tags=None, ids=None) → dict`
Export signed memory package for transplant.

### `e.import_memories(package, auto_accept=False) → list[MemoryUnit]`
Import memories from another agent.

### `e.anchor(unit_id, method="human_verified")`
Mark a memory as externally verified.

## Architecture

```
                    ┌──────────────┐
                    │    Agent     │
                    │  (any LLM)  │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │    ENGRAM    │
                    │ Orchestrator │
                    └──────┬───────┘
                           │
        ┌──────────────────┼───────────────────┐
        │                  │                   │
   ┌────┴─────┐      ┌────┴──────┐      ┌────┴──────┐
   │ LanceDB  │      │ Embedder  │      │    LLM    │
   │  Store   │      │(universal)│      │(universal)│
   └──────────┘      └───────────┘      └───────────┘

   Consolidator ←→ Dreamer ←→ Narrative
        ↕              ↕           ↕
   Metabolism    Prospective   Anchoring
        ↕              ↕           ↕
   Identity ←→ Transplant ←→ SafeWriter
```

## Neuroscience Inspiration

| Brain Region | ENGRAM Analog |
|-------------|---------------|
| Hippocampus | LanceDB — fast episodic binding/indexing |
| Cortex | Semantic store — consolidated long-term knowledge |
| Amygdala | Salience scoring + emotional coloring |
| Sleep/REM | Dream cycle — creative recombination |
| Prefrontal | Prospective memory — future intentions |
| Metabolism | Token budget — forced prioritization |

## License

MIT
