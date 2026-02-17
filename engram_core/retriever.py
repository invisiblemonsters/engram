"""ENGRAM hybrid retrieval with emotional modulation."""
import math
from datetime import datetime, timezone
from typing import Optional
from .schema import MemoryUnit
from .store import EngramStore
from .embedder import Embedder


class Retriever:
    """Hybrid retrieval: semantic + recency + salience + graph + emotion."""

    WEIGHTS = {
        "semantic": 0.6,
        "recency": 0.2,
        "salience": 0.15,
        "graph": 0.05,
    }

    def __init__(self, store: EngramStore, embedder: Embedder):
        self.store = store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 10,
                 type_filter: Optional[str] = None,
                 min_salience: float = 0.0,
                 emotion_query: Optional[list[float]] = None,
                 days_window: Optional[int] = None) -> list[MemoryUnit]:
        """Retrieve top-k memories using hybrid scoring."""
        query_emb = self.embedder.embed(query)
        
        # Vector search for candidates
        candidates = self.store.vector_search(
            query_emb, top_k=top_k * 3,
            type_filter=type_filter,
            min_salience=min_salience
        )

        if not candidates:
            # Fallback to recent memories
            return self.store.query(type=type_filter, min_salience=min_salience, limit=top_k)

        now = datetime.now(timezone.utc)
        scored = []

        for unit_id, semantic_score in candidates:
            unit = self.store.get(unit_id)
            if not unit or not unit.active:
                continue

            # Recency score (exponential decay over 30 days)
            try:
                ts = datetime.fromisoformat(unit.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_days = (now - ts).total_seconds() / 86400
            except:
                age_days = 30
            
            if days_window and age_days > days_window:
                continue

            recency = math.exp(-age_days / 14)  # half-life ~14 days

            # Graph proximity (simple: count of relations)
            graph_score = min(len(unit.relations) / 10, 1.0) if unit.relations else 0

            # Hybrid score
            score = (
                self.WEIGHTS["semantic"] * max(semantic_score, 0) +
                self.WEIGHTS["recency"] * recency +
                self.WEIGHTS["salience"] * unit.salience +
                self.WEIGHTS["graph"] * graph_score
            )

            # Emotional modulation
            if emotion_query and unit.emotion_vector:
                resonance = self._dot(emotion_query, unit.emotion_vector)
                if resonance > 0.6:
                    score *= 1.4
                elif resonance < -0.3:
                    score *= 0.6

            # Apply decay
            decayed_salience = unit.salience * (unit.decay_rate ** age_days)
            if decayed_salience < 0.01:
                continue  # effectively forgotten

            scored.append((unit, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Update access counts for retrieved memories
        results = []
        for unit, score in scored[:top_k]:
            self.store.update_access(unit.id)
            results.append(unit)

        return results

    def retrieve_prospective(self, current_context: str) -> list[MemoryUnit]:
        """Find prospective memories whose trigger matches current context."""
        prospectives = self.store.query(type="prospective", active_only=True, limit=50)
        if not prospectives:
            return []

        context_emb = self.embedder.embed(current_context)
        matches = []

        for p in prospectives:
            if not p.trigger_condition:
                continue
            trigger_emb = self.embedder.embed(p.trigger_condition)
            sim = self._cosine(context_emb, trigger_emb)
            if sim > 0.7:  # high threshold for trigger match
                matches.append(p)

        return matches

    def _dot(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = self._dot(a, b)
        na = sum(x*x for x in a) ** 0.5
        nb = sum(x*x for x in b) ** 0.5
        if na == 0 or nb == 0:
            return 0
        return dot / (na * nb)
