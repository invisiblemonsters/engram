"""Test ENGRAM against real imported memories."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from engram_core.engram import Engram

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")

def test_recall():
    e = Engram(data_dir=DATA_DIR)
    
    queries = [
        "What do I know about AIP protocol?",
        "How does Lightning payment work?",
        "What books have I written?",
        "What happened with bug bounties on huntr?",
        "What is my relationship with Grok?",
        "How does memory work?",
        "What wallets do I have?",
        "What did I build yesterday?",
    ]
    
    for q in queries:
        results = e.recall(q, top_k=3)
        print(f"\n=== {q} ===")
        for r in results[:3]:
            preview = r.content[:120].replace('\n', ' ').encode('ascii', 'replace').decode()
            print(f"  [{r.type}] (s={r.salience:.1f}) {preview}...")

    print(f"\n--- Status ---")
    s = e.status()
    print(f"Total: {s['memories']['total']}")
    print(f"Episodic: {s['memories']['episodic']}")
    print(f"Semantic: {s['memories']['semantic']}")
    print(f"Embedder: {s['embedder']}")
    print(f"Identity: {s['identity'][:24]}...")

if __name__ == "__main__":
    test_recall()
