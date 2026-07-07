"""LongTermMemory — durable memory records in SQLite (Design_Doc §15.2).

All queries are parameterized. Records are archived, never silently
destroyed (§25.3): archiving hides a record from normal reads while
keeping it recoverable; only an explicit delete() removes it.
"""

import json
import sqlite3
from pathlib import Path

from incortex.memory.memory_record import MemoryRecord

IN_MEMORY = ":memory:"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    importance REAL NOT NULL,
    confidence REAL NOT NULL,
    tags TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    last_accessed_at REAL NOT NULL,
    access_count INTEGER NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0
)
"""
_FIELDS = ("memory_id", "memory_type", "content", "source", "importance",
           "confidence", "tags", "created_at", "updated_at",
           "last_accessed_at", "access_count")


class LongTermMemory:
    def __init__(self, db_path=IN_MEMORY):
        path = str(db_path)
        if path != IN_MEMORY:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def save(self, record):
        """Insert or update a record; an existing archived flag is preserved."""
        if not isinstance(record, MemoryRecord):
            raise ValueError("long-term memory holds MemoryRecord instances")
        values = [getattr(record, field) for field in _FIELDS]
        values[_FIELDS.index("tags")] = json.dumps(list(record.tags))
        self._conn.execute(
            f"""INSERT OR REPLACE INTO memories ({", ".join(_FIELDS)}, archived)
                VALUES ({", ".join("?" for _ in _FIELDS)},
                        COALESCE((SELECT archived FROM memories WHERE memory_id = ?), 0))""",
            (*values, record.memory_id),
        )
        self._conn.commit()

    def get(self, memory_id):
        row = self._conn.execute(
            f"SELECT {', '.join(_FIELDS)} FROM memories WHERE memory_id = ?",
            (memory_id,),
        ).fetchone()
        return self._to_record(row) if row else None

    def all_records(self, include_archived=False):
        where = "" if include_archived else " WHERE archived = 0"
        rows = self._conn.execute(
            f"SELECT {', '.join(_FIELDS)} FROM memories{where}"
        ).fetchall()
        return [self._to_record(row) for row in rows]

    def count(self, include_archived=False):
        where = "" if include_archived else " WHERE archived = 0"
        return self._conn.execute(
            f"SELECT COUNT(*) FROM memories{where}"
        ).fetchone()[0]

    def archive(self, memory_id):
        """Hide a record from normal reads without destroying it (§25.3)."""
        cursor = self._conn.execute(
            "UPDATE memories SET archived = 1 WHERE memory_id = ?", (memory_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, memory_id):
        """Explicit, user-controlled removal (§25.3: memory must be deletable)."""
        cursor = self._conn.execute(
            "DELETE FROM memories WHERE memory_id = ?", (memory_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def close(self):
        self._conn.close()

    @staticmethod
    def _to_record(row):
        values = dict(zip(_FIELDS, row))
        values["tags"] = tuple(json.loads(values["tags"]))
        return MemoryRecord(**values)
