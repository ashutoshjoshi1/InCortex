"""MemoryTissue — one notebook interface over one or more MemoryCells.

Stores facts into every member cell and merges retrieval results across
them (Eq 2.2 as merged ranking + Eq 5.4 per-cell scores), deduplicating
identical facts and keeping the best score. Phase 5 will populate this
tissue with specialized short-term/long-term/vector cells.
"""

from incortex.cells import MemoryCell
from incortex.cells.memory_cell import DEFAULT_TOP_K
from incortex.tissues.base_tissue import BaseTissue, TissueOutput


class MemoryTissue(BaseTissue):
    def __init__(self, name="memory_tissue", memory_cells=None):
        super().__init__(name)
        for cell in memory_cells or [MemoryCell()]:
            self.add_cell(cell, critical=True)

    def store(self, content, importance=None):
        """Write a fact into every member memory cell."""
        message = {"action": "store", "content": content}
        if importance is not None:
            message["importance"] = importance
        outputs = [cell.process(message) for cell in self.cells]
        return TissueOutput(
            tissue_name=self.name,
            content={"stored": content, "copies": len(outputs)},
            confidence=min(output.confidence for output in outputs),
            cell_outputs=tuple(outputs),
        )

    def retrieve(self, query, top_k=DEFAULT_TOP_K):
        """Query every member cell, merge, dedupe, and rank the results."""
        message = {"action": "retrieve", "query": query, "top_k": top_k}
        outputs = [cell.process(message) for cell in self.cells]
        best_by_content = {}
        for output in outputs:
            for result in output.content["results"]:
                known = best_by_content.get(result["content"])
                if known is None or result["score"] > known["score"]:
                    best_by_content[result["content"]] = result
        merged = sorted(
            best_by_content.values(),
            key=lambda result: (-result["score"], -result["stored_at"]),
        )[:top_k]
        confidence = merged[0]["score"] if merged else 0.0
        return TissueOutput(
            tissue_name=self.name,
            content={"results": merged},
            confidence=confidence,
            cell_outputs=tuple(outputs),
        )

    def process(self, message):
        """Dispatch a MemoryCell-style message at the tissue level."""
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        action = message.get("action")
        if action == "store":
            return self.store(message.get("content"), message.get("importance"))
        if action == "retrieve":
            return self.retrieve(message.get("query"), message.get("top_k", DEFAULT_TOP_K))
        raise ValueError(f"{self.name}: action must be 'store' or 'retrieve'")
