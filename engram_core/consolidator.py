"""ENGRAM consolidation — episode→knowledge with contradiction resolution."""
import json
from datetime import datetime, timezone
from typing import Optional, Callable
from .schema import MemoryUnit
from .store import EngramStore
from .embedder import Embedder


class Consolidator:
    """Hippocampus-inspired memory consolidation.
    
    - Wakeup consolidation: detect unconsolidated episodes, batch distill
    - Micro-consolidation: every N new units during session
    - Contradiction resolution: versioned belief graph, never overwrite
    """

    def __init__(self, store: EngramStore, embedder: Embedder,
                 llm_fn: Optional[Callable] = None,
                 micro_threshold: int = 8):
        self.store = store
        self.embedder = embedder
        self.llm = llm_fn  # async or sync function: (prompt: str) -> str
        self.micro_threshold = micro_threshold
        self._new_count = 0

    def check_wakeup(self) -> list[MemoryUnit]:
        """On wakeup: find unconsolidated episodic memories."""
        return self.store.query(unconsolidated_only=True, limit=200)

    def consolidate_batch(self, episodes: list[MemoryUnit]) -> list[MemoryUnit]:
        """Distill episodic memories into semantic knowledge.
        
        Returns list of newly created semantic MemoryUnits.
        """
        if not episodes or not self.llm:
            return []

        # Build replay buffer
        replay = [{"id": e.id, "content": e.content, "timestamp": e.timestamp,
                    "tags": e.tags, "salience": e.salience} for e in episodes]

        prompt = f"""You are a memory consolidation system. Given these episodic memories (raw experiences),
distill them into semantic knowledge (facts, rules, lessons learned).

Rules:
- Extract durable facts, not transient details
- Identify contradictions with existing knowledge
- Merge related facts into single statements
- Preserve important context and decisions
- Output as JSON array

Episodic memories:
{json.dumps(replay, indent=2)}

Output format:
[
  {{
    "content": "distilled fact or rule",
    "tags": ["relevant", "tags"],
    "salience": 0.0-1.0,
    "source_episodes": ["episode_id1", "episode_id2"],
    "contradicts": null or "description of what this contradicts"
  }}
]

Output ONLY valid JSON array:"""

        try:
            result = self.llm(prompt)
            # Parse LLM output
            # Find JSON array in response
            start = result.find("[")
            end = result.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            facts = json.loads(result[start:end])
        except Exception as e:
            print(f"[ENGRAM] Consolidation LLM error: {e}")
            return []

        created = []
        prev_hash = self.store.get_last_hash()

        for fact in facts:
            content = fact.get("content", "")
            if not content:
                continue

            # Check for contradictions
            if fact.get("contradicts"):
                self._handle_contradiction(content, fact["contradicts"])

            # Create semantic memory
            embedding = self.embedder.embed(content)
            relations = []
            for eid in fact.get("source_episodes", []):
                relations.append({"target_id": eid, "relation": "distilled_from", "strength": 0.9})

            unit = MemoryUnit(
                content=content,
                type="semantic",
                embedding=embedding,
                salience=fact.get("salience", 0.6),
                tags=fact.get("tags", []),
                relations=relations,
                prev_hash=prev_hash,
            )
            prev_hash = unit.content_hash()
            self.store.store(unit)
            created.append(unit)

        # Mark episodes as consolidated
        for ep in episodes:
            self.store.mark_consolidated(ep.id)

        return created

    def on_new_memory(self, unit: MemoryUnit) -> Optional[list[MemoryUnit]]:
        """Called after each new episodic memory. Triggers micro-consolidation if threshold hit."""
        if unit.type != "episodic":
            return None

        self._new_count += 1
        if self._new_count >= self.micro_threshold:
            self._new_count = 0
            recent = self.store.query(type="episodic", unconsolidated_only=True, limit=20)
            if recent:
                return self.consolidate_batch(recent)
        return None

    def _handle_contradiction(self, new_fact: str, contradiction_desc: str):
        """Find and deactivate contradicted semantic memories."""
        # Search for the contradicted fact
        emb = self.embedder.embed(contradiction_desc)
        candidates = self.store.vector_search(emb, top_k=5)
        
        for uid, score in candidates:
            if score > 0.75:
                old = self.store.get(uid)
                if old and old.type == "semantic" and old.active:
                    # Soft deactivate, don't delete
                    self.store.deactivate(uid)
                    # The new fact will be created by the caller with a supersedes relation
                    break

    def wakeup_consolidate(self) -> list[MemoryUnit]:
        """Full wakeup consolidation sequence."""
        unconsolidated = self.check_wakeup()
        if not unconsolidated:
            return []
        print(f"[ENGRAM] Wakeup: {len(unconsolidated)} unconsolidated episodes found")
        return self.consolidate_batch(unconsolidated)
