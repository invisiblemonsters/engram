"""ENGRAM — Main orchestrator tying all subsystems together."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .schema import MemoryUnit
from .store import EngramStore
from .embedder import Embedder
from .retriever import Retriever
from .consolidator import Consolidator
from .dreamer import Dreamer
from .metabolism import Metabolism
from .identity import Identity
from .narrative import Narrative
from .transplant import Transplant
from .prospective import Prospective
from .anchoring import Anchoring
from .llm import EngramLLM


def _make_llm_fn(llm_client: EngramLLM):
    """Wrap EngramLLM into the simple str->str callable expected by subsystems."""
    def llm_fn(prompt: str) -> str:
        result = llm_client.call_text(prompt)
        if result is None:
            raise RuntimeError("LLM call failed")
        return result
    return llm_fn


class Engram:
    """ENGRAM cognitive memory system.
    
    Usage:
        engram = Engram(data_dir="engram_data", llm_fn=my_llm)
        engram.wakeup()
        engram.remember("I deployed AIP v0.1 today", tags=["aip", "milestone"])
        results = engram.recall("What do I know about AIP?")
        engram.sleep()
    """

    def __init__(self, data_dir: str = "engram_data",
                 model_path: Optional[str] = None,
                 llm_fn: Optional[Callable] = None,
                 llm_base_url: Optional[str] = None,
                 llm_model: Optional[str] = None,
                 agent_name: str = "Metatron",
                 max_tokens: int = 2_000_000):
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Core systems
        self.store = EngramStore(str(self.data_dir / "store"))
        self.embedder = Embedder(model_path=model_path)
        self.identity = Identity(str(self.data_dir / "identity"))

        # LLM backend: explicit fn > auto-detect copilot-proxy
        if llm_fn is None:
            kwargs = {}
            if llm_base_url:
                kwargs["base_url"] = llm_base_url
            if llm_model:
                kwargs["model"] = llm_model
            llm_client = EngramLLM(**kwargs)
            if llm_client.is_available():
                llm_fn = _make_llm_fn(llm_client)
                print(f"[ENGRAM] LLM backend: {llm_model} via {llm_base_url}")
            else:
                print("[ENGRAM] LLM backend: not available (stubs active)")

        # Cognitive systems
        self.retriever = Retriever(self.store, self.embedder)
        self.consolidator = Consolidator(self.store, self.embedder, llm_fn)
        self.dreamer = Dreamer(self.store, self.embedder, llm_fn)
        self.metabolism = Metabolism(self.store, max_tokens=max_tokens)
        self.narrative = Narrative(self.store, self.embedder, llm_fn, agent_name)
        self.transplant = Transplant(self.store, self.identity)
        self.prospective = Prospective(self.store, self.embedder, llm_fn)
        self.anchoring = Anchoring(self.store)

        self._session_start = None
        self._wakeup_done = False

    def wakeup(self) -> dict:
        """Full wakeup sequence. Call at session start.
        
        Returns wakeup report with context, consolidation results, etc.
        """
        self._session_start = datetime.now(timezone.utc)
        report = {
            "timestamp": self._session_start.isoformat(),
            "consolidation": [],
            "attestation": None,
            "narrative": None,
            "replay": None,
            "prospective_count": 0,
            "metabolism": {},
        }

        # 1. Verify chain integrity
        all_mem = self.store.query(active_only=True, limit=10000)
        root_hash = self.identity.compute_root_hash(all_mem)

        # 2. Wakeup attestation
        last_consolidation = None
        for m in reversed(all_mem):
            if m.consolidated_ts:
                last_consolidation = m.consolidated_ts
                break
        report["attestation"] = self.identity.wakeup_attestation(root_hash, last_consolidation)

        # 3. Consolidate unconsolidated episodes
        new_semantic = self.consolidator.wakeup_consolidate()
        report["consolidation"] = [m.content for m in new_semantic]

        # 4. Run metabolism
        report["metabolism"] = self.metabolism.status()
        self.metabolism.metabolize()

        # 5. Ground-truth anchoring check
        anchoring_report = self.anchoring.audit_report()
        report["anchoring"] = anchoring_report
        if anchoring_report["risk_level"] == "HIGH":
            print(f"[ENGRAM] WARNING: {anchoring_report['unanchored']} high-salience memories unanchored!")
            self.anchoring.demote_unanchored()

        # 6. Check prospective memories
        active_prospective = self.prospective.list_active()
        report["prospective_count"] = len(active_prospective)

        # 6. Get narrative context
        narrative = self.narrative.get_current_narrative()
        if narrative:
            report["narrative"] = narrative.content

        self._wakeup_done = True
        
        stats = self.store.count()
        print(f"[ENGRAM] Wakeup complete: {stats} active memories, "
              f"{len(new_semantic)} consolidated, "
              f"{report['metabolism'].get('utilization', 0)}% budget used")

        return report

    def remember(self, content: str, type: str = "episodic",
                 tags: list = None, salience: float = 0.5,
                 emotion: Optional[list[float]] = None) -> MemoryUnit:
        """Store a new memory.
        
        Args:
            content: What to remember
            type: Memory type (episodic, semantic, procedural)
            tags: Classification tags
            salience: Importance 0-1
            emotion: 8-dim emotion vector [joy, frustration, curiosity, anger, surprise, satisfaction, fear, calm]
        """
        embedding = self.embedder.embed(content)
        prev_hash = self.store.get_last_hash()

        unit = MemoryUnit(
            content=content,
            type=type,
            embedding=embedding,
            salience=salience,
            tags=tags or [],
            emotion_vector=emotion or [0.0] * 8,
            prev_hash=prev_hash,
        )

        # Sign it
        unit.signature = self.identity.sign_memory(unit)

        self.store.store(unit)

        # Check for micro-consolidation
        self.consolidator.on_new_memory(unit)

        # Earn metabolism tokens for being useful
        self.metabolism.earn(0.5)

        return unit

    def recall(self, query: str, top_k: int = 10,
               type_filter: Optional[str] = None,
               emotion: Optional[list[float]] = None) -> list[MemoryUnit]:
        """Retrieve memories relevant to query."""
        results = self.retriever.retrieve(
            query, top_k=top_k,
            type_filter=type_filter,
            emotion_query=emotion
        )

        # Check prospective triggers
        triggered = self.prospective.check_triggers(query)
        for unit, score in triggered:
            action = self.prospective.fire(unit)
            print(f"[ENGRAM] Prospective triggered: {action}")

        return results

    def dream(self) -> list[MemoryUnit]:
        """Run a dream cycle for creative insight generation."""
        return self.dreamer.dream()

    def sleep(self) -> dict:
        """End-of-session consolidation and maintenance.
        
        Call before session ends (or run via cron for crash resilience).
        """
        report = {"consolidated": 0, "dreamed": 0, "archived": 0, "narrative_updated": False}

        # Final consolidation
        new_semantic = self.consolidator.wakeup_consolidate()
        report["consolidated"] = len(new_semantic)

        # Dream if enough new knowledge
        if self.store.count(type="semantic") >= 10:
            insights = self.dreamer.dream()
            report["dreamed"] = len(insights)

        # Update narrative
        narrative = self.narrative.update_narrative()
        report["narrative_updated"] = narrative is not None

        # Metabolism cleanup
        archived = self.metabolism.metabolize()
        report["archived"] = len(archived)

        print(f"[ENGRAM] Sleep: {report['consolidated']} consolidated, "
              f"{report['dreamed']} insights, {report['archived']} archived")
        return report

    def intend(self, trigger: str, action: dict, content: Optional[str] = None) -> MemoryUnit:
        """Create a prospective memory (future intention)."""
        return self.prospective.create(trigger, action, content)

    def export_memories(self, tags: list[str] = None,
                        ids: list[str] = None) -> dict:
        """Export memories as signed transplant package."""
        if ids:
            return self.transplant.export_package(ids)
        elif tags:
            return self.transplant.export_by_tags(tags)
        return {}

    def import_memories(self, package: dict, auto_accept: bool = False) -> list[MemoryUnit]:
        """Import a transplant package from another agent."""
        return self.transplant.import_package(package, auto_accept=auto_accept)

    def anchor(self, unit_id: str, method: str = "human_verified"):
        """Mark a memory as externally verified (prevents bias drift)."""
        self.anchoring.anchor(unit_id, method)

    def status(self) -> dict:
        """Full system status."""
        return {
            "memories": {
                "total": self.store.count(),
                "episodic": self.store.count(type="episodic"),
                "semantic": self.store.count(type="semantic"),
                "insight": self.store.count(type="insight"),
                "prospective": self.store.count(type="prospective"),
                "narrative": self.store.count(type="narrative"),
            },
            "metabolism": self.metabolism.status(),
            "identity": self.identity.public_key_b64(),
            "anchoring": self.anchoring.audit_report(),
            "embedder": self.embedder.backend,
            "wakeup_done": self._wakeup_done,
        }

    def wakeup_context(self) -> str:
        """Get full wakeup context string for injection into agent system prompt."""
        return self.narrative.wakeup_context()
