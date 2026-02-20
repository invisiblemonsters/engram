"""ENGRAM memory transplant — signed inter-agent knowledge transfer."""
import json
from datetime import datetime, timezone
from typing import Optional
from .types import MemoryUnit


class Transplant:
    def __init__(self, store, identity):
        self.store = store
        self.identity = identity

    def export_package(self, unit_ids: list[str], metadata: Optional[dict] = None) -> dict:
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
        payload = json.dumps(package, sort_keys=True)
        package["signature"] = self.identity.sign(payload)
        return package

    def export_by_tags(self, tags: list[str], limit: int = 50) -> dict:
        all_mem = self.store.query(active_only=True, limit=1000)
        matching = [m for m in all_mem if any(t in m.tags for t in tags)][:limit]
        return self.export_package([m.id for m in matching], metadata={"filter_tags": tags})

    def verify_package(self, package: dict, trusted_keys: Optional[dict] = None) -> tuple[bool, str]:
        if "signature" not in package:
            return False, "No signature"
        sig = package.pop("signature")
        payload = json.dumps(package, sort_keys=True)
        package["signature"] = sig
        agent_key = package.get("agent_id", "")
        if trusted_keys and agent_key not in trusted_keys.values():
            return False, f"Unknown agent: {agent_key}"
        if not self.identity.verify(payload, sig, agent_key):
            return False, "Invalid signature"
        return True, "Valid"

    def import_package(self, package: dict, trust_score: float = 0.85,
                       auto_accept: bool = False,
                       trusted_keys: Optional[dict] = None) -> list[MemoryUnit]:
        valid, reason = self.verify_package(package, trusted_keys)
        if not valid:
            return []
        source_agent = package.get("agent_id", "unknown")
        imported = []
        for unit_dict in package.get("units", []):
            unit = MemoryUnit.from_dict(unit_dict)
            unit.source_agent = source_agent
            unit.trust_score = trust_score
            if not auto_accept:
                unit.active = False
                unit.tags = list(set(unit.tags + ["transplant", "proposal"]))
            else:
                unit.tags = list(set(unit.tags + ["transplant", "accepted"]))
            self.store.store(unit)
            imported.append(unit)
        return imported
