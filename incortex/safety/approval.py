"""Human approval — the person in the loop (Design_Doc §12.9, §25.2).

When the safety gate says 'require_approval', someone must actually be
asked. The default approver denies everything (fail-closed: an unattended
brain grants nothing); the callback approver wires the question to a real
human, e.g. a CLI prompt. Every decision is logged.
"""

from collections import deque

DEFAULT_LOG_SIZE = 100


class BaseApprover:
    """Contract: request(action, reason) -> bool, with a bounded audit log."""

    def __init__(self, log_size=DEFAULT_LOG_SIZE):
        self._log = deque(maxlen=log_size)

    def request(self, action, reason):
        """Ask for approval of one action; the answer is logged."""
        granted = bool(self._decide(action, reason))
        self._log.append({"action": action, "reason": reason, "granted": granted})
        return granted

    @property
    def decisions(self):
        """The most recent approval decisions, oldest first."""
        return tuple(self._log)

    def _decide(self, action, reason):
        raise NotImplementedError


class DenyAllApprover(BaseApprover):
    """The fail-closed default: nobody is watching, so nothing is granted."""

    def _decide(self, action, reason):
        return False


class CallbackApprover(BaseApprover):
    """Delegates the question to a callable — e.g. a CLI y/n prompt."""

    def __init__(self, callback, log_size=DEFAULT_LOG_SIZE):
        super().__init__(log_size)
        if not callable(callback):
            raise ValueError("callback must be callable")
        self._callback = callback

    def _decide(self, action, reason):
        return self._callback(action, reason)
