"""FeedbackEvent — one durable record of user feedback (Design_Doc §16.2)."""

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class FeedbackEvent:
    task_id: str
    success: bool
    rating: float | None
    correction: str | None
    user_comment: str | None
    created_at: float


def new_feedback_event(task_id, success, rating=None, correction=None,
                       user_comment=None, clock=time.time):
    """Build a validated FeedbackEvent stamped with the current time."""
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("task_id must be a non-empty string")
    if not isinstance(success, bool):
        raise ValueError("success must be a bool")
    if rating is not None and (not isinstance(rating, (int, float))
                               or not 0.0 <= rating <= 1.0):
        raise ValueError("rating must be a number in [0, 1]")
    return FeedbackEvent(
        task_id=task_id,
        success=success,
        rating=None if rating is None else float(rating),
        correction=correction,
        user_comment=user_comment,
        created_at=clock(),
    )
