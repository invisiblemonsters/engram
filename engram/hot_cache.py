"""ENGRAM Hot Cache — decay-aware memory summary generator."""
import math
from datetime import datetime, timezone
from typing import Optional, Callable
from .types import MemoryUnit


class HotCache:
    """Generates a decay-scored hot cache of the most relevant active memories."""
    
    QUERIES = [
        "identity, name, role, purpose",
        "active projects, tasks, deadlines",
        "key accounts, credentials, services",
        "lessons learned, mistakes to avoid",
        "important people, relationships, contacts",
        "wallet addresses, financial status",
        "technical architecture, infrastructure",
    ]
    
    def __init__(self, store, embedder, retriever, llm_fn: Optional[Callable] = None,
                 agent_name: str = "Agent"):
        self.store = store
        self.embedder = embedder
        self.retriever = retriever
        self.llm = llm_fn
        self.agent_name = agent_name
    
    def decay_score(self, unit: MemoryUnit) -> float:
        """Compute a composite decay-aware relevance score."""
        now = datetime.now(timezone.utc)
        try:
            ts = datetime.fromisoformat(unit.timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_days = max((now - ts).total_seconds() / 86400, 0)
        except Exception:
            age_days = 30
        
        decayed_salience = unit.salience * (unit.decay_rate ** age_days)
        recency = math.exp(-age_days / 14)
        access_boost = min(unit.retrieval_count / 20, 1.0)
        graph_score = min(len(unit.relations) / 10, 1.0) if unit.relations else 0
        
        return (decayed_salience * 0.4 +
                recency * 0.3 +
                access_boost * 0.2 +
                graph_score * 0.1)
    
    def gather(self, max_memories: int = 60) -> list[MemoryUnit]:
        """Gather top memories across all query dimensions, deduplicated and decay-ranked."""
        seen_ids = set()
        all_results = []
        
        for query in self.QUERIES:
            results = self.retriever.retrieve(query, top_k=15, update_access=False)
            for unit in results:
                if unit.id not in seen_ids:
                    seen_ids.add(unit.id)
                    all_results.append(unit)
        
        # Score and sort by decay-aware relevance
        scored = [(unit, self.decay_score(unit)) for unit in all_results]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [unit for unit, score in scored[:max_memories]]
    
    def generate(self, output_path: Optional[str] = None, max_memories: int = 60) -> str:
        """Generate a hot cache document from decay-scored memories."""
        memories = self.gather(max_memories)
        
        if not memories:
            return f"# {self.agent_name} Hot Cache\n\nNo memories available.\n"
        
        if self.llm:
            return self._llm_generate(memories, output_path)
        else:
            return self._simple_generate(memories, output_path)
    
    def _simple_generate(self, memories: list[MemoryUnit], output_path: Optional[str] = None) -> str:
        """Generate without LLM — just ranked memory dump."""
        lines = [f"# {self.agent_name} Hot Cache",
                 f"_Generated: {datetime.now(timezone.utc).isoformat()}_",
                 f"_Memories: {len(memories)} (decay-scored)_\n"]
        
        for i, unit in enumerate(memories, 1):
            score = self.decay_score(unit)
            lines.append(f"**{i}.** [{unit.type}] (score: {score:.3f}) {unit.content[:200]}")
            if unit.tags:
                lines.append(f"   Tags: {', '.join(unit.tags[:5])}")
            lines.append("")
        
        text = "\n".join(lines)
        if output_path:
            from pathlib import Path
            Path(output_path).write_text(text, encoding="utf-8")
        return text
    
    def _llm_generate(self, memories: list[MemoryUnit], output_path: Optional[str] = None) -> str:
        """Generate with LLM summarization."""
        import json
        
        memory_data = []
        for unit in memories:
            score = self.decay_score(unit)
            memory_data.append({
                "content": unit.content[:400],
                "type": unit.type,
                "decay_score": round(score, 3),
                "tags": unit.tags[:5],
                "age_indicator": unit.timestamp[:10],
            })
        
        prompt = f"""You are generating a hot cache summary for {self.agent_name}.
These memories are already ranked by decay-aware relevance (recent + frequently accessed + high salience memories rank highest).

Memories (ranked by relevance):
{json.dumps(memory_data, indent=1)}

Generate a concise, structured markdown document organized by topic.
Rules:
- Prioritize higher-scored memories (they are more current/relevant)
- If two memories contradict, prefer the higher-scored one
- Use ## headers for sections
- Be factual — this is a reference document, not narrative
- Include key facts, active tasks, important context
- Skip trivial or clearly outdated information
"""
        
        try:
            result = self.llm(prompt)
            header = (f"# {self.agent_name} Hot Cache\n\n"
                     f"_Auto-generated: {datetime.now(timezone.utc).isoformat()}_\n"
                     f"_Source: {len(memories)} decay-scored memories_\n\n")
            text = header + result
        except Exception:
            text = self._simple_generate(memories)
        
        if output_path:
            from pathlib import Path
            Path(output_path).write_text(text, encoding="utf-8")
        return text
