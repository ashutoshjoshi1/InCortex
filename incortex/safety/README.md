# `safety/` — Safety Layer

Protects the system, user, and environment. Enforces permission levels 0–5; Level 4 (code execution) and Level 5 (system-level) actions always require human approval. No uncontrolled self-modification, ever.

Planned modules (Design_Doc §12.9, §25, §20):

- `permissions.py` — permission levels and checks
- `risk.py` — action risk classification (low/medium/high)
- `policy.py` — safety policy rules
- `approval.py` — human-approval flow for risky actions

**Math:** [docs/math_model.md §7](../../docs/math_model.md) — risk = likelihood × impact, fail-closed permission gate, z-score anomaly flagging (Eq. 7.1–7.3).

**Status:** scaffolding only — built alongside Phases 3 and 7.
