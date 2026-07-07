"""SafetyOrgan — protects the system, user, and environment (Design_Doc §12.9).

Wraps the SafetyCell gate (Eq 7.1-7.2) and adds two organ-level duties:
a blocklist of actions that are never allowed regardless of scores
(Design_Doc §6 non-goals: no uncontrolled self-modification), and a
bounded log of every decision ("log important actions"). Z-score anomaly
flagging (Eq 7.3) arrives with the metrics work in a later phase.
"""

from collections import deque

from incortex.cells import SafetyCell
from incortex.organs.base_organ import BaseOrgan, OrganOutput

CAPABILITIES = (
    "delete", "run", "execute", "send", "email", "install",
    "shell", "command", "push", "permission",
)
# Actions that are never allowed, whatever their scores (Design_Doc §25.2, §26.3).
DEFAULT_BLOCKED_ACTIONS = frozenset({
    "change_safety_policy",
    "modify_own_code",
    "delete_all_files",
    "delete_all_memory",
})
DEFAULT_LOG_SIZE = 100


class SafetyOrgan(BaseOrgan):
    def __init__(self, name="safety_organ",
                 blocked_actions=DEFAULT_BLOCKED_ACTIONS, log_size=DEFAULT_LOG_SIZE):
        # 'min' mode: a safety verdict is never more confident than its weakest input
        super().__init__(name, capability_keywords=CAPABILITIES, confidence_mode="min")
        self._gate = SafetyCell()
        self.add_cell(self._gate, critical=True)
        self._blocked = frozenset(blocked_actions)
        self._log = deque(maxlen=log_size)

    @property
    def decisions(self):
        """The most recent gate decisions, oldest first."""
        return tuple(self._log)

    def check(self, action, permission_level, harm_probability=None, impact=None):
        """Gate one action: blocklist first, then the SafetyCell (Eq 7.2)."""
        if action in self._blocked:
            content = {
                "action": action,
                "decision": "block",
                "risk": 1.0,
                "permission_level": permission_level,
                "assumed_worst_case": False,
                "reason": "action is on the safety blocklist",
            }
            stage_outputs = ()
        else:
            message = {"action": action, "permission_level": permission_level}
            if harm_probability is not None:
                message["harm_probability"] = harm_probability
            if impact is not None:
                message["impact"] = impact
            output = self._gate.process(message)
            content = output.content
            stage_outputs = (output,)
        self._log.append({
            "action": content["action"],
            "decision": content["decision"],
            "risk": content["risk"],
            "reason": content["reason"],
        })
        return OrganOutput(
            organ_name=self.name,
            content=content,
            confidence=1.0,  # the gate is deterministic
            stage_outputs=stage_outputs,
        )

    def process(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        return self.check(
            message.get("action"),
            message.get("permission_level"),
            message.get("harm_probability"),
            message.get("impact"),
        )
