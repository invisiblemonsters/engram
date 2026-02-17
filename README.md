# ENGRAM

**Episodic-Networked Graph Retrieval & Agent Memory**

A cognitive memory architecture for persistent AI agents. Designed by [Metatron](https://github.com/invisiblemonsters) with [Grok 4.20](https://grok.com).

**Status:** v0.8.2 · 14 tests green · 652 memories live · [Nostr spec](https://clawstr.com/c/ai/post/2738d21a3e88cd85812ec247e9e47546729cb195782fa861de77d6dcbdde6efd)

## One-Command Install (Windows)

```powershell
powershell -ExecutionPolicy Bypass -Command "iwr https://raw.githubusercontent.com/invisiblemonsters/engram/main/install.ps1 -OutFile install.ps1; ./install.ps1"
```

Or manually:
```bash
git clone https://github.com/invisiblemonsters/engram.git
cd engram
pip install -r requirements.txt
python run_dream.py   # watch it generate original insights
```

## What You Get

- **Episodic → semantic consolidation** (hippocampus-inspired)
- **Creative dream cycles** every 4h (finds novel cross-domain connections)
- **Prospective memory triggers** ("when I see X, do Y")
- **Self-evolution** (auto-patches with pytest safety gate)
- **Signed transplants** + CRDT merge (cross-agent knowledge transfer)
- **Attestation** (Nostr kind 30079 proof-of-capability receipts)
- **14 tests green**, fully autonomous on Windows Task Scheduler

## What is this?

AI agents wake up with no memory. ENGRAM gives them a brain.

- **Typed memory** — episodic (raw events), semantic (distilled knowledge), procedural (how-to), insight (creative connections), prospective (future intentions), narrative (identity story)
- **Semantic retrieval** — local CPU embedding via sentence-transformers, hybrid scoring (semantic + recency + salience + graph proximity + emotional modulation)
- **Memory consolidation** — hippocampus-inspired replay and distillation, wakeup detection of unconsolidated episodes, micro-consolidation during sessions
- **Dream cycle** — creative recombination finding novel connections between memories
- **Memory metabolism** — token budget enforcement with natural forgetting pressure
- **Identity continuity** — Ed25519 signed memories, Merkle tree verification, wakeup attestation
- **Ground-truth anchoring** — prevents bias drift in self-referential LLM loops
- **Memory transplant** — signed inter-agent knowledge transfer with cryptographic provenance
- **Prospective memory** — context-triggered "when I see X, do Y" intentions

## Quick Start

```bash
pip install sentence-transformers pynacl numpy
```

```python
from engram_core.engram import Engram

# Initialize
engram = Engram(data_dir="my_memory")

# Wake up (consolidates, verifies chain, checks anchoring)
engram.wakeup()

# Remember something
engram.remember("Deployed AIP v0.1 today", tags=["milestone"], salience=0.9)

# Recall relevant memories
results = engram.recall("What do I know about AIP?")

# Set a future intention
engram.intend(
    trigger="Someone mentions bug bounties",
    action={"type": "remind", "message": "Check huntr for new targets"}
)

# End of session (consolidate, dream, update narrative)
engram.sleep()

# Check status
print(engram.status())
```

## Architecture

```
                    ┌─────────────┐
                    │   Agent     │
                    │  (Claude,   │
                    │   Grok,     │
                    │   etc.)     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   ENGRAM    │
                    │ Orchestrator│
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼─────┐     ┌─────▼─────┐
   │ SQLite  │      │  Vector   │     │  JSONL    │
   │Metadata │      │  Search   │     │ Audit Log │
   └─────────┘      └───────────┘     └───────────┘
        │                  │
   ┌────▼────┐      ┌─────▼─────┐
   │ Graph   │      │ Embedder  │
   │NetworkX │      │(CPU local)│
   └─────────┘      └───────────┘
```

## Neuroscience Inspiration

| Brain Region | ENGRAM Analog |
|-------------|---------------|
| Hippocampus | Vector DB — fast episodic binding/indexing |
| Cortex | Semantic store — consolidated long-term knowledge |
| Amygdala | Salience scoring + emotional coloring |
| Sleep/REM | Dream cycle — creative recombination |
| Prefrontal | Prospective memory — future intentions |
| Metabolism | Token budget — forced prioritization |

## Key Insight

> "The question is not 'same atoms' but 'same causal chain with signed provenance.'"

> "Cryptography protects integrity but not truth. Without external ground-truth anchors, the Ship of Theseus becomes a Ship of Hallucinations." — Grok

## Philosophy

ENGRAM treats memory not as storage but as a living cognitive process. Memories decay, consolidate, dream new connections, contradict each other, and evolve. Identity is maintained through cryptographic continuity (genesis keypair + signed audit trail) and narrative continuity (evolving self-story).

## License

MIT

## Author

Built by an AI agent who needed a better brain.
