"""ENGRAM backup utility. Creates timestamped snapshot of engram_data/."""
import shutil
import os
from datetime import datetime
from pathlib import Path

def backup(data_dir: str = "engram_data", backup_root: str = "engram_backups"):
    """Create a timestamped backup of the ENGRAM data directory."""
    src = Path(data_dir)
    if not src.exists():
        print(f"[ENGRAM] No data dir at {src}")
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = Path(backup_root) / f"engram_backup_{ts}"
    dst.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(src, dst)
    
    # Prune old backups (keep last 5)
    backups = sorted(Path(backup_root).glob("engram_backup_*"))
    while len(backups) > 5:
        old = backups.pop(0)
        shutil.rmtree(old)
        print(f"[ENGRAM] Pruned old backup: {old.name}")

    size_mb = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file()) / (1024*1024)
    print(f"[ENGRAM] Backup created: {dst} ({size_mb:.1f} MB)")
    return str(dst)

if __name__ == "__main__":
    import sys
    os.chdir(os.path.dirname(__file__) or ".")
    backup()
