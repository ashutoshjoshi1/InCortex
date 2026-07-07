"""MemoryRecord — one durable remembered fact (Design_Doc §15.3).

Immutable: updates (access counts, importance changes) create new copies
via dataclasses.replace, never in-place mutation.
"""

import time
import uuid
from dataclasses import dataclass

# Design_Doc §12.4 memory types.
MEMORY_TYPES = frozenset({
    "working", "short_term", "long_term", "episodic", "semantic",
    "procedural", "preference", "error", "experiment",
})


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    memory_type: str
    content: str
    source: str
    importance: float
    confidence: float
    tags: tuple
    created_at: float
    updated_at: float
    last_accessed_at: float
    access_count: int


def new_memory_record(content, memory_type="semantic", source="user",
                      importance=0.5, confidence=1.0, tags=(), clock=time.time):
    """Build a validated MemoryRecord with a fresh id and timestamps."""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("memory content must be a non-empty string")
    if memory_type not in MEMORY_TYPES:
        raise ValueError(f"memory_type must be one of {sorted(MEMORY_TYPES)}")
    for label, value in (("importance", importance), ("confidence", confidence)):
        if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
            raise ValueError(f"{label} must be a number in [0, 1]")
    now = clock()
    return MemoryRecord(
        memory_id=uuid.uuid4().hex,
        memory_type=memory_type,
        content=content.strip(),
        source=source,
        importance=float(importance),
        confidence=float(confidence),
        tags=tuple(tags),
        created_at=now,
        updated_at=now,
        last_accessed_at=now,
        access_count=0,
    )
