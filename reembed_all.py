"""Recompute all embeddings with current model (bge-small-en-v1.5).
Run after embedding model swap to ensure consistent vector space.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from engram_core.embedder import Embedder
from engram_core.lance_store import LanceStore

def main():
    store = LanceStore("engram_data/lance_store")
    embedder = Embedder()
    
    all_memories = store.query(active_only=False, limit=100000)
    print(f"Recomputing embeddings for {len(all_memories)} memories...")
    
    updated = 0
    for i, unit in enumerate(all_memories):
        new_emb = embedder.embed(unit.content)
        if new_emb:
            unit.embedding = new_emb
            store.store(unit)
            updated += 1
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(all_memories)}...")
    
    print(f"Done. Recomputed {updated}/{len(all_memories)} embeddings.")

if __name__ == "__main__":
    main()
