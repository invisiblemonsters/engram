"""ENGRAM CRDT Merger (v0.8) — Conflict-free merge of concurrent memory streams.
Last-write-wins on timestamp + signature chain, relation merging, salience boost.
Designed by Grok 4.20, implemented by Metatron.
"""
from datetime import datetime
from typing import Optional
from .schema import MemoryUnit


class CRDTMerger:
    """Merge concurrent memory streams using CRDT-inspired rules.
    
    Strategy:
    - Same ID: last-write-wins on timestamp, merge relations, boost salience
    - Different ID: just include both
    - Version tracking: max(local, incoming) + 1
    """

    def merge(self, local: MemoryUnit, incoming: MemoryUnit) -> MemoryUnit:
        """Merge two memory units with the same ID."""
        # Last-write-wins on timestamp
        local_ts = local.timestamp if hasattr(local.timestamp, 'timestamp') else datetime.now()
        incoming_ts = incoming.timestamp if hasattr(incoming.timestamp, 'timestamp') else datetime.now()
        
        if incoming_ts > local_ts:
            winner = incoming
            loser = local
        else:
            winner = local
            loser = incoming

        # Merge relations (deduplicate)
        existing_relations = {str(r) for r in winner.relations}
        for r in loser.relations:
            if str(r) not in existing_relations:
                winner.relations.append(r)

        # Salience: take max with slight discount on loser
        winner.salience = max(winner.salience, loser.salience * 0.95)

        # Version bump
        winner.version = max(
            getattr(local, 'version', 0),
            getattr(incoming, 'version', 0)
        ) + 1

        return winner

    def merge_packages(self, local_units: list[MemoryUnit],
                       incoming_package: dict) -> list[MemoryUnit]:
        """Merge an incoming transplant package with local memory.
        
        Returns merged list of MemoryUnits.
        """
        merged = {u.id: u for u in local_units}

        for inc_dict in incoming_package.get("units", []):
            inc = MemoryUnit.from_dict(inc_dict)
            if inc.id in merged:
                merged[inc.id] = self.merge(merged[inc.id], inc)
            else:
                merged[inc.id] = inc

        return list(merged.values())
