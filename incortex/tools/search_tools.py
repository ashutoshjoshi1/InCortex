"""Search tools — looking things up is a low-risk, read-only ability."""

from incortex.cells.memory_cell import DEFAULT_TOP_K
from incortex.tools.base_tool import BaseTool


class SearchMemoryTool(BaseTool):
    name = "search_memory"
    description = "search the brain's own long-term memory"
    permission_level = 1
    harm_probability = 0.01
    impact = 0.05

    def __init__(self, manager):
        self._manager = manager

    def validate(self, request):
        super().validate(request)
        query = request.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"{self.name}: 'query' must be a non-empty string")
        top_k = request.get("top_k", DEFAULT_TOP_K)
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError(f"{self.name}: top_k must be a positive integer")

    def _execute(self, request):
        results = self._manager.recall(request["query"],
                                       top_k=request.get("top_k", DEFAULT_TOP_K))
        return {"results": results}
