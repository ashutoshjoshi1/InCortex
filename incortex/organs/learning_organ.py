"""LearningOrgan — the heart of self-improvement (Design_Doc §12.7).

Phase 5: every scored event also lands in the durable LearningLog, and
failures feed the MistakeTracker, whose recurring clusters the Cortex
escalates into remembered weaknesses (§16.4).
"""

from incortex.learning import LearningLog, MistakeTracker
from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.tissues import LearningTissue

CAPABILITIES = (
    "feedback", "good", "bad", "wrong", "right", "better",
    "worse", "improve", "correct", "rating",
)


class LearningOrgan(BaseOrgan):
    def __init__(self, name="learning_organ", log=None, tracker=None):
        super().__init__(name, capability_keywords=CAPABILITIES)
        self._learning = LearningTissue()
        self.add_tissue(self._learning, critical=True)
        self.log = log if log is not None else LearningLog()
        self.tracker = tracker if tracker is not None else MistakeTracker()

    def score(self, feedback_message, description=None):
        """Score one feedback event, log it, and track any mistake."""
        output = self._learning.process(feedback_message)
        self._record(feedback_message, output, description)
        return self._wrap(output)

    def distribute(self, feedback_message, cells, description=None):
        """Score, log, track — then teach every participating cell."""
        output = self._learning.distribute(feedback_message, cells)
        self._record(feedback_message, output, description)
        return self._wrap(output)

    def process(self, message):
        return self.score(message)

    def _record(self, message, tissue_output, description):
        content = tissue_output.content
        self.log.record({
            "success": message["success"],
            "rating": message.get("rating"),
            "description": description,
            "learning_score": content["learning_score"],
            "band": content["band"],
        })
        self.tracker.record(message["success"], description)

    def _wrap(self, tissue_output):
        return OrganOutput(
            organ_name=self.name,
            content=tissue_output.content,
            confidence=tissue_output.confidence,
            stage_outputs=(tissue_output,),
        )
