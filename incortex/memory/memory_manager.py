"""MemoryManager — the memory system's front door (Design_Doc §15).

Orchestrates the three stores: every remembered fact goes to long-term
SQLite (durable), the vector index (findable), and short-term memory
(recent). Recall runs the Eq 5.4 triad — similarity + recency + importance
— with the forgetting curve of Eq 5.2, and accessing a memory resets its
decay clock, as in biology. Cleanup archives by retention (Eq 5.5); it
never destroys.
"""

import time
from dataclasses import replace

from incortex.cells.cell_math import exponential_decay
from incortex.memory.long_term import IN_MEMORY, LongTermMemory
from incortex.memory.memory_record import new_memory_record
from incortex.memory.short_term import DEFAULT_CAPACITY, ShortTermMemory
from incortex.memory.vector_memory import HashingEmbedder, VectorIndex

# Eq 5.4 defaults (beta_1, beta_2, beta_3) and thresholds
SIMILARITY_WEIGHT = 0.6
RECENCY_WEIGHT = 0.2
IMPORTANCE_WEIGHT = 0.2
RETRIEVAL_THRESHOLD = 0.25
# Freshness must never resurrect irrelevant memories: recency + importance
# alone can exceed the score threshold, so similarity has its own floor
# (Eq 5.4 as amended). Hash noise sits near 0.03; real matches near 0.4+.
SIMILARITY_FLOOR = 0.1
DEFAULT_TOP_K = 3
# Eq 5.2 — 7-day half-life for recency
DEFAULT_HALF_LIFE_SECONDS = 7 * 24 * 3600.0


class MemoryManager:
    def __init__(self, db_path=IN_MEMORY, half_life_seconds=DEFAULT_HALF_LIFE_SECONDS,
                 short_term_capacity=DEFAULT_CAPACITY, clock=time.time,
                 embedder=None):
        self._clock = clock
        self._half_life = half_life_seconds
        self.long_term = LongTermMemory(db_path)
        self.short_term = ShortTermMemory(short_term_capacity)
        self._index = VectorIndex(embedder or HashingEmbedder())
        # Rebuild the vector index from durable storage — the embedder is
        # deterministic, so a restart reconstructs identical vectors.
        for record in self.long_term.all_records():
            self._index.add(record.memory_id, record.content)

    def remember(self, content, memory_type="semantic", source="user",
                 importance=0.5, confidence=1.0, tags=()):
        """Store one fact in all three stores; returns the new record."""
        record = new_memory_record(content, memory_type=memory_type,
                                   source=source, importance=importance,
                                   confidence=confidence, tags=tags,
                                   clock=self._clock)
        self.long_term.save(record)
        self._index.add(record.memory_id, record.content)
        self.short_term.add(record)
        return record

    def recall(self, query, top_k=DEFAULT_TOP_K):
        """Eq 5.4 — retrieve the top-k records above the score threshold.

        Accessing a memory resets its forgetting clock (Eq 5.2).
        """
        now = self._clock()
        scored = []
        for memory_id, similarity in self._index.similarities(query).items():
            if similarity < SIMILARITY_FLOOR:
                continue
            record = self.long_term.get(memory_id)
            if record is None:
                continue
            recency = exponential_decay(now - record.last_accessed_at,
                                        self._half_life)
            score = (SIMILARITY_WEIGHT * similarity
                     + RECENCY_WEIGHT * recency
                     + IMPORTANCE_WEIGHT * record.importance)
            if score >= RETRIEVAL_THRESHOLD:
                scored.append((score, similarity, record))
        scored.sort(key=lambda item: (-item[0], -item[2].created_at))
        top = scored[:top_k]
        results = []
        for score, similarity, record in top:
            touched = replace(record, last_accessed_at=now, updated_at=now,
                              access_count=record.access_count + 1)
            self.long_term.save(touched)
            results.append({
                "memory_id": record.memory_id,
                "content": record.content,
                "score": score,
                "similarity": similarity,
                "importance": record.importance,
                "memory_type": record.memory_type,
                "stored_at": record.created_at,
            })
        return results

    def reinforce(self, memory_id, delta=0.1):
        """Raise a memory's importance — the Eq 5.3 'impact' factor in action."""
        record = self.long_term.get(memory_id)
        if record is None:
            raise ValueError(f"no memory with id '{memory_id}'")
        boosted = replace(record,
                          importance=min(1.0, record.importance + delta),
                          updated_at=self._clock())
        self.long_term.save(boosted)
        return boosted

    def forget(self, memory_id):
        """Explicit, user-controlled deletion (§25.3)."""
        self._index.remove(memory_id)
        return self.long_term.delete(memory_id)

    def cleanup(self, budget):
        """Eq 5.5 — archive the lowest-retention records beyond the budget."""
        records = self.long_term.all_records()
        if len(records) <= budget:
            return 0
        now = self._clock()
        by_retention = sorted(
            records,
            key=lambda record: record.importance * exponential_decay(
                now - record.last_accessed_at, self._half_life),
            reverse=True,
        )
        archived = 0
        for record in by_retention[budget:]:
            if self.long_term.archive(record.memory_id):
                self._index.remove(record.memory_id)
                archived += 1
        return archived

    def stats(self):
        return {
            "active": self.long_term.count(),
            "archived": (self.long_term.count(include_archived=True)
                         - self.long_term.count()),
            "short_term": len(self.short_term),
        }

    def close(self):
        self.long_term.close()
