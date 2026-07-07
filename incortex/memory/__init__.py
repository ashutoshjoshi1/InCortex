"""The Memory layer — durable, searchable, decaying storage (Phase 5)."""

from incortex.memory.long_term import IN_MEMORY, LongTermMemory
from incortex.memory.memory_manager import MemoryManager
from incortex.memory.memory_record import MEMORY_TYPES, MemoryRecord, new_memory_record
from incortex.memory.short_term import ShortTermMemory
from incortex.memory.vector_memory import (
    HashingEmbedder,
    VectorIndex,
    content_words,
    cosine_similarity,
    similarity01,
)
from incortex.memory.vector_memory_cell import VectorMemoryCell

__all__ = [
    "HashingEmbedder",
    "IN_MEMORY",
    "LongTermMemory",
    "MEMORY_TYPES",
    "MemoryManager",
    "MemoryRecord",
    "ShortTermMemory",
    "VectorIndex",
    "VectorMemoryCell",
    "content_words",
    "cosine_similarity",
    "new_memory_record",
    "similarity01",
]
