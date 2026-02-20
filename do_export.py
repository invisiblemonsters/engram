import sys, json, os

sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")

from engram_core.lance_store import LanceStore
from engram_core.transplant import Transplant
from engram_core.identity import Identity
from engram_core.store import EngramStore

# Load identity and store
identity = Identity(os.path.join(DATA_DIR, "identity"))
lance = LanceStore(os.path.join(DATA_DIR, "lance_store"))

# We need an EngramStore wrapper - check what transplant expects
# Let's just use the Engram class directly like transplant_demo does
from engram_core.engram import Engram

e = Engram(data_dir=DATA_DIR)

df = lance.table.to_pandas()
print(f"Total memories: {len(df)}")

# Export 100 memories
all_ids = df["id"].tolist()[:100]

package = e.transplant.export_package(all_ids, metadata={
    "topic": "full onboarding package for PicoClaw",
    "source_agent": "Metatron",
    "source_npub": "npub182m9y3qyd7wfm9sew59yk7f8wm9mhwhme2gfjfyq44djm6wfswtsumxtyk",
})

outpath = os.path.join(DATA_DIR, "memory_packages", "metatron-to-picoclaw-full.json")
with open(outpath, "w") as f:
    json.dump(package, f, indent=2, default=str)

mem_count = len(package.get("units", []))
print(f"Exported {mem_count} memories to {outpath}")
