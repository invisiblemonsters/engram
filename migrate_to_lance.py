"""One-shot migration from SQLite+numpy to LanceDB.
Reads all memories from old store, writes to new LanceStore.
Old data kept as backup.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from engram_core.store import EngramStore as OldStore
from engram_core.lance_store import LanceStore

def migrate():
    old_data_dir = os.path.join("engram_data", "store")
    new_data_dir = os.path.join("engram_data", "lance_store")

    if not os.path.exists(old_data_dir):
        print(f"Old store not found at {old_data_dir}")
        return

    print("Loading old SQLite store...")
    old = OldStore(old_data_dir)
    
    # Get ALL memories (active and inactive)
    all_memories = old.query(active_only=False, limit=100000)
    print(f"Found {len(all_memories)} memories in old store")

    if not all_memories:
        print("Nothing to migrate!")
        return

    print("Creating LanceDB store...")
    new = LanceStore(new_data_dir)

    migrated = 0
    errors = 0
    for unit in all_memories:
        try:
            # Ensure embedding exists
            if not unit.embedding:
                # Load from old store's vector cache
                import numpy as np
                vec = old.vectors.get(unit.id)
                if vec is not None:
                    unit.embedding = vec.tolist()
                else:
                    unit.embedding = [0.0] * 384  # placeholder
            
            new.store(unit)
            migrated += 1
            if migrated % 50 == 0:
                print(f"  Migrated {migrated}/{len(all_memories)}...")
        except Exception as e:
            print(f"  Error migrating {unit.id}: {e}")
            errors += 1

    print(f"\nMigration complete!")
    print(f"  Migrated: {migrated}")
    print(f"  Errors: {errors}")
    print(f"  New store: {new_data_dir}")
    print(f"\nOld store preserved at: {old_data_dir}")
    print(f"To switch: update Engram.__init__ to use LanceStore")

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    migrate()
