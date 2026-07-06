# `muscles/` — Muscle Layer

The brain thinks; Muscles act. Muscles execute approved actions only — they make no deep decisions, and every Muscle obeys the permission rules in `safety/`.

Planned modules (Design_Doc §11, §20):

- `base_muscle.py` — shared `BaseMuscle` interface
- `speech_muscle.py`, `file_muscle.py`, `code_muscle.py`, `search_muscle.py`, `api_muscle.py`

**Math:** [docs/math_model.md §7](../../docs/math_model.md) — every Muscle action passes the risk score and fail-closed permission gate (Eq. 7.1–7.2) before executing.

**Status:** scaffolding only — built in Phase 7.
