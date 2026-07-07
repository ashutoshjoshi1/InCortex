# `tests/` — Test Suite

Every Cell, Tissue, Organ, memory module, and safety rule gets tested (pytest).

Planned test modules (Design_Doc §20, §26):

- `test_cells.py`, `test_tissues.py`, `test_organs.py`
- `test_memory.py`, `test_learning.py`, `test_safety.py`

Four test categories:

1. **Unit** — each component in isolation
2. **Integration** — full flows (input → memory → reasoning → response)
3. **Safety** — dangerous actions are blocked or require approval
4. **Learning** — feedback measurably changes future behavior

**Math:** [docs/math_model.md §11](../docs/math_model.md) lists the testable properties of every equation — range, monotonicity, decay, fail-closed gating, convergence — which become property tests here.

**Status:** `test_cells.py` (78), `test_tissues.py` (37), `test_organs.py` (43), `test_core.py` (46), `test_memory.py` (37), and `test_learning.py` (20) — 261 tests, 100% coverage of the Cell, Tissue, Organ, Cortex Core, Memory, and Learning layers, including the math property tests. Remaining modules ship alongside their phases.
