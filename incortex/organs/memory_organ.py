"""MemoryOrgan — stores and retrieves knowledge (Design_Doc §12.4).

Phase 3 wraps the MemoryTissue; Phase 5 adds specialized short-term,
long-term, and vector memory behind the same store/retrieve interface.
"""

from incortex.cells.memory_cell import DEFAULT_TOP_K
from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.tissues import MemoryTissue

CAPABILITIES = (
    "remember", "recall", "memory", "know", "learned", "store",
    "forget", "note", "fact", "remind",
)


class MemoryOrgan(BaseOrgan):
    def __init__(self, name="memory_organ"):
        super().__init__(name, capability_keywords=CAPABILITIES)
        self._memory = MemoryTissue()
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
