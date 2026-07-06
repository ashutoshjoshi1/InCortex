# `api/` — API Layer

FastAPI service exposing the brain to other applications:

```text
POST /v1/chat            POST /v1/memory/add      POST /v1/memory/search
POST /v1/feedback        POST /v1/tools/execute
GET  /v1/health          GET  /v1/organs          GET  /v1/cells    GET /v1/logs
```

Planned modules (Design_Doc §19, §20):

- `main.py` — FastAPI app entrypoint
- `routes_chat.py`, `routes_memory.py`, `routes_feedback.py`
- `schemas.py` — Pydantic request/response models

**Status:** scaffolding only — built after the Cortex Core (Phase 4+).
