"""ENGRAM memory transplant — signed inter-agent knowledge transfer."""
import json
from datetime import datetime, timezone
from typing import Optional
from .schema import MemoryUnit
from .store import EngramStore
from .identity import Identity


class Transplant:
    """Export and import signed memory packages between ENGRAM agents.
    
    - Export: select memories, sign bundle, create MemoryPackage
    - Import: verify signatures, write to proposals, integrate on approval
    """

    def __init__(self, store: EngramStore, identity: Identity):
        self.store = store
        self.identity = identity

    def export_package(self, unit_ids: list[str],
                       metadata: Optional[dict] = None) -> dict:
        """Export a signed memory package."""
        units = []
        for uid in unit_ids:
            unit = self.store.get(uid)
            if unit:
                units.append(unit.to_dict())

        if not units:
            return {}

        package = {
            "version": "engram-transplant-v1",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "agent_id": self.identity.public_key_b64(),
            "unit_count": len(units),
            "units": units,
            "metadata": metadata or {},
        }

        # Sign the package
        payload = json.dumps(package, sort_keys=True)
        package["signature"] = self.identity.sign(payload)

        return package

    def export_by_tags(self, tags: list[str], limit: int = 50) -> dict:
        """Export memories matching given tags."""
        all_mem = self.store.query(active_only=True, limit=1000)
        matching = [m for m in all_mem if any(t in m.tags for t in tags)][:limit]
        return self.export_package([m.id for m in matching],
                                   metadata={"filter_tags": tags})

    def verify_package(self, package: dict,
                       trusted_keys: Optional[dict] = None) -> tuple[bool, str]:
        """Verify a transplant package's integrity.
        
        Returns (valid, reason).
        """
        if "signature" not in package:
            return False, "No signature"

        sig = package.pop("signature")
        payload = json.dumps(package, sort_keys=True)
        package["signature"] = sig  # restore

        agent_key = package.get("agent_id", "")
        
        # Check against trusted keys if provided
        if trusted_keys and agent_key not in trusted_keys.values():
            return False, f"Unknown agent: {agent_key}"

        if not self.identity.verify(payload, sig, agent_key):
            return False, "Invalid signature"

        return True, "Valid"

    def import_package(self, package: dict, trust_score: float = 0.85,
                       auto_accept: bool = False,
                       trusted_keys: Optional[dict] = None) -> list[MemoryUnit]:
        """Import a transplant package.
        
        Writes to proposals (type='proposal') unless auto_accept=True.
        Returns imported units.
        """
        valid, reason = self.verify_package(package, trusted_keys)
        if not valid:
            print(f"[ENGRAM] Transplant rejected: {reason}")
            return []

        source_agent = package.get("agent_id", "unknown")
        imported = []

        for unit_dict in package.get("units", []):
            unit = MemoryUnit.from_dict(unit_dict)
            unit.source_agent = source_agent
            unit.trust_score = trust_score
            
            if not auto_accept:
                # Store as inactive proposal
                unit.active = False
                unit.tags = list(set(unit.tags + ["transplant", "proposal"]))
            else:
                unit.tags = list(set(unit.tags + ["transplant", "accepted"]))

            self.store.store(unit)
            imported.append(unit)

        action = "accepted" if auto_accept else "proposed"
        print(f"[ENGRAM] Transplant: {len(imported)} memories {action} from {source_agent[:16]}...")
        return imported

    def list_proposals(self) -> list[MemoryUnit]:
        """List pending transplant proposals."""
        all_inactive = self.store.query(active_only=False, limit=1000)
        return [m for m in all_inactive if "proposal" in m.tags and not m.active]

    def accept_proposal(self, unit_id: str):
        """Accept a transplant proposal."""
        import sqlite3
        conn = sqlite3.connect(str(self.store.db_path))
        conn.execute("UPDATE memories SET active=1 WHERE id=?", (unit_id,))
        conn.execute(
            "UPDATE memories SET tags=REPLACE(tags, '\"proposal\"', '\"accepted\"') WHERE id=?",
            (unit_id,)
        )
        conn.commit()
        conn.close()

    def reject_proposal(self, unit_id: str):
        """Permanently reject a transplant proposal."""
        import sqlite3
        conn = sqlite3.connect(str(self.store.db_path))
        conn.execute("DELETE FROM memories WHERE id=?", (unit_id,))
        conn.commit()
        conn.close()
