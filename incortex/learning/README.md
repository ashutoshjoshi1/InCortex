# `learning/` — Learning Layer

The heart of self-improvement. v0.1 learning is *controlled*: memory updates, feedback collection, mistake tracking, and evaluation scoring — not uncontrolled model training.

Modules (Design_Doc §12.7, §16, §20):

- `feedback.py` — ✅ durable `FeedbackEvent` record (§16.2)
- `learning_log.py` — ✅ JSONL learning history, reloaded across restarts
- `mistake_tracker.py` — ✅ similarity-clustered failures, repeat rate, error trend (Eq 6.5)
- `evaluator.py` — planned: calibration metrics (Eq 6.7, v0.4 self-evaluation)
- `learning_loop.py` — planned: bandit strategy values + UCB (Eq 6.3–6.4, when strategies exist)
- `skill_builder.py` — planned: reusable skill library (Eq 6.6, Phase 9)

**Math:** [docs/math_model.md §6](../../docs/math_model.md) — feedback normalization, learning score, mistake clustering (Eq. 6.1, 6.2, 6.5 live in the Cells/Organs and here).

**Status:** Phase 5 implemented with 100% test coverage (`tests/test_learning.py`), including weakness escalation into memory (§16.4). Plain-language walkthrough: [docs/understanding/phase_5_memory_learning.md](../../docs/understanding/phase_5_memory_learning.md).
