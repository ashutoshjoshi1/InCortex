# `examples/` — Runnable Demos

Small scripts showing InCortex capabilities end to end.

Examples (Design_Doc §20):

- `voice_demo.py` — ✅ the full speech loop with no audio hardware: scripted conversation, printed "speech", including the mumble-gate in action
- `dev_demo.py` — ✅ the Development Organ working a miniature codebase: issue analysis → gated read → approval-gated test run → unified-diff patch → PR draft it cannot merge
- `strategy_demo.py` — ✅ advanced learning: three strategies compete under UCB, the best wins the most trials, and the calibration report grades the system's honesty
- `basic_chat.py` — planned: CLI chat with the Cortex
- `memory_demo.py` — planned: teach a fact, retrieve it later
- `feedback_demo.py` — planned: correction changes future behavior

**Status:** voice demo landed with Phase 6, dev demo with Phase 8; the rest land with future phases.
