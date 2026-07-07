"""ReasoningOrgan — thinks through problems against evidence (Design_Doc §12.5).

Runs in conservative 'min' confidence mode (math_model.md §10): a reasoning
chain is never more trustworthy than its weakest stage.
"""

from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.tissues import ReasoningTissue

CAPABILITIES = (
    "why", "how", "compare", "reason", "think", "solve",
    "decide", "conclude", "analyze", "cause",
)


class ReasoningOrgan(BaseOrgan):
    def __init__(self, name="reasoning_organ"):
        super().__init__(name, capability_keywords=CAPABILITIES, confidence_mode="min")
        self._reasoning = ReasoningTissue()
        self.add_tissue(self._reasoning, critical=True)

    def reason(self, question, evidence):
        output = self._reasoning.reason(question, evidence)
        return OrganOutput(
            organ_name=self.name,
            content=output.content,
            confidence=output.confidence,
            stage_outputs=(output,),
        )

    def process(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        return self.reason(message.get("question"), message.get("evidence", []))
