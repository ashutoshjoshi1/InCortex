"""MemoryCell — Phase 1 in-memory store and retrieval.

Implements the retrieval triad of Eq 5.4 (similarity + recency + importance)
with the forgetting curve of Eq 5.2. Similarity is token-overlap (Jaccard) as
a stand-in for embedding cosine similarity until Phase 5 adds vector memory;
access-resets and importance learning (Eq 5.3) also arrive in Phase 5.
"""

import time
from dataclasses import dataclass

from incortex.cells.base_cell import BaseCell
from incortex.cells.cell_math import exponential_decay, jaccard_similarity, tokenize

# Eq 5.4 defaults: (beta_1, beta_2, beta_3)
SIMILARITY_WEIGHT = 0.6
RECENCY_WEIGHT = 0.2
IMPORTANCE_WEIGHT = 0.2
RETRIEVAL_THRESHOLD = 0.25
DEFAULT_TOP_K = 3
DEFAULT_IMPORTANCE = 0.5
# Eq 5.2 — short-term half-life default: 7 days
DEFAULT_HALF_LIFE_SECONDS = 7 * 24 * 3600.0


@dataclass(frozen=True)
class MemoryEntry:
    content: str
    tokens: frozenset
    importance: float
    stored_at: float


def validate_memory_message(cell_name, message):
    """Shared schema check for store/retrieve messages (used by the Phase 1
    MemoryCell and the Phase 5 VectorMemoryCell)."""
    if not isinstance(message, dict):
        raise ValueError(f"{cell_name}: message must be a dict")
    action = message.get("action")
    if action not in ("store", "retrieve"):
        raise ValueError(f"{cell_name}: action must be 'store' or 'retrieve'")
    key = "content" if action == "store" else "query"
    value = message.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{cell_name}: '{key}' must be a non-empty string")
    importance = message.get("importance", DEFAULT_IMPORTANCE)
    if not isinstance(importance, (int, float)) or not 0.0 <= importance <= 1.0:
        raise ValueError(f"{cell_name}: importance must be a number in [0, 1]")
    top_k = message.get("top_k", DEFAULT_TOP_K)
    if not isinstance(top_k, int) or top_k < 1:
        raise ValueError(f"{cell_name}: top_k must be a positive integer")


class MemoryCell(BaseCell):
    """Messages: {"action": "store", "content": str, "importance"?: float}
    or {"action": "retrieve", "query": str, "top_k"?: int}."""

    def __init__(self, name="memory_cell",
                 half_life_seconds=DEFAULT_HALF_LIFE_SECONDS, clock=time.time):
        super().__init__(name, "memory")
        self._half_life = half_life_seconds
        self._clock = clock
        self._entries = []

    def _validate(self, message):
        validate_memory_message(self.name, message)

    def _process(self, message):
        if message["action"] == "store":
            return self._store(message)
        return self._retrieve(message)

    def _store(self, message):
        content = message["content"].strip()
        entry = MemoryEntry(
            content=content,
            tokens=frozenset(tokenize(content)),
            importance=float(message.get("importance", DEFAULT_IMPORTANCE)),
            stored_at=self._clock(),
        )
        self._entries.append(entry)
        return {"action": "store", "stored": content, "count": len(self._entries)}, 1.0

    def _retrieve(self, message):
        query_tokens = frozenset(tokenize(message["query"]))
        now = self._clock()
        scored = []
        for entry in self._entries:
            similarity = jaccard_similarity(query_tokens, entry.tokens)
            if similarity == 0.0:
                continue  # zero overlap is never relevant, however fresh (math §5.4)
            recency = exponential_decay(now - entry.stored_at, self._half_life)
            score = (  # Eq 5.4
                SIMILARITY_WEIGHT * similarity
                + RECENCY_WEIGHT * recency
                + IMPORTANCE_WEIGHT * entry.importance
            )
            if score >= RETRIEVAL_THRESHOLD:
                scored.append((score, entry))
        scored.sort(key=lambda pair: (-pair[0], -pair[1].stored_at))
        top = scored[: message.get("top_k", DEFAULT_TOP_K)]
        results = [
            {"content": entry.content, "score": score,
             "importance": entry.importance, "stored_at": entry.stored_at}
            for score, entry in top
        ]
        confidence = results[0]["score"] if results else 0.0
        return {"action": "retrieve", "results": results}, confidence
