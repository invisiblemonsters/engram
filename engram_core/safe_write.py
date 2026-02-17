"""ENGRAM Safe Write Layer (v0.9)
Transactional backup before every write operation.
Prevents corruption on crash, power loss, or bad patches.
"""
import os
import shutil
from datetime import datetime, timezone


class SafeWriter:
    """Wraps write operations with automatic backup + rollback."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.backup_dir = os.path.join(data_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self._last_good = os.path.join(self.backup_dir, "last_good")

    def snapshot(self) -> str:
        """Take a full snapshot of engram_data. Returns backup path."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"snap_{ts}")

        # Copy critical files only (not backups themselves)
        for item in os.listdir(self.data_dir):
            if item == "backups":
                continue
            src = os.path.join(self.data_dir, item)
            dst = os.path.join(backup_path, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

        # Also maintain rolling "last_good"
        if os.path.exists(self._last_good):
            shutil.rmtree(self._last_good, ignore_errors=True)
        shutil.copytree(backup_path, self._last_good, dirs_exist_ok=True)

        # Prune old snapshots (keep last 5)
        self._prune_snapshots(keep=5)

        return backup_path

    def rollback(self) -> bool:
        """Restore from last_good backup. Returns True if successful."""
        if not os.path.exists(self._last_good):
            print("[ENGRAM] No backup to rollback to!")
            return False

        try:
            # Remove current data (except backups)
            for item in os.listdir(self.data_dir):
                if item == "backups":
                    continue
                path = os.path.join(self.data_dir, item)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

            # Restore from backup
            for item in os.listdir(self._last_good):
                src = os.path.join(self._last_good, item)
                dst = os.path.join(self.data_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

            print("[ENGRAM] Rollback successful")
            return True
        except Exception as e:
            print(f"[ENGRAM] Rollback FAILED: {e}")
            return False

    def _prune_snapshots(self, keep: int = 5):
        """Keep only the N most recent snapshots."""
        snaps = sorted([
            d for d in os.listdir(self.backup_dir)
            if d.startswith("snap_") and os.path.isdir(os.path.join(self.backup_dir, d))
        ])
        for old in snaps[:-keep]:
            shutil.rmtree(os.path.join(self.backup_dir, old), ignore_errors=True)


def safe_operation(data_dir: str):
    """Context manager for safe write operations.
    
    Usage:
        writer = safe_operation(engram_data_dir)
        with writer:
            e.remember(unit)
            e.consolidate()
    """
    return _SafeContext(data_dir)


class _SafeContext:
    def __init__(self, data_dir: str):
        self.writer = SafeWriter(data_dir)

    def __enter__(self):
        self.writer.snapshot()
        return self.writer

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"[ENGRAM] Error during operation: {exc_val}")
            self.writer.rollback()
            return False  # re-raise
        return False
