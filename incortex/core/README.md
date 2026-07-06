# `core/` — Cortex Core

The central coordinator. It does not perform tasks itself — it routes `CortexMessage`s to the right Organs, builds execution plans, applies safety checks, and forwards results to the Learning Organ.

Planned modules (Design_Doc §13–§14, §20):

- `cortex.py` — CortexCore coordinator
- `router.py` — message routing to Organs
- `scheduler.py` — task scheduling
- `message.py` — `CortexMessage` standard format
- `state.py` — system/session state
- `config.py` — configuration loading

**Status:** scaffolding only — built in Phase 4.
