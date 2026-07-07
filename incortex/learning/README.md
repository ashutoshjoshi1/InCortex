# `learning/` — Learning Layer

The heart of self-improvement. v0.1 learning is *controlled*: memory updates, feedback collection, mistake tracking, and evaluation scoring — not uncontrolled model training.

Modules (Design_Doc §12.7, §16, §20):

- `feedback.py` — ✅ durable `FeedbackEvent` record (§16.2)
- `learning_log.py` — ✅ JSONL learning history, reloaded across restarts
- `mistake_tracker.py` — ✅ similarity-clustered failures, repeat rate, error trend (Eq 6.5)
- `learning_loop.py` — ✅ `StrategyBank`: bandit value updates + UCB selection, experiment tracking, model comparison (Eq 6.3–6.4, Phase 9)
- `evaluator.py` — ✅ `SelfEvaluator`: Brier score and ECE calibration of the brain's own confidence (Eq 6.7, Phase 9)
- `skill_builder.py` — ✅ `SkillBuilder`: recurring successes promoted to skills via the rule of succession (Eq 6.6, Phase 9)
- Fine-tuning pipeline — deferred to v1.0 per the design doc's learning timeline (§12.7) and math_model §6.7

**Math:** [docs/math_model.md §6](../../docs/math_model.md) — the complete §6 suite is now implemented (Eq 6.1–6.7).

**Status:** Phases 5 and 9 implemented with 100% test coverage (`tests/test_learning.py`), including weakness *and* skill escalation into memory. Walkthroughs: [phase_5_memory_learning.md](../../docs/understanding/phase_5_memory_learning.md), [phase_9_advanced_learning.md](../../docs/understanding/phase_9_advanced_learning.md).
