"""MemoryOrgan — stores and retrieves knowledge (Design_Doc §12.4).

Phase 5: backed by a MemoryManager — SQLite persistence, vector-similarity
retrieval, and the forgetting curve — wrapped in a VectorMemoryCell inside
the MemoryTissue, so everything upstream keeps the same interface.
"""

from incortex.cells.memory_cell import DEFAULT_TOP_K
from incortex.memory import MemoryManager, VectorMemoryCell
from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.tissues import MemoryTissue

CAPABILITIES = (
    "remember", "recall", "memory", "know", "learned", "store",
    "forget", "note", "fact", "remind",
)


class MemoryOrgan(BaseOrgan):
    def __init__(self, name="memory_organ", manager=None):
        super().__init__(name, capability_keywords=CAPABILITIES)
        self.manager = manager or MemoryManager()
        self._memory = MemoryTissue(
            memory_cells=[VectorMemoryCell(self.manager)]
        )
        self.add_tissue(self._memory, critical=True)

    def store(self, content, importance=None):
        return self._wrap(self._memory.store(content, importance))

    def retrieve(self, query, top_k=DEFAULT_TOP_K):
        return self._wrap(self._memory.retrieve(query, top_k))

    def process(self, message):
        return self._wrap(self._memory.process(message))

    def _wrap(self, tissue_output):
        return OrganOutput(
            organ_name=self.name,
            content=tissue_output.content,
            confidence=tissue_output.confidence,
            stage_outputs=(tissue_output,),
        )
