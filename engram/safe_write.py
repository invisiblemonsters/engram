"""ENGRAM Safe Write Layer — transactional backup before every write operation."""
import shutil
from pathlib import Path
from datetime import datetime, timezone


class SafeWriter:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._last_good = self.backup_dir / "last_good"

    def snapshot(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"snap_{ts}"

        for item in self.data_dir.iterdir():
            if item.name == "backups":
                continue
            dst = backup_path / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)

        if self._last_good.exists():
            shutil.rmtree(self._last_good, ignore_errors=True)
        shutil.copytree(backup_path, self._last_good, dirs_exist_ok=True)
        self._prune_snapshots(keep=5)
        return str(backup_path)

    def rollback(self) -> bool:
        if not self._last_good.exists():
            return False
        try:
            for item in self.data_dir.iterdir():
                if item.name == "backups":
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            for item in self._last_good.iterdir():
                dst = self.data_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dst)
            return True
        except Exception:
            return False

    def _prune_snapshots(self, keep: int = 5):
        snaps = sorted([d for d in self.backup_dir.iterdir()
                         if d.name.startswith("snap_") and d.is_dir()])
        for old in snaps[:-keep]:
            shutil.rmtree(old, ignore_errors=True)
