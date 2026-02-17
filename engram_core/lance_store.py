"""ENGRAM LanceDB Storage Layer (v0.9.1)
Replaces SQLite + numpy with LanceDB for vector + metadata in one store.
Same API as EngramStore for drop-in replacement.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import lancedb
import numpy as np
import pyarrow as pa

from .schema import MemoryUnit


class LanceStore:
    """LanceDB-backed store. Replaces SQLite + numpy vectors."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.data_dir / "episodic.jsonl"

        db_path = str(self.data_dir / "lancedb")
        self.db = lancedb.connect(db_path)

        try:
            resp = self.db.list_tables()
            tables = resp.tables if hasattr(resp, 'tables') else list(resp)
        except Exception:
            tables = []
        if "memories" in tables:
            self.table = self.db.open_table("memories")
            self._has_schema_version = "schema_version" in [f.name for f in self.table.schema]
        else:
            self.table = None  # created on first store()
            self._has_schema_version = True  # new tables will have it

    def _ensure_table(self, embedding_dim: int = 384):
        """Create table if it doesn't exist."""
        if self.table is not None:
            return
        # Double-check (race condition guard)
        try:
            resp = self.db.list_tables()
            tables = resp.tables if hasattr(resp, 'tables') else list(resp)
            if "memories" in tables:
                self.table = self.db.open_table("memories")
                return
        except Exception:
            pass
        schema = pa.schema([
            ("id", pa.string()),
            ("type", pa.string()),
            ("content", pa.string()),
            ("timestamp", pa.string()),
            ("salience", pa.float32()),
            ("emotion_vector", pa.string()),
            ("tags", pa.string()),
            ("relations", pa.string()),
            ("decay_rate", pa.float32()),
            ("version", pa.int32()),
            ("prev_hash", pa.string()),
            ("signature", pa.string()),
            ("consolidated_ts", pa.string()),
            ("trigger_condition", pa.string()),
            ("action", pa.string()),
            ("source_agent", pa.string()),
            ("trust_score", pa.float32()),
            ("maintenance_cost", pa.float32()),
            ("retrieval_count", pa.int32()),
            ("last_accessed", pa.string()),
            ("active", pa.bool_()),
            ("schema_version", pa.int32()),
            ("vector", pa.list_(pa.float32(), embedding_dim)),
        ])
        self.table = self.db.create_table("memories", schema=schema)

    def _unit_to_row(self, unit: MemoryUnit) -> dict:
        """Convert MemoryUnit to LanceDB row."""
        row = {
            "id": unit.id,
            "type": unit.type,
            "content": unit.content,
            "timestamp": unit.timestamp,
            "salience": float(unit.salience),
            "emotion_vector": json.dumps(unit.emotion_vector),
            "tags": json.dumps(unit.tags),
            "relations": json.dumps(unit.relations),
            "decay_rate": float(unit.decay_rate),
            "version": int(unit.version),
            "prev_hash": unit.prev_hash or "",
            "signature": unit.signature or "",
            "consolidated_ts": unit.consolidated_ts or "",
            "trigger_condition": unit.trigger_condition or "",
            "action": json.dumps(unit.action) if unit.action else "",
            "source_agent": unit.source_agent or "",
            "trust_score": float(unit.trust_score),
            "maintenance_cost": float(unit.maintenance_cost),
            "retrieval_count": int(unit.retrieval_count),
            "last_accessed": unit.last_accessed or "",
            "active": bool(unit.active),
            "vector": unit.embedding if unit.embedding else [0.0] * 384,
        }
        if self._has_schema_version:
            row["schema_version"] = int(unit.schema_version)
        return row

    def _row_to_unit(self, row: dict) -> MemoryUnit:
        """Convert LanceDB row to MemoryUnit."""
        d = dict(row)
        # Remove lance vector column, put in embedding
        embedding = d.pop("vector", [])
        d["embedding"] = list(embedding) if embedding is not None else []

        # Parse JSON strings back
        for key in ("emotion_vector", "tags", "relations"):
            val = d.get(key)
            if isinstance(val, str) and val:
                try:
                    d[key] = json.loads(val)
                except json.JSONDecodeError:
                    d[key] = []
            elif not val:
                d[key] = []

        if isinstance(d.get("action"), str) and d["action"]:
            try:
                d["action"] = json.loads(d["action"])
            except json.JSONDecodeError:
                d["action"] = None
        elif not d.get("action"):
            d["action"] = None

        # Handle empty strings as None
        for key in ("consolidated_ts", "trigger_condition", "source_agent"):
            if d.get(key) == "":
                d[key] = None

        d["active"] = bool(d.get("active", True))
        d.setdefault("schema_version", 1)

        return MemoryUnit.from_dict(d)

    def store(self, unit: MemoryUnit) -> str:
        """Store a memory unit. Returns the unit id."""
        dim = len(unit.embedding) if unit.embedding else 384
        self._ensure_table(dim)

        # Check if exists (update)
        try:
            existing = self.table.search().where(f"id = '{unit.id}'").limit(1).to_list()
            if existing:
                self.table.delete(f"id = '{unit.id}'")
        except Exception:
            pass

        row = self._unit_to_row(unit)
        self.table.add([row])

        # Append to audit log
        if unit.type == "episodic":
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(unit.to_json() + "\n")

        return unit.id

    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        """Retrieve a single memory unit by id."""
        if self.table is None:
            return None
        try:
            rows = self.table.search().where(f"id = '{unit_id}'").limit(1).to_list()
            if rows:
                return self._row_to_unit(rows[0])
        except Exception:
            pass
        return None

    def query(self, type: Optional[str] = None, active_only: bool = True,
              min_salience: float = 0.0, limit: int = 100,
              unconsolidated_only: bool = False) -> list[MemoryUnit]:
        """Query memories with filters."""
        if self.table is None:
            return []

        conditions = []
        if active_only:
            conditions.append("active = true")
        if type:
            conditions.append(f"type = '{type}'")
        if min_salience > 0:
            conditions.append(f"salience >= {min_salience}")
        if unconsolidated_only:
            conditions.append("consolidated_ts = '' AND type = 'episodic'")

        where = " AND ".join(conditions) if conditions else None

        try:
            q = self.table.search().limit(limit)
            if where:
                q = q.where(where)
            rows = q.to_list()
            units = [self._row_to_unit(r) for r in rows]
            # Sort by timestamp desc
            units.sort(key=lambda u: u.timestamp, reverse=True)
            return units[:limit]
        except Exception as e:
            print(f"[ENGRAM] LanceDB query error: {e}")
            return []

    def vector_search(self, query_embedding: list[float], top_k: int = 20,
                      type_filter: Optional[str] = None,
                      min_salience: float = 0.0) -> list[tuple[str, float]]:
        """Vector similarity search. Returns [(id, score)]."""
        if self.table is None or not query_embedding:
            return []

        try:
            q = self.table.search(query_embedding).limit(top_k).metric("cosine")
            if type_filter:
                q = q.where(f"type = '{type_filter}' AND active = true")
            else:
                q = q.where("active = true")

            rows = q.to_list()
            # LanceDB returns _distance (lower = more similar for cosine)
            # Convert to similarity score: 1 - distance
            results = []
            for r in rows:
                dist = r.get("_distance", 1.0)
                sim = 1.0 - dist
                results.append((r["id"], sim))
            return results
        except Exception as e:
            print(f"[ENGRAM] LanceDB vector search error: {e}")
            return []

    def update_access(self, unit_id: str):
        """Increment retrieval count and update last_accessed."""
        unit = self.get(unit_id)
        if unit:
            unit.retrieval_count += 1
            unit.last_accessed = datetime.now(timezone.utc).isoformat()
            self.store(unit)

    def deactivate(self, unit_id: str):
        """Soft-delete a memory unit."""
        unit = self.get(unit_id)
        if unit:
            unit.active = False
            self.store(unit)

    def mark_consolidated(self, unit_id: str):
        """Mark an episodic memory as consolidated."""
        unit = self.get(unit_id)
        if unit:
            unit.consolidated_ts = datetime.now(timezone.utc).isoformat()
            self.store(unit)

    def count(self, type: Optional[str] = None, active_only: bool = True) -> int:
        if self.table is None:
            return 0
        try:
            conditions = []
            if active_only:
                conditions.append("active = true")
            if type:
                conditions.append(f"type = '{type}'")
            where = " AND ".join(conditions) if conditions else None

            if where:
                return len(self.table.search().where(where).limit(100000).to_list())
            else:
                return self.table.count_rows()
        except Exception:
            return 0

    def get_last_hash(self) -> str:
        """Get the prev_hash of the most recent memory."""
        if self.table is None:
            return ""
        try:
            rows = self.table.search().limit(1).to_list()
            if rows:
                # Sort by timestamp to find latest
                all_rows = self.table.search().limit(100000).to_list()
                all_rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
                return all_rows[0].get("prev_hash", "") if all_rows else ""
        except Exception:
            pass
        return ""

    def all_active_costs(self) -> list[tuple[str, float, float]]:
        """Return (id, maintenance_cost, utility_score) for metabolism."""
        if self.table is None:
            return []
        try:
            rows = self.table.search().where("active = true").limit(100000).to_list()
            results = []
            for r in rows:
                cost = r.get("maintenance_cost", 0.0)
                utility = r.get("retrieval_count", 0) * 0.6 + r.get("salience", 0.5) * 0.3
                results.append((r["id"], cost, utility))
            results.sort(key=lambda x: x[2])
            return results
        except Exception:
            return []
