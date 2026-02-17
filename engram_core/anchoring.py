"""ENGRAM ground-truth anchoring — prevents bias drift in self-referential LLM loops.

Grok's insight: "Cryptography protects integrity but not truth. Add mandatory external 
ground-truth anchors for any semantic memory above salience 0.85. Without it the Ship 
of Theseus becomes a Ship of Hallucinations."

This module enforces that high-salience semantic memories are periodically validated
against external sources (tool calls, human confirmation, web verification).
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable
from .schema import MemoryUnit
from .store import EngramStore


class Anchoring:
    """Ground-truth validation for high-salience memories.
    
    Prevents compounding bias drift in the consolidation→dream→narrative loop.
    Any semantic memory with salience > threshold must be externally anchored
    within a configurable window, or it gets demoted.
    """

    def __init__(self, store: EngramStore,
                 salience_threshold: float = 0.85,
                 anchor_window_days: int = 7,
                 demotion_factor: float = 0.6):
        self.store = store
        self.salience_threshold = salience_threshold
        self.anchor_window_days = anchor_window_days
        self.demotion_factor = demotion_factor

    def find_unanchored(self) -> list[MemoryUnit]:
        """Find high-salience semantic memories that lack external validation."""
        all_semantic = self.store.query(type="semantic", active_only=True,
                                        min_salience=self.salience_threshold, limit=500)
        now = datetime.now(timezone.utc)
        unanchored = []

        for m in all_semantic:
            # Check if anchored (has 'anchored' or 'human_verified' or 'tool_verified' tag)
            anchor_tags = {"anchored", "human_verified", "tool_verified", "external_verified"}
            if anchor_tags.intersection(set(m.tags)):
                continue

            # Check age
            try:
                ts = datetime.fromisoformat(m.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age = now - ts
            except:
                age = timedelta(days=999)

            if age > timedelta(days=self.anchor_window_days):
                unanchored.append(m)

        return unanchored

    def demote_unanchored(self, dry_run: bool = False) -> list[str]:
        """Demote high-salience memories that haven't been anchored.
        
        Returns list of demoted memory ids.
        """
        unanchored = self.find_unanchored()
        demoted = []

        for m in unanchored:
            if not dry_run:
                import sqlite3
                new_salience = m.salience * self.demotion_factor
                conn = sqlite3.connect(str(self.store.db_path))
                conn.execute(
                    "UPDATE memories SET salience=? WHERE id=?",
                    (new_salience, m.id)
                )
                # Add warning tag
                tags = m.tags + ["unanchored_demoted"]
                conn.execute(
                    "UPDATE memories SET tags=? WHERE id=?",
                    (str(tags), m.id)
                )
                conn.commit()
                conn.close()
            demoted.append(m.id)

        if demoted:
            print(f"[ENGRAM] Anchoring: demoted {len(demoted)} unanchored high-salience memories")
        return demoted

    def anchor(self, unit_id: str, method: str = "human_verified",
               evidence: Optional[str] = None):
        """Mark a memory as externally anchored/verified.
        
        Methods: 'human_verified', 'tool_verified', 'external_verified'
        """
        import sqlite3
        conn = sqlite3.connect(str(self.store.db_path))
        
        # Get current tags
        row = conn.execute("SELECT tags FROM memories WHERE id=?", (unit_id,)).fetchone()
        if row:
            import json
            try:
                tags = json.loads(row[0]) if row[0] else []
            except:
                tags = []
            tags.append(method)
            if "unanchored_demoted" in tags:
                tags.remove("unanchored_demoted")
            conn.execute(
                "UPDATE memories SET tags=? WHERE id=?",
                (json.dumps(tags), unit_id)
            )
            conn.commit()
        conn.close()

    def audit_report(self) -> dict:
        """Generate anchoring audit report."""
        all_semantic = self.store.query(type="semantic", active_only=True, limit=10000)
        high_salience = [m for m in all_semantic if m.salience >= self.salience_threshold]
        
        anchor_tags = {"anchored", "human_verified", "tool_verified", "external_verified"}
        anchored = [m for m in high_salience if anchor_tags.intersection(set(m.tags))]
        unanchored = self.find_unanchored()

        return {
            "total_semantic": len(all_semantic),
            "high_salience": len(high_salience),
            "anchored": len(anchored),
            "unanchored": len(unanchored),
            "anchor_rate": round(len(anchored) / max(len(high_salience), 1) * 100, 1),
            "risk_level": "HIGH" if len(unanchored) > 10 else "MEDIUM" if len(unanchored) > 3 else "LOW",
        }
