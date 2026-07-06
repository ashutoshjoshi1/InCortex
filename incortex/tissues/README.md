# `tissues/` — Tissue Layer

A Tissue is a group of Cells working together on one capability: it routes messages to the right Cell, combines outputs, and reports collective health.

Planned modules (Design_Doc §10, §20):

- `base_tissue.py` — shared `BaseTissue` interface
- `language_tissue.py`, `memory_tissue.py`, `reasoning_tissue.py`, `learning_tissue.py`

**Math:** [docs/math_model.md §2](../../docs/math_model.md) — confidence-weighted combination, voting, mixture-of-experts gating, tissue health (Eq. 2.1–2.4).

**Status:** scaffolding only — built in Phase 2.
