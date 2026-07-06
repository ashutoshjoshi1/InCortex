# `learning/` — Learning Layer

The heart of self-improvement. v0.1 learning is *controlled*: memory updates, feedback collection, mistake tracking, and evaluation scoring — not uncontrolled model training.

Planned modules (Design_Doc §12.7, §16, §20):

- `feedback.py` — `FeedbackEvent` collection
- `evaluator.py` — learning scores per task
- `learning_loop.py` — task → feedback → score → strategy update
- `mistake_tracker.py` — repeated-error tracking
- `skill_builder.py` — reusable skill library (Phase 9)

**Status:** scaffolding only — built in Phase 5, extended in Phase 9.
