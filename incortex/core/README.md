# `core/` — Cortex Core

The central coordinator. It does not perform tasks itself — it routes `CortexMessage`s to the right Organs, builds execution plans, applies safety checks, and forwards results to the Learning Organ.

Modules (Design_Doc §13–§14, §20):

- `cortex.py` — ✅ CortexCore: the full loop with safety-gated writes and the Eq 4.4 answer-acceptance rule
- `router.py` — ✅ Eq 4.2 routing by keyword relevance + intent affinity, with best-organ fallback
- `scheduler.py` — ✅ Eq 4.3 starvation-free priority queue (uncapped age term)
- `message.py` — ✅ `CortexMessage` envelope + `MessageBus` with bounded activity history (§17)
- `state.py` — ✅ `TaskContext` (per-request case file) + `SystemState` (EMA scoreboard)
- `config.py` — ✅ typed §24 config (TOML via stdlib `tomllib`), strict loading (unknown keys are errors), and `build_cortex(config)` — a brain assembled to match the file (added in Phase 10)

**Math:** [docs/math_model.md §4](../../docs/math_model.md) — loop composition, routing threshold, scheduling priority, answer acceptance (Eq. 4.1–4.4). *Eq 4.3 was amended in Phase 4: the age term is uncapped so the no-starvation property (§11.8) actually holds.*

**Status:** Phase 4 implemented with 100% test coverage (`tests/test_core.py`). Plain-language walkthrough: [docs/understanding/phase_4_cortex_core.md](../../docs/understanding/phase_4_cortex_core.md).
