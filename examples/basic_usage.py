"""Basic ENGRAM usage — no LLM required."""
from engram import Engram

e = Engram(data_dir="./example_data")

# Store memories
e.remember("Learned about vector databases today", type="episodic", tags=["learning"], salience=0.7)
e.remember("LanceDB is fast for hybrid search", type="semantic", tags=["tech"], salience=0.8)

# Recall
results = e.recall("vector databases", top_k=5)
for m in results:
    print(f"[{m.type}] {m.content} (salience={m.salience})")

# Status
print(e.status())
