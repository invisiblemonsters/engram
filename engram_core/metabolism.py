"""ENGRAM memory metabolism — token budget enforcement and natural forgetting."""
from datetime import datetime, timezone
from .store import EngramStore


class Metabolism:
    """Metabolic pressure on memory: maintenance costs, budget enforcement, pruning.
    
    Each memory has a cost. Agent has a budget. Over budget = forced forgetting.
    Agent earns capacity through useful work.
    """

    def __init__(self, store: EngramStore, max_tokens: int = 2_000_000,
                 earn_per_action: int = 50_000):
        self.store = store
        self.max_tokens = max_tokens
        self.earn_per_action = earn_per_action
        self._earned_tokens = 0

    def compute_costs(self):
        """Recompute maintenance costs for all active memories."""
        now = datetime.now(timezone.utc)
        memories = self.store.query(active_only=True, limit=10000)
        
        for m in memories:
            try:
                ts = datetime.fromisoformat(m.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_days = max((now - ts).total_seconds() / 86400, 0)
            except:
                age_days = 1
            
            m.compute_maintenance_cost(age_days)
            # Update in DB (lightweight — just the cost field)
            import sqlite3
            conn = sqlite3.connect(str(self.store.db_path))
            conn.execute(
                "UPDATE memories SET maintenance_cost=? WHERE id=?",
                (m.maintenance_cost, m.id)
            )
            conn.commit()
            conn.close()

    def total_cost(self) -> float:
        """Total maintenance cost of all active memories."""
        costs = self.store.all_active_costs()
        return sum(c[1] for c in costs)

    def effective_budget(self) -> float:
        """Budget including earned tokens."""
        return self.max_tokens + self._earned_tokens

    def earn(self, multiplier: float = 1.0):
        """Agent performed useful work — earn token capacity."""
        self._earned_tokens += int(self.earn_per_action * multiplier)

    def metabolize(self, dry_run: bool = False) -> list[str]:
        """Enforce budget. Archive low-utility memories if over budget.
        
        Returns list of archived memory ids.
        """
        self.compute_costs()
        total = self.total_cost()
        budget = self.effective_budget()

        if total <= budget:
            return []

        excess = total - budget
        archived = []

        # Get memories sorted by utility (lowest first)
        costs = self.store.all_active_costs()
        # costs is [(id, maintenance_cost, utility_score)]
        costs.sort(key=lambda x: x[2])  # sort by utility ascending

        for uid, mcost, utility in costs:
            if excess <= 0:
                break
            if utility > 5.0:  # don't prune high-utility memories
                continue
            
            if not dry_run:
                self.store.deactivate(uid)
            archived.append(uid)
            excess -= mcost

        if archived:
            print(f"[ENGRAM] Metabolism: archived {len(archived)} low-utility memories "
                  f"(total_cost={total:.0f}, budget={budget:.0f})")
        return archived

    def status(self) -> dict:
        """Return metabolism status."""
        total = self.total_cost()
        budget = self.effective_budget()
        active = self.store.count(active_only=True)
        return {
            "active_memories": active,
            "total_cost": round(total, 1),
            "budget": round(budget, 1),
            "utilization": round(total / budget * 100, 1) if budget > 0 else 0,
            "earned_tokens": self._earned_tokens,
            "headroom": round(budget - total, 1),
        }
