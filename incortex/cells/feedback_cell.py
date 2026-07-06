"""FeedbackCell — turns raw user feedback into a learning score.

Implements rating normalization (Eq 6.1) and the per-task learning score
with its high/medium/low bands (Eq 6.2). Deterministic arithmetic, so the
raw confidence of its output is always 1.0.
"""

from incortex.cells.base_cell import BaseCell
from incortex.cells.cell_math import clip01

# Eq 6.2 weights (w_s, w_r, w_c, w_p) — positive terms cap L at 0.8 by design
SUCCESS_WEIGHT = 0.4
RATING_WEIGHT = 0.4
CORRECTION_WEIGHT = 0.3
PENALTY_WEIGHT = 0.3
HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4


class FeedbackCell(BaseCell):
    """Message: {"success": bool, "rating"?: number, "rating_min"?, "rating_max"?,
    "correction_severity"?: float in [0,1], "penalty"?: bool}."""

    def __init__(self, name="feedback_cell"):
        super().__init__(name, "feedback")

    def _validate(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        if not isinstance(message.get("success"), bool):
            raise ValueError(f"{self.name}: 'success' (bool) is required")
        if "rating" in message:
            self._validate_rating(message)
        severity = message.get("correction_severity", 0.0)
        if not isinstance(severity, (int, float)) or not 0.0 <= severity <= 1.0:
            raise ValueError(f"{self.name}: correction_severity must be in [0, 1]")
        if not isinstance(message.get("penalty", False), bool):
            raise ValueError(f"{self.name}: penalty must be a bool")

    def _validate_rating(self, message):
        rating = message["rating"]
        low = message.get("rating_min", 0.0)
        high = message.get("rating_max", 1.0)
        for label, value in (("rating", rating), ("rating_min", low), ("rating_max", high)):
            if not isinstance(value, (int, float)):
                raise ValueError(f"{self.name}: {label} must be a number")
        if low >= high:
            raise ValueError(f"{self.name}: rating_min must be below rating_max")
        if not low <= rating <= high:
            raise ValueError(
                f"{self.name}: rating {rating} outside scale [{low}, {high}]"
            )

    def _process(self, message):
        success = 1.0 if message["success"] else 0.0
        if "rating" in message:
            low = message.get("rating_min", 0.0)
            high = message.get("rating_max", 1.0)
            normalized = (message["rating"] - low) / (high - low)  # Eq 6.1
        else:
            normalized = success  # no rating given: success is the satisfaction proxy
        severity = float(message.get("correction_severity", 0.0))
        penalty = 1.0 if message.get("penalty") else 0.0
        score = clip01(  # Eq 6.2
            SUCCESS_WEIGHT * success
            + RATING_WEIGHT * normalized
            - CORRECTION_WEIGHT * severity
            - PENALTY_WEIGHT * penalty
        )
        band = ("high" if score >= HIGH_THRESHOLD
                else "medium" if score >= MEDIUM_THRESHOLD else "low")
        content = {
            "learning_score": score,
            "band": band,
            "normalized_rating": normalized,
        }
        return content, 1.0
