"""ShortTermMemory — a bounded buffer of the most recent memories.

The working end of the memory system (Design_Doc §12.4): newest first,
oldest silently evicted at capacity. Durability lives in long_term.py.
"""

from collections import deque

from incortex.memory.memory_record import MemoryRecord

DEFAULT_CAPACITY = 100  # Design_Doc §24: max_short_term_items


class ShortTermMemory:
    def __init__(self, capacity=DEFAULT_CAPACITY):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self._items = deque(maxlen=capacity)

    def add(self, record):
        if not isinstance(record, MemoryRecord):
            raise ValueError("short-term memory holds MemoryRecord instances")
        self._items.append(record)

    def recent(self, count=None):
        """The newest records first."""
        items = tuple(reversed(self._items))
        return items if count is None else items[:count]

    def clear(self):
        self._items.clear()

    def __len__(self):
        return len(self._items)
