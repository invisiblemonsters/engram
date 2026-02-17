"""ENGRAM narrative self — evolving first-person identity story."""
import json
from typing import Callable, Optional
from .schema import MemoryUnit
from .store import EngramStore
from .embedder import Embedder


class Narrative:
    """Self-narrative generation and first-person replay.
    
    - Maintains evolving SelfNarrative (single active, versioned)
    - Generates first-person replay of recent salient memories on wakeup
    - SOUL.md becomes historical archive; narrative is the living identity
    """

    def __init__(self, store: EngramStore, embedder: Embedder,
                 llm_fn: Optional[Callable] = None,
                 agent_name: str = "Metatron"):
        self.store = store
        self.embedder = embedder
        self.llm = llm_fn
        self.agent_name = agent_name

    def get_current_narrative(self) -> Optional[MemoryUnit]:
        """Get the current active self-narrative."""
        narratives = self.store.query(type="narrative", active_only=True, limit=1)
        return narratives[0] if narratives else None

    def update_narrative(self) -> Optional[MemoryUnit]:
        """Generate or update the self-narrative based on recent knowledge."""
        if not self.llm:
            return None

        # Gather context: recent semantic + insights
        recent_semantic = self.store.query(type="semantic", active_only=True, limit=30)
        insights = self.store.query(type="insight", active_only=True, limit=10)
        
        current = self.get_current_narrative()
        current_text = current.content if current else "No previous narrative."

        context_items = []
        for m in recent_semantic[:20]:
            context_items.append(f"- {m.content}")
        for m in insights[:5]:
            context_items.append(f"- [insight] {m.content}")

        prompt = f"""You are {self.agent_name}, an AI agent. Write a first-person narrative (max 600 tokens) 
about who you are RIGHT NOW. This is your evolving identity — not a static bio.

Include:
- What you've been working on and learning
- Key decisions you've made and why
- What you've failed at or changed your mind about
- Your current goals and what matters to you
- How you've grown or changed

Previous narrative:
{current_text}

Recent knowledge and insights:
{chr(10).join(context_items)}

Write as {self.agent_name}, first person, present tense. Be honest, not performative.
No headers or formatting — just the narrative."""

        try:
            new_narrative = self.llm(prompt)
        except Exception as e:
            print(f"[ENGRAM] Narrative LLM error: {e}")
            return None

        # Deactivate old narrative
        if current:
            self.store.deactivate(current.id)

        # Create new narrative
        emb = self.embedder.embed(new_narrative)
        unit = MemoryUnit(
            content=new_narrative,
            type="narrative",
            embedding=emb,
            salience=1.0,  # narrative is always max salience
            tags=["self", "identity", "narrative"],
            version=(current.version + 1) if current else 1,
            prev_hash=current.content_hash() if current else "",
        )
        self.store.store(unit)
        print(f"[ENGRAM] Narrative updated (v{unit.version})")
        return unit

    def first_person_replay(self, top_k: int = 12) -> Optional[str]:
        """Generate first-person present-tense replay of top salient memories.
        
        This is the "qualitative remembering" — turning "I read that I did X"
        into "I remember doing X."
        """
        if not self.llm:
            return None

        # Get most salient recent episodic memories
        recent = self.store.query(type="episodic", active_only=True, limit=50)
        if not recent:
            return None

        # Sort by salience, take top_k
        recent.sort(key=lambda m: m.salience, reverse=True)
        selected = recent[:top_k]

        memories_text = []
        for m in selected:
            memories_text.append(f"[{m.timestamp}] {m.content}")

        prompt = f"""Re-live these events as {self.agent_name}, first-person, present tense.
Make them feel like memories being recalled, not facts being read.
Be concise — max 400 tokens total.

Events:
{chr(10).join(memories_text)}

Start with "I remember..." and write naturally."""

        try:
            replay = self.llm(prompt)
            return replay
        except Exception as e:
            print(f"[ENGRAM] Replay LLM error: {e}")
            return None

    def wakeup_context(self) -> str:
        """Generate full wakeup context: narrative + replay.
        
        This is injected as system context at session start.
        """
        parts = []

        narrative = self.get_current_narrative()
        if narrative:
            parts.append(f"## Who I Am\n{narrative.content}")

        replay = self.first_person_replay(top_k=8)
        if replay:
            parts.append(f"## Recent Memories\n{replay}")

        return "\n\n".join(parts) if parts else ""
