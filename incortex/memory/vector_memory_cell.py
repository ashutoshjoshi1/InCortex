"""VectorMemoryCell — the MemoryManager wearing the Cell contract.

Speaks the exact same store/retrieve message schema as the Phase 1
MemoryCell, so it slots into a MemoryTissue unchanged — but behind it sit
SQLite persistence, vector similarity, and the forgetting curve.
"""

from incortex.cells.base_cell import BaseCell
from incortex.cells.memory_cell import (
    DEFAULT_IMPORTANCE,
    DEFAULT_TOP_K,
    validate_memory_message,
)


class VectorMemoryCell(BaseCell):
    """Messages: {"action": "store", "content": str, "importance"?: float}
    or {"action": "retrieve", "query": str, "top_k"?: int}."""

    def __init__(self, manager, name="vector_memory_cell"):
        super().__init__(name, "memory")
        self._manager = manager

    def _validate(self, message):
        validate_memory_message(self.name, message)

    def _process(self, message):
        if message["action"] == "store":
            record = self._manager.remember(
                message["content"],
                importance=message.get("importance", DEFAULT_IMPORTANCE),
            )
            content = {
                "action": "store",
                "stored": record.content,
                "count": self._manager.stats()["active"],
            }
            return content, 1.0
        results = self._manager.recall(
            message["query"], top_k=message.get("top_k", DEFAULT_TOP_K)
        )
        confidence = results[0]["score"] if results else 0.0
        return {"action": "retrieve", "results": results}, confidence
