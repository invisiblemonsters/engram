"""ENGRAM memory metabolism — token budget enforcement and natural forgetting."""
from datetime import datetime, timezone


class Metabolism:
    def __init__(self, store, max_tokens: int = 2_000_000, earn_per_action: int = 50_000):
        self.store = store
        self.max_tokens = max_tokens
        self.earn_per_action = earn_per_action
        self._earned_tokens = 0

    def compute_costs(self):
        now = datetime.now(timezone.utc)
        memories = self.store.query(active_only=True, limit=10000)
        for m in memories:
            try:
                ts = datetime.fromisoformat(m.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_days = max((now - ts).total_seconds() / 86400, 0)
            except Exception:
                age_days = 1
            m.compute_maintenance_cost(age_days)
            self.store.update_unit(m)

    def total_cost(self) -> float:
        costs = self.store.all_active_costs()
        return sum(c[1] for c in costs)

    def effective_budget(self) -> float:
        return self.max_tokens + self._earned_tokens

    def earn(self, multiplier: float = 1.0):
        self._earned_tokens += int(self.earn_per_action * multiplier)

    def metabolize(self, dry_run: bool = False) -> list[str]:
        self.compute_costs()
        total = self.total_cost()
        budget = self.effective_budget()
        if total <= budget:
            return []
        excess = total - budget
        archived = []
        costs = self.store.all_active_costs()
        costs.sort(key=lambda x: x[2])
        for uid, mcost, utility in costs:
            if excess <= 0:
                break
            if utility > 5.0:
                continue
            if not dry_run:
                self.store.deactivate(uid)
            archived.append(uid)
            excess -= mcost
        return archived

    def status(self) -> dict:
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
