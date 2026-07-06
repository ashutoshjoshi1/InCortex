"""LearningTissue — scores feedback events and spreads them to other Cells.

Wraps the FeedbackCell (Eq 6.1-6.2), keeps an EMA of learning scores so
the system can see whether it is improving (Eq 1.7), and distributes each
event as CellFeedback to any cells that took part in the task — the first
piece of Design_Doc §16's learning loop.
"""

from incortex.cells import CellFeedback, FeedbackCell
from incortex.cells.base_cell import EMA_ALPHA
from incortex.cells.cell_math import ema_update
from incortex.tissues.base_tissue import BaseTissue, TissueOutput


class LearningTissue(BaseTissue):
    def __init__(self, name="learning_tissue"):
        super().__init__(name)
        self._feedback = FeedbackCell()
        self.add_cell(self._feedback, critical=True)
        self._running_score = None
        self._events = 0

    def process(self, message):
        """Score one feedback event and update the running learning score."""
        output = self._feedback.process(message)
        score = output.content["learning_score"]
        self._running_score = (
            score if self._running_score is None
            else ema_update(self._running_score, score, EMA_ALPHA)
        )
        self._events += 1
        content = {
            **output.content,
            "running_score": self._running_score,
            "events": self._events,
        }
        return TissueOutput(
            tissue_name=self.name,
            content=content,
            confidence=output.confidence,
            cell_outputs=(output,),
        )

    def distribute(self, message, cells):
        """Score the event, then teach it to every cell that took part."""
        result = self.process(message)
        feedback = CellFeedback(
            success=message["success"],
            rating=result.content["normalized_rating"],
        )
        for cell in cells:
            cell.learn(feedback)
        return result
