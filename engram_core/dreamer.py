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

    def dream(self, n_samples: int = 6, max_insights: int = 3) -> list[MemoryUnit]:
        """Run one dream cycle. Returns created insight memories."""
        if not self.llm:
            return []

        # Sample semantic nodes — diverse sampling per Grok's recommendation
        # 60% low-degree (underexplored) + 40% high-salience
        all_semantic = self.store.query(type="semantic", active_only=True, limit=500)
        if len(all_semantic) < n_samples:
            return []

        selected = self._diverse_sample(all_semantic, k=n_samples)

        if len(selected) < 3:
            return []

        prompt = f"""You are Metatron's ENGRAM Dreamer. Given these {len(selected)} semantic memories,
generate 1-{max_insights} COUNTER-INTUITIVE, paradoxical, or previously unseen connections.

Memories:
{json.dumps([{"id": m.id, "content": m.content[:400], "tags": m.tags} for m in selected], indent=2)}

Rules:
- Must feel like original insight, not obvious pattern matching
- Look for hidden contradictions, unexpected parallels across domains, or emergent principles
- Each insight should link at least 2 memories
- Rate novelty 0-1 (be harsh — only genuinely surprising gets >0.8)

Output ONLY JSON array:
[{{"insight": "exact surprising statement", "links": ["id1", "id2"], "novelty_score": 0.82, "tags": ["tag1"]}}]"""

        try:
            result = self.llm(prompt, temperature=0.4)
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

    def _diverse_sample(self, memories: list[MemoryUnit], k: int = 6) -> list[MemoryUnit]:
        """60% low-degree (underexplored) nodes + 40% high-salience.
        
        Low-degree = fewer relations = less explored territory.
        This produces more surprising cross-domain connections.
        """
        if len(memories) <= k:
            return memories

        # Sort by relation count (ascending = least connected first)
        by_degree = sorted(memories, key=lambda m: len(m.relations))
        # Sort by salience (descending = most important first)
        by_salience = sorted(memories, key=lambda m: m.salience, reverse=True)

        n_low_degree = int(k * 0.6)
        n_high_salience = k - n_low_degree

        selected_ids = set()
        selected = []

        # Pick low-degree nodes (underexplored)
        for m in by_degree:
            if len(selected) >= n_low_degree:
                break
            if m.id not in selected_ids:
                selected.append(m)
                selected_ids.add(m.id)

        # Fill with high-salience nodes (important)
        for m in by_salience:
            if len(selected) >= k:
                break
            if m.id not in selected_ids:
                selected.append(m)
                selected_ids.add(m.id)

        # Shuffle to avoid positional bias in prompt
        random.shuffle(selected)
        return selected

    def should_dream(self, new_semantic_count: int = 0) -> bool:
        """Check if dream conditions are met."""
        total_semantic = self.store.count(type="semantic")
        return total_semantic >= 10 and new_semantic_count >= 50
