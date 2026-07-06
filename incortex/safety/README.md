# `safety/` — Safety Layer

Protects the system, user, and environment. Enforces permission levels 0–5; Level 4 (code execution) and Level 5 (system-level) actions always require human approval. No uncontrolled self-modification, ever.

Planned modules (Design_Doc §12.9, §25, §20):

- `permissions.py` — permission levels and checks
- `risk.py` — action risk classification (low/medium/high)
- `policy.py` — safety policy rules
- `approval.py` — human-approval flow for risky actions

**Status:** scaffolding only — built alongside Phases 3 and 7.
