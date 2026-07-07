"""Scheduler — a starvation-free priority queue (Eq 4.3).

Priority = 0.5*urgency + 0.3*importance + 0.2*(age / age_max), recomputed
at pop time. The age term is deliberately uncapped, so any task's priority
eventually exceeds any fixed urgency/importance combination — no task
starves (math_model.md §11 property 8). Ties go to the older task.
"""

import itertools
import time
from dataclasses import dataclass
from typing import Any

URGENCY_BY_PRIORITY = {"low": 0.2, "normal": 0.5, "high": 1.0}
WEIGHT_URGENCY = 0.5
WEIGHT_IMPORTANCE = 0.3
WEIGHT_AGE = 0.2
DEFAULT_AGE_MAX_SECONDS = 60.0


@dataclass(frozen=True)
class ScheduledTask:
    payload: Any
    urgency: float
    importance: float
    submitted_at: float
    sequence: int


class Scheduler:
    def __init__(self, age_max_seconds=DEFAULT_AGE_MAX_SECONDS, clock=time.time):
        if age_max_seconds <= 0:
            raise ValueError("age_max_seconds must be positive")
        self._age_max = age_max_seconds
        self._clock = clock
        self._queue = []
        self._sequence = itertools.count()

    def submit(self, payload, urgency=0.5, importance=0.5):
        """Queue a task. Urgency accepts a number in [0,1] or a priority name."""
        if isinstance(urgency, str):
            if urgency not in URGENCY_BY_PRIORITY:
                raise ValueError(f"urgency name must be one of {list(URGENCY_BY_PRIORITY)}")
            urgency = URGENCY_BY_PRIORITY[urgency]
        for label, value in (("urgency", urgency), ("importance", importance)):
            if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{label} must be a number in [0, 1]")
        task = ScheduledTask(
            payload=payload,
            urgency=float(urgency),
            importance=float(importance),
            submitted_at=self._clock(),
            sequence=next(self._sequence),
        )
        self._queue.append(task)
        return task

    def priority(self, task):
        """Eq 4.3 — recomputed live so waiting keeps raising priority."""
        age = max(0.0, self._clock() - task.submitted_at)
        return (
            WEIGHT_URGENCY * task.urgency
            + WEIGHT_IMPORTANCE * task.importance
            + WEIGHT_AGE * (age / self._age_max)
        )

    def pop(self):
        """Remove and return the highest-priority task (older wins ties)."""
        if not self._queue:
            raise ValueError("scheduler is empty")
        best = max(self._queue, key=lambda task: (self.priority(task), -task.sequence))
        self._queue.remove(best)
        return best

    def __len__(self):
        return len(self._queue)
