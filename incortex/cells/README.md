# `cells/` — Cell Layer

The smallest intelligent processing units. A Cell does one small job well and follows the contract:

```text
Input → Process → Output → Learn → Report Health
```

Modules (Design_Doc §9, §20):

- `base_cell.py` — ✅ shared `BaseCell` contract, confidence blending, health, feedback
- `cell_math.py` — ✅ pure equation helpers (softmax, entropy confidence, EMA, decay, similarity)
- `text_cell.py` — ✅ text normalization and statistics
- `intent_cell.py` — ✅ keyword-scored intent distribution with entropy confidence
- `memory_cell.py` — ✅ in-memory store/retrieve with the Eq 5.4 retrieval triad
- `feedback_cell.py` — ✅ rating normalization and learning score bands
- `response_cell.py` — ✅ intent-keyed replies with honest confidence (added in Phase 2)
- `reasoning_cell.py`, `planner_cell.py`, `safety_cell.py` — planned, arrive with Phases 3–7

**Math:** [docs/math_model.md §1](../../docs/math_model.md) — activation, entropy confidence, history blending, health score, and status bands (Eq. 1.1–1.10).

**Status:** Phase 1 implemented with 100% test coverage (`tests/test_cells.py`).
