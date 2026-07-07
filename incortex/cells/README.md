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
- `reasoning_cell.py` — ✅ three-step evidence reasoning with Eq 3.1 chain confidence (added in Phase 3)
- `safety_cell.py` — ✅ fail-closed risk gate, Eq 7.1–7.2 (added in Phase 3)
- `ear_cell.py` — ✅ an Ear provider wearing the Cell contract; transcript confidence enters the chain math (added in Phase 6)
- `mouth_cell.py` — ✅ a Mouth provider wearing the Cell contract — the design doc's SpeechCell (added in Phase 6)
- `planner_cell.py` — planned, arrives with the Planning Organ

**Math:** [docs/math_model.md §1](../../docs/math_model.md) — activation, entropy confidence, history blending, health score, and status bands (Eq. 1.1–1.10).

**Status:** Phase 1 implemented with 100% test coverage (`tests/test_cells.py`).
