"""The Safety layer — human approval machinery (Phase 7).

The permission mathematics (risk, gate, blocklist) live in
cells/safety_cell.py and organs/safety_organ.py; this package holds what
cannot be computed: asking a person.
"""

from incortex.safety.approval import BaseApprover, CallbackApprover, DenyAllApprover

__all__ = ["BaseApprover", "CallbackApprover", "DenyAllApprover"]
