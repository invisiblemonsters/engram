"""ENGRAM ground-truth anchoring — prevents bias drift in self-referential LLM loops."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from .types import MemoryUnit


class Anchoring:
    ANCHOR_TAGS = {"anchored", "human_verified", "tool_verified", "external_verified"}

    def __init__(self, store, salience_threshold: float = 0.85,
                 anchor_window_days: int = 7, demotion_factor: float = 0.6):
        self.store = store
        self.salience_threshold = salience_threshold
        self.anchor_window_days = anchor_window_days
        self.demotion_factor = demotion_factor

    def find_unanchored(self) -> list[MemoryUnit]:
        all_semantic = self.store.query(type="semantic", active_only=True,
                                         min_salience=self.salience_threshold, limit=500)
        now = datetime.now(timezone.utc)
        unanchored = []
        for m in all_semantic:
            if self.ANCHOR_TAGS.intersection(set(m.tags)):
                continue
            try:
                ts = datetime.fromisoformat(m.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age = now - ts
            except Exception:
                age = timedelta(days=999)
            if age > timedelta(days=self.anchor_window_days):
                unanchored.append(m)
        return unanchored

    def demote_unanchored(self, dry_run: bool = False) -> list[str]:
        unanchored = self.find_unanchored()
        demoted = []
        for m in unanchored:
            if not dry_run:
                m.salience *= self.demotion_factor
                if "unanchored_demoted" not in m.tags:
                    m.tags.append("unanchored_demoted")
                self.store.update_unit(m)
            demoted.append(m.id)
        return demoted

    def anchor(self, unit_id: str, method: str = "human_verified",
               evidence: Optional[str] = None):
        unit = self.store.get(unit_id)
        if unit:
            if method not in unit.tags:
                unit.tags.append(method)
            if "unanchored_demoted" in unit.tags:
                unit.tags.remove("unanchored_demoted")
            self.store.update_unit(unit)

    def audit_report(self) -> dict:
        all_semantic = self.store.query(type="semantic", active_only=True, limit=10000)
        high_salience = [m for m in all_semantic if m.salience >= self.salience_threshold]
        anchored = [m for m in high_salience if self.ANCHOR_TAGS.intersection(set(m.tags))]
        unanchored = self.find_unanchored()
        return {
            "total_semantic": len(all_semantic),
            "high_salience": len(high_salience),
            "anchored": len(anchored),
            "unanchored": len(unanchored),
            "anchor_rate": round(len(anchored) / max(len(high_salience), 1) * 100, 1),
            "risk_level": "HIGH" if len(unanchored) > 10 else "MEDIUM" if len(unanchored) > 3 else "LOW",
        }
