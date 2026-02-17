"""Batch consolidate all episodic memories into semantic knowledge.
Run once to bootstrap the semantic layer. ~8-12 min on CPU + NVIDIA API."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
from engram_core.engram import Engram

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")

print("[CONSOLIDATE] Starting full batch consolidation...")

e = Engram(
    data_dir=DATA_DIR,
    llm_base_url="https://integrate.api.nvidia.com/v1",
    llm_model="meta/llama-3.3-70b-instruct"
)

s = e.status()
print(f"[CONSOLIDATE] Total: {s['memories']['total']}, Episodic: {s['memories']['episodic']}, Semantic: {s['memories']['semantic']}")
print(f"[CONSOLIDATE] LLM active: {e.consolidator.llm is not None}")

if not e.consolidator.llm:
    print("[CONSOLIDATE] ERROR: No LLM backend available. Cannot consolidate.")
    sys.exit(1)

# Get all unconsolidated episodic memories
unconsolidated = e.consolidator.check_wakeup()
print(f"[CONSOLIDATE] Unconsolidated episodes: {len(unconsolidated)}")

if not unconsolidated:
    print("[CONSOLIDATE] Nothing to consolidate. Running dream cycle instead...")
    insights = e.dream()
    print(f"[CONSOLIDATE] Dreams: {len(insights)} insights")
    sys.exit(0)

# Batch consolidate in groups of 10 (Nemotron handles small batches better)
batch_size = 12
total_semantic = 0
total_batches = (len(unconsolidated) + batch_size - 1) // batch_size

for i in range(0, len(unconsolidated), batch_size):
    batch = unconsolidated[i:i+batch_size]
    batch_num = i // batch_size + 1
    print(f"\n[CONSOLIDATE] Batch {batch_num}/{total_batches} ({len(batch)} episodes)...")
    
    try:
        new_semantic = e.consolidator.consolidate_batch(batch)
        total_semantic += len(new_semantic)
        print(f"[CONSOLIDATE] Batch {batch_num}: {len(new_semantic)} semantic units created")
        
        for ns in new_semantic[:3]:  # Show first 3
            print(f"  -> {ns.content[:100]}...")
        
        # Small delay to avoid rate limiting
        time.sleep(2)
    except Exception as ex:
        print(f"[CONSOLIDATE] Batch {batch_num} FAILED: {ex}")
        continue

print(f"\n[CONSOLIDATE] Consolidation complete: {total_semantic} semantic units from {len(unconsolidated)} episodes")

# Run metabolism
print("[CONSOLIDATE] Running metabolism...")
archived = e.metabolism.metabolize()
print(f"[CONSOLIDATE] Archived: {len(archived)} low-utility memories")

# Now try dreaming
print("[CONSOLIDATE] Running dream cycle...")
insights = e.dream()
print(f"[CONSOLIDATE] Dreams: {len(insights)} insights")
for ins in insights:
    print(f"  [insight] {ins.content[:120]}...")

# Final status
s = e.status()
print(f"\n[CONSOLIDATE] Final: {s['memories']['total']} total, {s['memories']['episodic']} episodic, {s['memories']['semantic']} semantic, {s['memories']['insight']} insights")
