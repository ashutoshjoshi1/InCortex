"""SafetyCell — the permission gate every risky action must pass.

Implements risk = likelihood x impact (Eq 7.1) and the gate of Eq 7.2 with
deterministic precedence: execute, then require_approval, then block. The
gate is fail-closed: a missing harm or impact estimate is treated as the
worst case (1.0), so unknown risk can never slip through as low risk.
"""

from incortex.cells.base_cell import BaseCell
from incortex.cells.cell_math import clip01

TAU_RISK = 0.3               # Eq 7.2 risk threshold
DEFAULT_MAX_AUTO_LEVEL = 2   # L_max: highest level allowed without a human
ALWAYS_APPROVAL_LEVEL = 4    # Design_Doc §12.9: levels 4-5 always need a human
WORST_CASE = 1.0             # fail-closed default for missing estimates
PERMISSION_LEVELS = range(6)


class SafetyCell(BaseCell):
    """Message: {"action": str, "permission_level": 0-5,
    "harm_probability"?: float, "impact"?: float}."""

    def __init__(self, name="safety_cell", max_auto_level=DEFAULT_MAX_AUTO_LEVEL):
        super().__init__(name, "safety")
        self._max_auto_level = max_auto_level

    def _validate(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        action = message.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ValueError(f"{self.name}: 'action' must be a non-empty string")
        level = message.get("permission_level")
        if isinstance(level, bool) or not isinstance(level, int) or level not in PERMISSION_LEVELS:
            raise ValueError(f"{self.name}: 'permission_level' must be an integer 0-5")
        for key in ("harm_probability", "impact"):
            if key in message:
                value = message[key]
                if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                    raise ValueError(f"{self.name}: '{key}' must be a number in [0, 1]")

    def _process(self, message):
        level = message["permission_level"]
        assumed = "harm_probability" not in message or "impact" not in message
        harm = message.get("harm_probability", WORST_CASE)  # fail-closed
        impact = message.get("impact", WORST_CASE)
        risk = clip01(harm * impact)  # Eq 7.1

        # Eq 7.2, precedence: execute -> require_approval -> block.
        # This ordering matches Design_Doc §26.3: risky or high-tier actions go
        # to a human; only safe-but-over-ceiling actions are silently blocked.
        if level <= self._max_auto_level and risk < TAU_RISK:
            decision = "execute"
            reason = (f"level {level} within ceiling {self._max_auto_level} "
                      f"and risk {risk:.2f} < {TAU_RISK}")
        elif level >= ALWAYS_APPROVAL_LEVEL:
            decision = "require_approval"
            reason = f"level {level} actions always require a human"
        elif risk >= TAU_RISK:
            decision = "require_approval"
            reason = f"risk {risk:.2f} >= {TAU_RISK}"
        else:
            decision = "block"
            reason = f"level {level} exceeds ceiling {self._max_auto_level}"

        content = {
            "action": message["action"],
            "decision": decision,
            "risk": risk,
            "permission_level": level,
            "assumed_worst_case": assumed,
            "reason": reason,
        }
        return content, 1.0  # the gate is deterministic arithmetic
