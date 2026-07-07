# `safety/` — Safety Layer

Protects the system, user, and environment. Enforces permission levels 0–5; Level 4 (code execution) and Level 5 (system-level) actions always require human approval. No uncontrolled self-modification, ever.

Modules (Design_Doc §12.9, §25, §20):

- `approval.py` — ✅ the human in the loop: `BaseApprover` (audit-logged), `DenyAllApprover` (fail-closed default: an unattended brain grants nothing), `CallbackApprover` (wire to a terminal prompt or UI)
- `permissions.py` / `risk.py` / `policy.py` — the permission mathematics live in `cells/safety_cell.py` (Eq. 7.1–7.2 gate) and `organs/safety_organ.py` (blocklist, decision log, configurable `max_auto_level` ceiling); separate modules arrive if policy grows beyond them

**Math:** [docs/math_model.md §7](../../docs/math_model.md) — risk = likelihood × impact, fail-closed permission gate (Eq. 7.1–7.2). Z-score anomaly flagging (Eq. 7.3) arrives with the metrics work.

**Status:** Phase 7 implemented with 100% test coverage (`tests/test_safety.py`). Plain-language walkthrough: [docs/understanding/phase_7_tool_system.md](../../docs/understanding/phase_7_tool_system.md).
