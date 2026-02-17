"""ENGRAM dream cycle — creative recombination for novel insights."""
import json
import random
from typing import Callable, Optional
from .schema import MemoryUnit
from .store import EngramStore
from .embedder import Embedder


class Dreamer:
    """Hippocampal replay + cortical remixing.
    
    Samples random semantic nodes, asks LLM for surprising connections,
    filters by novelty (embedding distance), creates 'insight' memories.
    """

    def __init__(self, store: EngramStore, embedder: Embedder,
                 llm_fn: Optional[Callable] = None,
                 novelty_threshold: float = 0.75,
                 min_score: float = 0.55):
        self.store = store
        self.embedder = embedder
        self.llm = llm_fn
        self.novelty_threshold = novelty_threshold
        self.min_score = min_score

    def dream(self, n_samples: int = 5, max_insights: int = 3) -> list[MemoryUnit]:
        """Run one dream cycle. Returns created insight memories."""
        if not self.llm:
            return []

        # Sample semantic nodes (salience-biased random)
        all_semantic = self.store.query(type="semantic", active_only=True, limit=500)
        if len(all_semantic) < n_samples:
            return []

        # Weighted sampling by salience
        weights = [m.salience + 0.1 for m in all_semantic]
        total = sum(weights)
        weights = [w / total for w in weights]
        
        selected = []
        indices = list(range(len(all_semantic)))
        for _ in range(n_samples):
            if not indices:
                break
            # Weighted random choice
            r = random.random()
            cumulative = 0
            for i, idx in enumerate(indices):
                cumulative += weights[idx]
                if r <= cumulative:
                    selected.append(all_semantic[idx])
                    indices.pop(i)
                    break

        if len(selected) < 3:
            return []

        prompt = f"""You are a creative insight generator. Given these {len(selected)} memories from an AI agent,
find 1-{max_insights} SURPRISING, non-obvious connections between them.

Memories:
{json.dumps([{"id": m.id, "content": m.content, "tags": m.tags} for m in selected], indent=2)}

Rules:
- Connections must be genuinely novel, not obvious restatements
- Each insight should link at least 2 of the memories
- Rate your own novelty 0-1 (be harsh — only truly surprising gets >0.75)

Output JSON array:
[
  {{
    "insight": "the surprising connection or idea",
    "links": ["memory_id_1", "memory_id_2"],
    "novelty_score": 0.0-1.0,
    "tags": ["relevant", "tags"]
  }}
]

Output ONLY valid JSON array:"""

        try:
            result = self.llm(prompt)
            start = result.find("[")
            end = result.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            insights = json.loads(result[start:end])
        except Exception as e:
            print(f"[ENGRAM] Dream LLM error: {e}")
            return []

        created = []
        prev_hash = self.store.get_last_hash()

        for insight in insights:
            content = insight.get("insight", "")
            score = insight.get("novelty_score", 0)
            
            if not content or score < self.min_score:
                continue

            # Verify novelty via embedding distance
            # Reject if too similar to existing memory (cosine sim > threshold)
            # 0.75 means "only reject near-duplicates", lower = stricter
            emb = self.embedder.embed(content)
            nearest = self.store.vector_search(emb, top_k=3)
            max_sim = nearest[0][1] if nearest else 0
            if max_sim > self.novelty_threshold:
                continue  # too similar to existing memory

            relations = [
                {"target_id": lid, "relation": "inspired_by", "strength": 0.9}
                for lid in insight.get("links", [])
            ]

            unit = MemoryUnit(
                content=content,
                type="insight",
                embedding=emb,
                salience=0.92,  # insights start high
                tags=insight.get("tags", []) + ["dream"],
                relations=relations,
                prev_hash=prev_hash,
            )
            prev_hash = unit.content_hash()
            self.store.store(unit)
            created.append(unit)

        if created:
            print(f"[ENGRAM] Dream: {len(created)} new insights created")
        return created

    def should_dream(self, new_semantic_count: int = 0) -> bool:
        """Check if dream conditions are met."""
        total_semantic = self.store.count(type="semantic")
        return total_semantic >= 10 and new_semantic_count >= 50
