"""Recompute all embeddings with current model (bge-small-en-v1.5).
Processes in batches to avoid OOM.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from engram_core.embedder import Embedder
from engram_core.lance_store import LanceStore

def main():
    store = LanceStore("engram_data/lance_store")
    embedder = Embedder()
    
    # Get all IDs first, then process one at a time
    all_memories = store.query(active_only=False, limit=100000)
    total = len(all_memories)
    print(f"Recomputing embeddings for {total} memories...", flush=True)
    
    updated = 0
    for i, unit in enumerate(all_memories):
        new_emb = embedder.embed(unit.content)
        if new_emb:
            unit.embedding = new_emb
            store.store(unit)
            updated += 1
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{total}...", flush=True)
    
    print(f"Done. Recomputed {updated}/{total} embeddings.", flush=True)

if __name__ == "__main__":
    main()
