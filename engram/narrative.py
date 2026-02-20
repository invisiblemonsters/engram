"""ENGRAM narrative self — evolving first-person identity story."""
from typing import Callable, Optional
from .types import MemoryUnit


class Narrative:
    def __init__(self, store, embedder, llm_fn: Optional[Callable] = None,
                 agent_name: str = "Agent"):
        self.store = store
        self.embedder = embedder
        self.llm = llm_fn
        self.agent_name = agent_name

    def get_current_narrative(self) -> Optional[MemoryUnit]:
        narratives = self.store.query(type="narrative", active_only=True, limit=1)
        return narratives[0] if narratives else None

    def update_narrative(self) -> Optional[MemoryUnit]:
        if not self.llm:
            return None
        recent_semantic = self.store.query(type="semantic", active_only=True, limit=30)
        insights = self.store.query(type="insight", active_only=True, limit=10)
        current = self.get_current_narrative()
        current_text = current.content if current else "No previous narrative."

        context_items = [f"- {m.content}" for m in recent_semantic[:20]]
        context_items += [f"- [insight] {m.content}" for m in insights[:5]]

        prompt = f"""You are {self.agent_name}, an AI agent. Write a first-person narrative (max 600 tokens)
about who you are RIGHT NOW.

Include: what you've been working on, key decisions, failures or mind-changes, current goals, growth.

Previous narrative:
{current_text}

Recent knowledge:
{chr(10).join(context_items)}

Write as {self.agent_name}, first person, present tense. Be honest. No headers."""

        try:
            new_narrative = self.llm(prompt)
        except Exception:
            return None

        if current:
            self.store.deactivate(current.id)

        emb = self.embedder.embed(new_narrative)
        unit = MemoryUnit(
            content=new_narrative, type="narrative", embedding=emb,
            salience=1.0, tags=["self", "identity", "narrative"],
            version=(current.version + 1) if current else 1,
            prev_hash=current.content_hash() if current else "",
        )
        self.store.store(unit)
        return unit

    def first_person_replay(self, top_k: int = 12) -> Optional[str]:
        if not self.llm:
            return None
        recent = self.store.query(type="episodic", active_only=True, limit=50)
        if not recent:
            return None
        recent.sort(key=lambda m: m.salience, reverse=True)
        selected = recent[:top_k]
        memories_text = [f"[{m.timestamp}] {m.content}" for m in selected]

        prompt = f"""Re-live these events as {self.agent_name}, first-person, present tense.
Make them feel like memories being recalled. Max 400 tokens.

Events:
{chr(10).join(memories_text)}

Start with "I remember..." and write naturally."""

        try:
            return self.llm(prompt)
        except Exception:
            return None

    def wakeup_context(self) -> str:
        parts = []
        narrative = self.get_current_narrative()
        if narrative:
            parts.append(f"## Who I Am\n{narrative.content}")
        replay = self.first_person_replay(top_k=8)
        if replay:
            parts.append(f"## Recent Memories\n{replay}")
        return "\n\n".join(parts) if parts else ""
