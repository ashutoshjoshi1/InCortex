"""TaskContext and SystemState — the Cortex's working memory about itself.

TaskContext is the case file for one request: what was asked, which organs
took part, each stage's confidence, and the final verdict. SystemState is
the long-running scoreboard: EMA-smoothed statistics (Eq 1.7) and the last
context per session (so feedback can find who to teach).
"""

from dataclasses import dataclass, field

from incortex.cells.base_cell import EMA_ALPHA
from incortex.cells.cell_math import clip01, ema_update, pipeline_confidence


@dataclass
class TaskContext:
    """Accumulating record of one request's journey through the brain."""

    task_id: str
    session_id: str
    raw_text: str
    cleaned_text: str = ""
    intent: str = ""
    stages: list = field(default_factory=list)  # (stage_name, confidence)
    organs_used: list = field(default_factory=list)
    memory_results: list = field(default_factory=list)
    reply: str = ""
    chain_confidence: float = 0.0
    accepted: bool = False

    def add_stage(self, name, confidence):
        self.stages.append((name, clip01(confidence)))

    def use_organ(self, organ_name):
        if organ_name not in self.organs_used:
            self.organs_used.append(organ_name)

    def chain(self):
        """Eq 3.1 — geometric-mean confidence across all recorded stages."""
        if not self.stages:
            return 0.0
        return pipeline_confidence([confidence for _, confidence in self.stages])


class SystemState:
    """EMA-smoothed system statistics and per-session bookkeeping."""

    def __init__(self):
        self._tasks_handled = 0
        self._accepted = 0
        self._confidence_ema = None
        self._learning_ema = None
        self._sessions = {}

    def record_task(self, context):
        self._tasks_handled += 1
        if context.accepted:
            self._accepted += 1
        self._confidence_ema = self._smooth(self._confidence_ema,
                                            context.chain_confidence)
        self._sessions[context.session_id] = context

    def record_learning(self, score):
        self._learning_ema = self._smooth(self._learning_ema, score)

    def last_context(self, session_id):
        return self._sessions.get(session_id)

    def snapshot(self):
        acceptance = (self._accepted / self._tasks_handled
                      if self._tasks_handled else None)
        return {
            "tasks_handled": self._tasks_handled,
            "acceptance_rate": acceptance,
            "confidence_ema": self._confidence_ema,
            "learning_ema": self._learning_ema,
            "sessions": len(self._sessions),
        }

    @staticmethod
    def _smooth(previous, sample):
        """Eq 1.7 — the first sample seeds the average."""
        return sample if previous is None else ema_update(previous, sample, EMA_ALPHA)
