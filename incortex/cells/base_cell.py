"""BaseCell — the smallest intelligent unit in InCortex.

Implements the shared contract from Design_Doc §9.3
(receive → process → emit → learn → health_check) and the math from
docs/math_model.md §1: historical confidence (Eq 1.5), confidence
blending (Eq 1.6), EMA statistics (Eq 1.7), health score (Eq 1.8),
and status bands (Eq 1.9).
"""

import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from incortex.cells.cell_math import clip01, ema_update, status_band

# Eq 1.6 — weight of the raw per-call confidence vs. the historical track record
GAMMA_RAW_WEIGHT = 0.7
# Eq 1.7 — EMA smoothing rate for all running statistics
EMA_ALPHA = 0.1
# Eq 1.8 — health mix: success rate, confidence, latency
HEALTH_WEIGHT_SUCCESS = 0.5
HEALTH_WEIGHT_CONFIDENCE = 0.3
HEALTH_WEIGHT_LATENCY = 0.2
LATENCY_BUDGET_SECONDS = 1.0

FEEDBACK_LOG_SIZE = 100


@dataclass(frozen=True)
class CellOutput:
    """Immutable result of one process() call."""

    cell_name: str
    cell_type: str
    content: Any
    confidence: float  # blended, Eq 1.6
    raw_confidence: float


@dataclass(frozen=True)
class CellFeedback:
    """Simple learning feedback a Cell can store (Phase 1 scope)."""

    success: bool
    rating: float | None = None  # already normalized to [0, 1]
    note: str | None = None


def require_nonempty_text(cell_name, message):
    """Shared validator for text-handling Cells — fail fast at the boundary."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError(f"{cell_name}: message must be a non-empty string")


class BaseCell:
    """One Cell = one small job done well, with confidence, health, and learning."""

    def __init__(self, name, cell_type):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("cell name must be a non-empty string")
        if not isinstance(cell_type, str) or not cell_type.strip():
            raise ValueError("cell type must be a non-empty string")
        self.name = name
        self.cell_type = cell_type
        # Feedback counters for Eq 1.5
        self._feedback_successes = 0
        self._feedback_total = 0
        # EMA seeds: success starts at 1.0 (health tracks *observed* failures),
        # confidence starts neutral at 0.5 (competence must be earned),
        # latency starts at 0.0 (nothing measured yet).
        self._success_ema = 1.0
        self._confidence_ema = 0.5
        self._latency_ema = 0.0
        self._processed = 0
        self._errors = 0
        self._inbox = None
        self._last_output = None
        self._feedback_log = deque(maxlen=FEEDBACK_LOG_SIZE)

    # -- contract -----------------------------------------------------------

    def receive(self, message):
        """Validate and hold an incoming message for the next process() call."""
        if message is None:
            raise ValueError(f"{self.name}: cannot receive None")
        self._validate(message)
        self._inbox = message

    def process(self, message=None):
        """Run the Cell's job and return a CellOutput with blended confidence."""
        payload = message if message is not None else self._inbox
        if payload is None:
            raise ValueError(
                f"{self.name}: nothing to process - pass a message or call receive() first"
            )
        self._validate(payload)
        started = time.perf_counter()
        try:
            content, raw_confidence = self._process(payload)
        except Exception:
            self._errors += 1
            self._success_ema = ema_update(self._success_ema, 0.0, EMA_ALPHA)
            raise
        latency = time.perf_counter() - started
        raw_confidence = clip01(raw_confidence)
        confidence = clip01(  # Eq 1.6
            GAMMA_RAW_WEIGHT * raw_confidence
            + (1.0 - GAMMA_RAW_WEIGHT) * self.historical_confidence
        )
        self._confidence_ema = ema_update(self._confidence_ema, confidence, EMA_ALPHA)
        self._latency_ema = ema_update(self._latency_ema, latency, EMA_ALPHA)
        self._processed += 1
        self._inbox = None
        self._last_output = CellOutput(
            cell_name=self.name,
            cell_type=self.cell_type,
            content=content,
            confidence=confidence,
            raw_confidence=raw_confidence,
        )
        return self._last_output

    def emit(self):
        """Return the last output, or None if the Cell has not processed yet."""
        return self._last_output

    def learn(self, feedback):
        """Store feedback and update the Cell's track record (Eq 1.5, 1.7)."""
        record = self._coerce_feedback(feedback)
        self._feedback_total += 1
        if record.success:
            self._feedback_successes += 1
        self._success_ema = ema_update(
            self._success_ema, 1.0 if record.success else 0.0, EMA_ALPHA
        )
        self._feedback_log.append(record)
        self._learn(record)

    def accepts(self, message):
        """True if this Cell's validator would accept the message.

        Lets Tissues route messages to the right Cells (the Phase 2
        stand-in for the learned gate of Eq 2.3).
        """
        try:
            self._validate(message)
        except ValueError:
            return False
        return True

    def health_check(self):
        """Report health per Eq 1.8 and the status band per Eq 1.9."""
        health = self._health_score()
        return {
            "name": self.name,
            "type": self.cell_type,
            "status": status_band(health),
            "health": health,
            "confidence": self.historical_confidence,
            "processed": self._processed,
            "errors": self._errors,
            "feedback_count": self._feedback_total,
        }

    # -- scores -------------------------------------------------------------

    @property
    def historical_confidence(self):
        """Eq 1.5 — Beta-smoothed track record; 0.5 for a brand-new Cell."""
        return (self._feedback_successes + 1) / (self._feedback_total + 2)

    def _health_score(self):
        latency_score = 1.0 - min(1.0, self._latency_ema / LATENCY_BUDGET_SECONDS)
        return (  # Eq 1.8
            HEALTH_WEIGHT_SUCCESS * self._success_ema
            + HEALTH_WEIGHT_CONFIDENCE * self._confidence_ema
            + HEALTH_WEIGHT_LATENCY * latency_score
        )

    @staticmethod
    def _coerce_feedback(feedback):
        if isinstance(feedback, dict):
            try:
                feedback = CellFeedback(**feedback)
            except TypeError as exc:
                raise ValueError(f"invalid feedback: {exc}") from exc
        if not isinstance(feedback, CellFeedback):
            raise ValueError("feedback must be a CellFeedback or a dict")
        if not isinstance(feedback.success, bool):
            raise ValueError("feedback.success must be a bool")
        if feedback.rating is not None and not 0.0 <= float(feedback.rating) <= 1.0:
            raise ValueError("feedback.rating must be in [0, 1]")
        return feedback

    # -- subclass hooks -----------------------------------------------------

    def _validate(self, message):
        """Override to validate inputs at the boundary. Default: accept anything non-None."""

    def _process(self, message):
        """Do the Cell's one job. Return (content, raw_confidence)."""
        raise NotImplementedError

    def _learn(self, feedback):
        """Optional subclass hook — react to validated feedback."""
