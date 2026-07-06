# `tools/` — Tool Layer

Tools are controlled external abilities (read/write files, search, run Python, GitHub actions). Every tool declares a risk level and permission requirement, and is registered in the Tool Registry.

Planned modules (Design_Doc §18, §20):

- `base_tool.py` — `BaseTool` interface (validate → execute → result)
- `tool_registry.py` — names, schemas, risk levels, enable/disable
- `file_tools.py`, `python_tool.py`, `github_tool.py`

**Status:** scaffolding only — built in Phase 7.
