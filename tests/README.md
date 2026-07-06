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

**Status:** scaffolding only — tests ship alongside each implementation phase.
