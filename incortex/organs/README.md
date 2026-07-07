# `organs/` — Organ Layer

An Organ is a specialized subsystem made of Tissues and Cells (Language, Memory, Reasoning, Planning, Learning, Speech, Safety, Tool, Development).

Modules (Design_Doc §12, §20):

- `base_organ.py` — ✅ component management (tissues + cells), recursive health, pipeline confidence, capability relevance
- `language_organ.py` — ✅ understand + respond over the LanguageTissue
- `memory_organ.py` — ✅ store + retrieve over the MemoryTissue
- `reasoning_organ.py` — ✅ evidence-based reasoning, conservative min-mode confidence
- `learning_organ.py` — ✅ feedback scoring and distribution
- `safety_organ.py` — ✅ Eq 7.1–7.2 gate, action blocklist, bounded decision log
- `input_organ.py`, `planning_organ.py`, `speech_organ.py`, `tool_organ.py` — planned (Phases 4–7; Development Organ in Phase 8)

**Math:** [docs/math_model.md §3](../../docs/math_model.md) — pipeline confidence degradation, organ relevance for routing (Eq. 3.1–3.2); the SafetyOrgan implements §7 (Eq. 7.1–7.2).

**Status:** Phase 3 implemented with 100% test coverage (`tests/test_organs.py`). Plain-language walkthrough: [docs/understanding/phase_3_organ_system.md](../../docs/understanding/phase_3_organ_system.md).
