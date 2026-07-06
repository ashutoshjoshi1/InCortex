# `cells/` — Cell Layer

The smallest intelligent processing units. A Cell does one small job well and follows the contract:

```text
Input → Process → Output → Learn → Report Health
```

Planned modules (Design_Doc §9, §20):

- `base_cell.py` — shared `BaseCell` interface (the first file to be written — see Design_Doc §30)
- `text_cell.py`, `intent_cell.py`, `memory_cell.py`, `reasoning_cell.py`,
  `planner_cell.py`, `feedback_cell.py`, `safety_cell.py`

**Math:** [docs/math_model.md §1](../../docs/math_model.md) — activation, entropy confidence, history blending, health score, and status bands (Eq. 1.1–1.10).

**Status:** scaffolding only — built in Phase 1 (the first implementation phase).
