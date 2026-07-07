"""LearningOrgan — the heart of self-improvement (Design_Doc §12.7).

Phase 3 wraps the LearningTissue: scores feedback events (Eq 6.1-6.2),
tracks the running learning score (Eq 1.7), and spreads feedback to every
cell that took part in a task.
"""

from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.tissues import LearningTissue

CAPABILITIES = (
    "feedback", "good", "bad", "wrong", "right", "better",
    "worse", "improve", "correct", "rating",
)


class LearningOrgan(BaseOrgan):
    def __init__(self, name="learning_organ"):
        super().__init__(name, capability_keywords=CAPABILITIES)
        self._learning = LearningTissue()
        self.add_tissue(self._learning, critical=True)

    def score(self, feedback_message):
        """Score one feedback event and update the running average."""
        return self._wrap(self._learning.process(feedback_message))

    def distribute(self, feedback_message, cells):
        """Score the event, then teach it to every participating cell."""
        return self._wrap(self._learning.distribute(feedback_message, cells))

    def process(self, message):
        return self.score(message)

    def _wrap(self, tissue_output):
        return OrganOutput(
            organ_name=self.name,
            content=tissue_output.content,
            confidence=tissue_output.confidence,
            stage_outputs=(tissue_output,),
        )
