"""ENGRAM consolidation — episode→knowledge with contradiction resolution."""
import json
from typing import Optional, Callable
from .types import MemoryUnit


class Consolidator:
    """Hippocampus-inspired memory consolidation."""

    def __init__(self, store, embedder, llm_fn: Optional[Callable] = None,
                 micro_threshold: int = 8):
        self.store = store
        self.embedder = embedder
        self.llm = llm_fn
        self.micro_threshold = micro_threshold
        self._new_count = 0

    def check_wakeup(self) -> list[MemoryUnit]:
        return self.store.query(unconsolidated_only=True, limit=200)

    def consolidate_batch(self, episodes: list[MemoryUnit]) -> list[MemoryUnit]:
        if not episodes or not self.llm:
            return []

        replay = []
        for e in episodes:
            ts = e.timestamp if isinstance(e.timestamp, str) else str(e.timestamp)[:19]
            content = e.content[:300] if len(e.content) > 300 else e.content
            replay.append({"id": e.id, "content": content, "ts": ts,
                           "tags": e.tags[:5], "salience": e.salience})

        prompt = (
            "You are a memory consolidation system. Distill these episodic memories "
            "into semantic knowledge (durable facts, rules, lessons). "
            "Merge related facts. Preserve important context.\n\n"
            "Episodes:\n" + json.dumps(replay, indent=1) + "\n\n"
            "Output ONLY a valid JSON array:\n"
            '[{"content": "fact", "tags": ["tag"], "salience": 0.7, '
            '"source_episodes": ["id1"], "contradicts": null}]'
        )

        try:
            result = self.llm(prompt)
            start = result.find("[")
            end = result.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            facts = json.loads(result[start:end])
        except Exception:
            return []

        created = []
        prev_hash = self.store.get_last_hash()

        for fact in facts:
            content = fact.get("content", "")
            if not content:
                continue
            if fact.get("contradicts"):
                self._handle_contradiction(content, fact["contradicts"])

            embedding = self.embedder.embed(content)
            relations = [{"target_id": eid, "relation": "distilled_from", "strength": 0.9}
                         for eid in fact.get("source_episodes", [])]

            unit = MemoryUnit(
                content=content, type="semantic", embedding=embedding,
                salience=fact.get("salience", 0.6), tags=fact.get("tags", []),
                relations=relations, prev_hash=prev_hash,
            )
            prev_hash = unit.content_hash()
            self.store.store(unit)
            created.append(unit)

        for ep in episodes:
            self.store.mark_consolidated(ep.id)

        return created

    def on_new_memory(self, unit: MemoryUnit) -> Optional[list[MemoryUnit]]:
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
        emb = self.embedder.embed(contradiction_desc)
        candidates = self.store.vector_search(emb, top_k=5)
        for uid, score in candidates:
            if score > 0.75:
                old = self.store.get(uid)
                if old and old.type == "semantic" and old.active:
                    self.store.deactivate(uid)
                    break

    def wakeup_consolidate(self) -> list[MemoryUnit]:
        unconsolidated = self.check_wakeup()
        if not unconsolidated:
            return []
        return self.consolidate_batch(unconsolidated)
