# `tools/` — Tool Layer

Tools are controlled external abilities (read/write files, search, run Python, fetch URLs). Every tool declares its permission level and risk estimates, is registered in the Tool Registry, and is only ever invoked through the ToolOrgan's safety gate.

Modules (Design_Doc §18, §20):

- `base_tool.py` — ✅ the muscle-fiber contract: validate → execute → `ToolResult`; fail-closed defaults (an unclassified tool is level 5, worst-case risk)
- `tool_registry.py` — ✅ catalogue with per-tool enable/disable kill-switch
- `file_tools.py` — ✅ sandboxed read (L1) / write (L2); path escapes rejected at validation
- `search_tools.py` — ✅ memory search as a gated tool (L1)
- `python_tool.py` — ✅ code execution (L4 — always needs a human), separate process, hard timeout
- `api_tool.py` — ✅ HTTP GET (L3 — blocked until config raises the ceiling), scheme and size guards
- `dev_tools.py` — ✅ development abilities (added in Phase 8): `list_project_files` (L1, sandboxed inventory), `run_tests` (L4 — pytest in a separate process; failures come back as data for the learning loop), `create_github_issue` (L3, injectable transport)

**Math:** [docs/math_model.md §7](../../docs/math_model.md) — each tool declares the Eq. 7.1 inputs; the ToolOrgan runs the Eq. 7.2 gate before every execution.

**Status:** Phase 7 implemented with 100% test coverage (`tests/test_safety.py`). Plain-language walkthrough: [docs/understanding/phase_7_tool_system.md](../../docs/understanding/phase_7_tool_system.md).
