"""ENGRAM prospective memory — context-triggered future intentions."""
from typing import Optional, Callable
from .schema import MemoryUnit
from .store import EngramStore
from .embedder import Embedder


class Prospective:
    """Context-triggered prospective memory.
    
    'When I next see X, do Y' — not cron-based, but context-activated.
    On every context update, scan for matching trigger conditions.
    """

    def __init__(self, store: EngramStore, embedder: Embedder,
                 llm_fn: Optional[Callable] = None,
                 trigger_threshold: float = 0.7):
        self.store = store
        self.embedder = embedder
        self.llm = llm_fn
        self.trigger_threshold = trigger_threshold

    def create(self, trigger_condition: str, action: dict,
               content: Optional[str] = None, salience: float = 0.8) -> MemoryUnit:
        """Create a prospective memory.
        
        Args:
            trigger_condition: Natural language trigger ("When I see a huntr notification")
            action: What to do {"type": "remind", "message": "Check the bounty status"}
            content: Optional description
        """
        if not content:
            content = f"WHEN: {trigger_condition} → THEN: {action.get('message', str(action))}"

        emb = self.embedder.embed(trigger_condition)
        
        unit = MemoryUnit(
            content=content,
            type="prospective",
            embedding=emb,
            salience=salience,
            trigger_condition=trigger_condition,
            action=action,
            tags=["prospective", "active"],
        )
        self.store.store(unit)
        print(f"[ENGRAM] Prospective memory created: {trigger_condition[:60]}...")
        return unit

    def check_triggers(self, current_context: str) -> list[tuple[MemoryUnit, float]]:
        """Check if any prospective memories are triggered by current context.
        
        Returns list of (memory, similarity_score) for triggered memories.
        """
        prospectives = self.store.query(type="prospective", active_only=True, limit=100)
        if not prospectives:
            return []

        context_emb = self.embedder.embed(current_context)
        triggered = []

        for p in prospectives:
            if not p.trigger_condition:
                continue
            
            # Use stored embedding for trigger
            if p.embedding:
                from .retriever import Retriever
                sim = sum(a*b for a, b in zip(context_emb, p.embedding))
                norm_a = sum(a*a for a in context_emb) ** 0.5
                norm_b = sum(b*b for b in p.embedding) ** 0.5
                if norm_a > 0 and norm_b > 0:
                    sim = sim / (norm_a * norm_b)
                else:
                    sim = 0
            else:
                trigger_emb = self.embedder.embed(p.trigger_condition)
                sim = sum(a*b for a, b in zip(context_emb, trigger_emb))
                norm_a = sum(a*a for a in context_emb) ** 0.5
                norm_b = sum(b*b for b in trigger_emb) ** 0.5
                if norm_a > 0 and norm_b > 0:
                    sim = sim / (norm_a * norm_b)
                else:
                    sim = 0

            if sim >= self.trigger_threshold:
                # Optional: LLM verification for high-confidence matching
                if self.llm and sim < 0.85:
                    verify = self.llm(
                        f"Does this context match this trigger?\n"
                        f"Context: {current_context[:200]}\n"
                        f"Trigger: {p.trigger_condition}\n"
                        f"Answer YES or NO only:"
                    )
                    if "YES" not in verify.upper():
                        continue

                triggered.append((p, sim))

        return triggered

    def fire(self, unit: MemoryUnit) -> dict:
        """Fire a prospective memory — mark as completed, return action."""
        self.store.deactivate(unit.id)
        print(f"[ENGRAM] Prospective fired: {unit.trigger_condition[:60]}...")
        return unit.action or {}

    def list_active(self) -> list[MemoryUnit]:
        """List all active prospective memories."""
        return self.store.query(type="prospective", active_only=True, limit=100)
