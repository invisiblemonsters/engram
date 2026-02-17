"""ENGRAM Memory Unit schema and types."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional


MEMORY_TYPES = ("episodic", "semantic", "procedural", "insight", "prospective", "narrative")
RELATION_TYPES = ("causes", "contradicts", "supports", "supersedes", "inspired_by", "related_to")
EMOTION_DIMS = ("joy", "frustration", "curiosity", "anger", "surprise", "satisfaction", "fear", "calm")


@dataclass
class Relation:
    target_id: str
    relation: str  # one of RELATION_TYPES
    strength: float = 0.8

    def to_dict(self):
        return {"target_id": self.target_id, "relation": self.relation, "strength": self.strength}


@dataclass
class MemoryUnit:
    content: str
    type: str = "episodic"  # one of MEMORY_TYPES
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    embedding: list = field(default_factory=list)
    salience: float = 0.5
    emotion_vector: list = field(default_factory=lambda: [0.0] * 8)
    tags: list = field(default_factory=list)
    relations: list = field(default_factory=list)  # list of Relation dicts
    decay_rate: float = 0.95
    version: int = 1
    prev_hash: str = ""
    signature: str = ""
    consolidated_ts: Optional[str] = None
    trigger_condition: Optional[str] = None
    action: Optional[dict] = None
    source_agent: Optional[str] = None
    trust_score: float = 1.0
    maintenance_cost: float = 0.0
    retrieval_count: int = 0
    last_accessed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active: bool = True

    def content_hash(self) -> str:
        """SHA-256 of content + timestamp + prev_hash for chain integrity."""
        payload = f"{self.id}|{self.content}|{self.timestamp}|{self.prev_hash}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def compute_maintenance_cost(self, age_days: float = 0) -> float:
        """Metabolic cost: tokens * salience * 1.2^age."""
        token_estimate = len(self.content.split()) * 1.3  # rough token count
        self.maintenance_cost = token_estimate * self.salience * (1.2 ** age_days)
        return self.maintenance_cost

    def utility_score(self, days_window: int = 30) -> float:
        """Utility = retrieval_count*0.6 + salience*0.3 + len(relations)*0.1."""
        graph_degree = len(self.relations) if self.relations else 0
        return (self.retrieval_count * 0.6 + self.salience * 0.3 + min(graph_degree, 10) * 0.01)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryUnit":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, s: str) -> "MemoryUnit":
        return cls.from_dict(json.loads(s))
