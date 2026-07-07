# `tissues/` — Tissue Layer

A Tissue is a group of Cells working together on one capability: it routes messages to the right Cell, combines outputs, and reports collective health.

Modules (Design_Doc §10, §20):

- `base_tissue.py` — ✅ member management, accept-based routing, confidence-weighted combining, feedback propagation, conservative health
- `language_tissue.py` — ✅ TextCell → IntentCell → ResponseCell chain
- `memory_tissue.py` — ✅ merged, deduplicated retrieval across MemoryCells
- `learning_tissue.py` — ✅ feedback scoring, running learning score, feedback distribution
- `reasoning_tissue.py` — ✅ chain reasoning over evidence (added in Phase 3)

**Math:** [docs/math_model.md §2](../../docs/math_model.md) — confidence-weighted combination, voting, mixture-of-experts gating, tissue health (Eq. 2.1–2.4).

**Status:** Phase 2 implemented with 100% test coverage (`tests/test_tissues.py`). Plain-language walkthrough: [docs/understanding/phase_2_tissue_system.md](../../docs/understanding/phase_2_tissue_system.md).
