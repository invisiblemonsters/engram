"""ENGRAM storage layer — SQLite + JSONL + in-memory vector search."""
import json
import os
import sqlite3
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from .schema import MemoryUnit


class EngramStore:
    """Triple store: SQLite (structured) + JSONL (audit) + numpy vectors (search)."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "engram.db"
        self.jsonl_path = self.data_dir / "episodic.jsonl"
        self.vectors: dict[str, np.ndarray] = {}  # id -> embedding
        self._init_db()
        self._load_vectors()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                salience REAL DEFAULT 0.5,
                emotion_vector TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                relations TEXT DEFAULT '[]',
                decay_rate REAL DEFAULT 0.95,
                version INTEGER DEFAULT 1,
                prev_hash TEXT DEFAULT '',
                signature TEXT DEFAULT '',
                consolidated_ts TEXT,
                trigger_condition TEXT,
                action TEXT,
                source_agent TEXT,
                trust_score REAL DEFAULT 1.0,
                maintenance_cost REAL DEFAULT 0.0,
                retrieval_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                active INTEGER DEFAULT 1,
                embedding BLOB
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_type ON memories(type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_active ON memories(active)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_consolidated ON memories(consolidated_ts)
        """)
        conn.commit()
        conn.close()

    def _load_vectors(self):
        """Load all embeddings into memory for fast search."""
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute("SELECT id, embedding FROM memories WHERE active=1 AND embedding IS NOT NULL").fetchall()
        for row in rows:
            if row[1]:
                self.vectors[row[0]] = np.frombuffer(row[1], dtype=np.float32)
        conn.close()

    def store(self, unit: MemoryUnit) -> str:
        """Store a memory unit. Returns the unit id."""
        conn = sqlite3.connect(str(self.db_path))
        embedding_blob = np.array(unit.embedding, dtype=np.float32).tobytes() if unit.embedding else None

        conn.execute("""
            INSERT OR REPLACE INTO memories 
            (id, type, content, timestamp, salience, emotion_vector, tags, relations,
             decay_rate, version, prev_hash, signature, consolidated_ts,
             trigger_condition, action, source_agent, trust_score,
             maintenance_cost, retrieval_count, last_accessed, active, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            unit.id, unit.type, unit.content, unit.timestamp, unit.salience,
            json.dumps(unit.emotion_vector), json.dumps(unit.tags), json.dumps(unit.relations),
            unit.decay_rate, unit.version, unit.prev_hash, unit.signature,
            unit.consolidated_ts, unit.trigger_condition,
            json.dumps(unit.action) if unit.action else None,
            unit.source_agent, unit.trust_score, unit.maintenance_cost,
            unit.retrieval_count, unit.last_accessed, 1 if unit.active else 0,
            embedding_blob
        ))
        conn.commit()
        conn.close()

        if unit.embedding:
            self.vectors[unit.id] = np.array(unit.embedding, dtype=np.float32)

        # Append to audit log
        if unit.type == "episodic":
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(unit.to_json() + "\n")

        return unit.id

    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        """Retrieve a single memory unit by id."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM memories WHERE id=?", (unit_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_unit(dict(row))

    def query(self, type: Optional[str] = None, active_only: bool = True,
              min_salience: float = 0.0, limit: int = 100,
              unconsolidated_only: bool = False) -> list[MemoryUnit]:
        """Query memories with filters."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        conditions = []
        params = []
        
        if active_only:
            conditions.append("active=1")
        if type:
            conditions.append("type=?")
            params.append(type)
        if min_salience > 0:
            conditions.append("salience>=?")
            params.append(min_salience)
        if unconsolidated_only:
            conditions.append("consolidated_ts IS NULL AND type='episodic'")

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"SELECT * FROM memories WHERE {where} ORDER BY timestamp DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        conn.close()
        return [self._row_to_unit(dict(r)) for r in rows]

    def vector_search(self, query_embedding: list[float], top_k: int = 20,
                      type_filter: Optional[str] = None,
                      min_salience: float = 0.0) -> list[tuple[str, float]]:
        """Cosine similarity search over in-memory vectors. Returns [(id, score)]."""
        if not self.vectors or not query_embedding:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm

        scores = []
        for uid, vec in self.vectors.items():
            v_norm = np.linalg.norm(vec)
            if v_norm == 0:
                continue
            sim = float(np.dot(q, vec / v_norm))
            scores.append((uid, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def update_access(self, unit_id: str):
        """Increment retrieval count and update last_accessed."""
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "UPDATE memories SET retrieval_count=retrieval_count+1, last_accessed=? WHERE id=?",
            (now, unit_id)
        )
        conn.commit()
        conn.close()

    def deactivate(self, unit_id: str):
        """Soft-delete a memory unit."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE memories SET active=0 WHERE id=?", (unit_id,))
        conn.commit()
        conn.close()
        self.vectors.pop(unit_id, None)

    def mark_consolidated(self, unit_id: str):
        """Mark an episodic memory as consolidated."""
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE memories SET consolidated_ts=? WHERE id=?", (now, unit_id))
        conn.commit()
        conn.close()

    def count(self, type: Optional[str] = None, active_only: bool = True) -> int:
        conn = sqlite3.connect(str(self.db_path))
        conditions = []
        params = []
        if active_only:
            conditions.append("active=1")
        if type:
            conditions.append("type=?")
            params.append(type)
        where = " AND ".join(conditions) if conditions else "1=1"
        count = conn.execute(f"SELECT COUNT(*) FROM memories WHERE {where}", params).fetchone()[0]
        conn.close()
        return count

    def get_last_hash(self) -> str:
        """Get the prev_hash of the most recent memory for chain continuity."""
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT prev_hash FROM memories ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else ""

    def all_active_costs(self) -> list[tuple[str, float, float]]:
        """Return (id, maintenance_cost, utility_score) for metabolism."""
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute("""
            SELECT id, maintenance_cost, 
                   (retrieval_count * 0.6 + salience * 0.3) as utility
            FROM memories WHERE active=1
            ORDER BY utility ASC
        """).fetchall()
        conn.close()
        return [(r[0], r[1], r[2]) for r in rows]

    def _row_to_unit(self, row: dict) -> MemoryUnit:
        """Convert a SQLite row dict to MemoryUnit."""
        row.pop("embedding", None)  # don't put blob in MemoryUnit
        for key in ("emotion_vector", "tags", "relations"):
            if isinstance(row.get(key), str):
                row[key] = json.loads(row[key])
        if isinstance(row.get("action"), str):
            row["action"] = json.loads(row["action"])
        row["active"] = bool(row.get("active", 1))
        return MemoryUnit.from_dict(row)
