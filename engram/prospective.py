"""ENGRAM prospective memory — context-triggered future intentions."""
from typing import Optional, Callable
from .types import MemoryUnit


class Prospective:
    def __init__(self, store, embedder, llm_fn: Optional[Callable] = None,
                 trigger_threshold: float = 0.7):
        self.store = store
        self.embedder = embedder
        self.llm = llm_fn
        self.trigger_threshold = trigger_threshold

    def create(self, trigger_condition: str, action: dict,
               content: Optional[str] = None, salience: float = 0.8) -> MemoryUnit:
        if not content:
            content = f"WHEN: {trigger_condition} -> THEN: {action.get('message', str(action))}"
        emb = self.embedder.embed(trigger_condition)
        unit = MemoryUnit(
            content=content, type="prospective", embedding=emb,
            salience=salience, trigger_condition=trigger_condition,
            action=action, tags=["prospective", "active"],
        )
        self.store.store(unit)
        return unit

    def check_triggers(self, current_context: str) -> list[tuple[MemoryUnit, float]]:
        prospectives = self.store.query(type="prospective", active_only=True, limit=100)
        if not prospectives:
            return []

        context_emb = self.embedder.embed(current_context)
        triggered = []

        for p in prospectives:
            if not p.trigger_condition:
                continue
            if p.embedding:
                sim = self._cosine(context_emb, p.embedding)
            else:
                trigger_emb = self.embedder.embed(p.trigger_condition)
                sim = self._cosine(context_emb, trigger_emb)

            if sim >= self.trigger_threshold:
                triggered.append((p, sim))

        return triggered

    def fire(self, unit: MemoryUnit) -> dict:
        self.store.deactivate(unit.id)
        return unit.action or {}

    def list_active(self) -> list[MemoryUnit]:
        return self.store.query(type="prospective", active_only=True, limit=100)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na > 0 and nb > 0 else 0
