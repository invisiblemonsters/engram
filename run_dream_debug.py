"""Debug dream cycle — show what's being filtered."""
import sys, os, json, random, time
sys.path.insert(0, os.path.dirname(__file__))
from engram_core.engram import Engram

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")
e = Engram(data_dir=DATA_DIR, llm_base_url="https://integrate.api.nvidia.com/v1", llm_model="meta/llama-3.3-70b-instruct")

# Manually run dream with debug
all_semantic = e.store.query(type="semantic", active_only=True, limit=500)
print(f"Semantic memories: {len(all_semantic)}")

# Sample 5
weights = [m.salience + 0.1 for m in all_semantic]
total = sum(weights)
weights = [w / total for w in weights]
selected = random.sample(all_semantic, min(5, len(all_semantic)))

print(f"\nSampled {len(selected)} memories:")
for s in selected:
    print(f"  - {s.content[:100]}")

prompt = f"""You are a creative insight generator. Given these {len(selected)} memories from an AI agent,
find 1-3 SURPRISING, non-obvious connections between them.

Memories:
{json.dumps([{"id": m.id, "content": m.content[:200], "tags": m.tags} for m in selected], indent=2)}

Rules:
- Connections must be genuinely novel, not obvious restatements
- Each insight should link at least 2 of the memories
- Rate your own novelty 0-1 (be harsh — only truly surprising gets >0.75)

Output ONLY a valid JSON array:
[{{"insight": "the surprising connection", "links": ["id1", "id2"], "novelty_score": 0.8, "tags": ["tag"]}}]"""

print("\nCalling LLM...")
t = time.time()
result = e.consolidator.llm(prompt)
print(f"LLM response ({time.time()-t:.1f}s):\n{result[:1000]}")

# Parse
start = result.find("[")
end = result.rfind("]") + 1
if start >= 0 and end > 0:
    insights = json.loads(result[start:end])
    print(f"\nParsed {len(insights)} insights:")
    for ins in insights:
        content = ins.get("insight", "")
        score = ins.get("novelty_score", 0)
        print(f"\n  Score: {score}")
        print(f"  Content: {content[:200]}")
        
        # Check novelty
        emb = e.embedder.embed(content)
        nearest = e.store.vector_search(emb, top_k=3)
        if nearest:
            print(f"  Nearest similarities: {[f'{s:.3f}' for _, s in nearest]}")
            threshold = 1 - 0.55  # = 0.45
            print(f"  Threshold (reject if > {threshold}): {'REJECTED' if nearest[0][1] > threshold else 'ACCEPTED'}")
            # With relaxed threshold (0.35 = novelty 0.65)
            print(f"  Relaxed threshold 0.60: {'REJECTED' if nearest[0][1] > 0.60 else 'ACCEPTED'}")
