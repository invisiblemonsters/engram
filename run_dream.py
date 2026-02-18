"""Run dream cycle + metabolism on the consolidated memory store."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from engram_core.engram import Engram

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")

print("[DREAM] Initializing ENGRAM...")
e = Engram(
    data_dir=DATA_DIR,
    llm_base_url="https://integrate.api.nvidia.com/v1",
    llm_model="meta/llama-3.3-70b-instruct"
)

s = e.status()
print(f"[DREAM] Memories: {s['memories']['total']} total, {s['memories']['semantic']} semantic, {s['memories']['insight']} insights")

# Run metabolism first
print("\n[DREAM] Running metabolism...")
t = time.time()
archived = e.metabolism.metabolize()
print(f"[DREAM] Metabolism: {len(archived)} low-utility memories archived ({time.time()-t:.1f}s)")

# Run dream cycle
print("\n[DREAM] Running dream cycle...")
t = time.time()
insights = e.dream()
print(f"[DREAM] Dream cycle: {len(insights)} insights generated ({time.time()-t:.1f}s)")
for i, ins in enumerate(insights):
    print(f"  [{i+1}] {ins.content[:200]}...")

# Run self-evolution
print("\n[DREAM] Running self-evolution...")
t = time.time()
from engram_core.self_evolve import SelfEvolver
evolver = SelfEvolver(e, e.dreamer.llm)
evo_results = evolver.evolve()
print(f"[DREAM] Self-evolution: {evo_results['proposed']} proposals ({time.time()-t:.1f}s)")

# Final status
s = e.status()
print(f"\n[DREAM] Final: {s['memories']['total']} total, {s['memories']['episodic']} episodic, {s['memories']['semantic']} semantic, {s['memories']['insight']} insights")

# Regenerate MEMORY.md hot cache from ENGRAM
print("\n[DREAM] Regenerating MEMORY.md hot cache...")
t = time.time()
from engram_hot_cache import generate_hot_cache
generate_hot_cache()
print(f"[DREAM] Hot cache updated ({time.time()-t:.1f}s)")
