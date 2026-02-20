"""ENGRAM hybrid retrieval with emotional modulation."""
import math
from datetime import datetime, timezone
from typing import Optional
from .types import MemoryUnit


class Retriever:
    WEIGHTS = {"semantic": 0.6, "recency": 0.2, "salience": 0.15, "graph": 0.05}

    def __init__(self, store, embedder):
        self.store = store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 10,
                 type_filter: Optional[str] = None,
                 min_salience: float = 0.0,
                 emotion_query: Optional[list[float]] = None,
                 days_window: Optional[int] = None,
                 update_access: bool = True) -> list[MemoryUnit]:
        query_emb = self.embedder.embed(query)
        candidates = self.store.vector_search_full(query_emb, top_k=top_k * 3,
                                                    type_filter=type_filter, min_salience=min_salience)
        if not candidates:
            return self.store.query(type=type_filter, min_salience=min_salience, limit=top_k)

        now = datetime.now(timezone.utc)
        scored = []

        for unit, semantic_score in candidates:
            if not unit or not unit.active:
                continue
            try:
                ts = datetime.fromisoformat(unit.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_days = (now - ts).total_seconds() / 86400
            except Exception:
                age_days = 30
            if days_window and age_days > days_window:
                continue

            decayed_salience = unit.salience * (unit.decay_rate ** age_days)
            if decayed_salience < 0.01:
                continue

            recency = math.exp(-age_days / 14)
            graph_score = min(len(unit.relations) / 10, 1.0) if unit.relations else 0
            score = (self.WEIGHTS["semantic"] * max(semantic_score, 0) +
                     self.WEIGHTS["recency"] * recency +
                     self.WEIGHTS["salience"] * decayed_salience +
                     self.WEIGHTS["graph"] * graph_score)

            if emotion_query and unit.emotion_vector:
                resonance = sum(a * b for a, b in zip(emotion_query, unit.emotion_vector))
                if resonance > 0.6:
                    score *= 1.4
                elif resonance < -0.3:
                    score *= 0.6
            scored.append((unit, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for unit, score in scored[:top_k]:
            if update_access:
                self.store.update_access(unit.id)
            results.append(unit)
        return results
