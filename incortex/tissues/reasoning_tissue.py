"""ReasoningTissue — chain reasoning over evidence as a tissue.

Phase 3 wraps a single ReasoningCell (critical). Later phases add cells for
different reasoning modes with gated selection (Eq 2.3) — the tissue-level
interface stays the same.
"""

from incortex.cells import ReasoningCell
from incortex.tissues.base_tissue import BaseTissue, TissueOutput


class ReasoningTissue(BaseTissue):
    def __init__(self, name="reasoning_tissue"):
        super().__init__(name)
        self._reasoner = ReasoningCell()
        self.add_cell(self._reasoner, critical=True)

    def reason(self, question, evidence):
        """Think through a question against retrieved evidence."""
        output = self._reasoner.process({"question": question, "evidence": evidence})
        return TissueOutput(
            tissue_name=self.name,
            content=output.content,
            confidence=output.confidence,
            cell_outputs=(output,),
        )

    def process(self, message):
        """Accept the same dict messages as the ReasoningCell."""
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        return self.reason(message.get("question"), message.get("evidence", []))
