"""ENGRAM — Main orchestrator tying all subsystems together."""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .config import EngramConfig
from .types import MemoryUnit
from .store import LanceStore
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
from .safe_write import SafeWriter
from .llm import EngramLLM

logger = logging.getLogger("engram")


def _make_llm_fn(llm_client: EngramLLM):
    def llm_fn(prompt: str, temperature: float = 0.0) -> str:
        result = llm_client.call_text(prompt, temperature=temperature)
        if result is None:
            raise RuntimeError("LLM call failed")
        return result
    return llm_fn


class Engram:
    """ENGRAM cognitive memory system.

    Usage:
        engram = Engram()  # auto-discovers config
        engram.remember("something happened", type="episodic", tags=["test"], salience=0.8)
        results = engram.recall("what happened?", top_k=5)
        engram.sleep()
        status = engram.status()
    """

    def __init__(self, data_dir: Optional[str] = None,
                 config_path: Optional[str] = None,
                 llm_fn: Optional[Callable] = None,
                 **kwargs):
        # Build config from yaml + env + explicit overrides
        overrides = {}
        if data_dir is not None:
            overrides["data_dir"] = data_dir
        overrides.update(kwargs)
        self.config = EngramConfig(config_path=config_path, **overrides)

        self.data_dir = self.config.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Core systems
        self.store = LanceStore(str(self.data_dir / "lance_store"))
        self.embedder = Embedder(
            provider=self.config.embedding_provider,
            model=self.config.embedding_model,
        )
        self.identity = Identity(str(self.data_dir / "identity"))

        # LLM backend
        if llm_fn is None and self.config.llm_provider != "none":
            llm_client = EngramLLM(
                provider=self.config.llm_provider,
                model=self.config.llm_model,
                api_key=self.config.llm_api_key,
                base_url=self.config.llm_base_url,
            )
            if llm_client.is_available():
                llm_fn = _make_llm_fn(llm_client)
                logger.info(f"LLM backend: {self.config.llm_provider}/{self.config.llm_model}")
            else:
                logger.info("LLM backend: not available (stubs active)")

        # Cognitive systems
        self.retriever = Retriever(self.store, self.embedder)
        self.consolidator = Consolidator(self.store, self.embedder, llm_fn)
        self.dreamer = Dreamer(self.store, self.embedder, llm_fn)
        self.metabolism = Metabolism(self.store, max_tokens=self.config.max_tokens)
        self.narrative = Narrative(self.store, self.embedder, llm_fn, self.config.agent_name)
        self.transplant = Transplant(self.store, self.identity)
        self.prospective = Prospective(self.store, self.embedder, llm_fn)
        self.anchoring = Anchoring(self.store)
        self.safe_writer = SafeWriter(str(self.data_dir))

        self._session_start = None
        self._wakeup_done = False

    def wakeup(self) -> dict:
        """Full wakeup sequence. Call at session start."""
        self._session_start = datetime.now(timezone.utc)
        report = {
            "timestamp": self._session_start.isoformat(),
            "consolidation": [], "attestation": None,
            "narrative": None, "replay": None,
            "prospective_count": 0, "metabolism": {},
        }

        all_mem = self.store.query(active_only=True, limit=10000)
        root_hash = self.identity.compute_root_hash(all_mem)

        last_consolidation = None
        for m in reversed(all_mem):
            if m.consolidated_ts:
                last_consolidation = m.consolidated_ts
                break
        report["attestation"] = self.identity.wakeup_attestation(root_hash, last_consolidation)

        new_semantic = self.consolidator.wakeup_consolidate()
        report["consolidation"] = [m.content for m in new_semantic]

        report["metabolism"] = self.metabolism.status()
        self.metabolism.metabolize()

        anchoring_report = self.anchoring.audit_report()
        report["anchoring"] = anchoring_report
        if anchoring_report["risk_level"] == "HIGH":
            self.anchoring.demote_unanchored()

        active_prospective = self.prospective.list_active()
        report["prospective_count"] = len(active_prospective)

        narrative = self.narrative.get_current_narrative()
        if narrative:
            report["narrative"] = narrative.content

        self._wakeup_done = True
        return report

    def remember(self, content: str, type: str = "episodic",
                 tags: list = None, salience: float = 0.5,
                 emotion: Optional[list[float]] = None) -> MemoryUnit:
        """Store a new memory."""
        embedding = self.embedder.embed(content)
        prev_hash = self.store.get_last_hash()

        unit = MemoryUnit(
            content=content, type=type, embedding=embedding,
            salience=salience, tags=tags or [],
            emotion_vector=emotion or [0.0] * 8,
            prev_hash=prev_hash,
        )
        unit.signature = self.identity.sign_memory(unit)
        self.store.store(unit)
        self.consolidator.on_new_memory(unit)
        self.metabolism.earn(0.5)
        return unit

    def recall(self, query: str, top_k: int = 10,
               type_filter: Optional[str] = None,
               emotion: Optional[list[float]] = None) -> list[MemoryUnit]:
        """Retrieve memories relevant to query."""
        results = self.retriever.retrieve(query, top_k=top_k,
                                           type_filter=type_filter, emotion_query=emotion)
        triggered = self.prospective.check_triggers(query)
        for unit, score in triggered:
            self.prospective.fire(unit)
        return results

    def dream(self) -> list[MemoryUnit]:
        """Run a dream cycle for creative insight generation."""
        return self.dreamer.dream()

    def sleep(self) -> dict:
        """End-of-session consolidation and maintenance."""
        self.safe_writer.snapshot()
        report = {"consolidated": 0, "dreamed": 0, "archived": 0, "narrative_updated": False}

        new_semantic = self.consolidator.wakeup_consolidate()
        report["consolidated"] = len(new_semantic)

        if self.store.count(type="semantic") >= 10:
            insights = self.dreamer.dream()
            report["dreamed"] = len(insights)

        narrative = self.narrative.update_narrative()
        report["narrative_updated"] = narrative is not None

        archived = self.metabolism.metabolize()
        report["archived"] = len(archived)
        return report

    def intend(self, trigger: str, action: dict, content: Optional[str] = None) -> MemoryUnit:
        """Create a prospective memory (future intention)."""
        return self.prospective.create(trigger, action, content)

    def export_memories(self, tags: list[str] = None, ids: list[str] = None) -> dict:
        if ids:
            return self.transplant.export_package(ids)
        elif tags:
            return self.transplant.export_by_tags(tags)
        return {}

    def import_memories(self, package: dict, auto_accept: bool = False) -> list[MemoryUnit]:
        return self.transplant.import_package(package, auto_accept=auto_accept)

    def anchor(self, unit_id: str, method: str = "human_verified"):
        self.anchoring.anchor(unit_id, method)

    def status(self) -> dict:
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
        return self.narrative.wakeup_context()
