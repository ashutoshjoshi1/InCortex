# `api/` — API Layer

FastAPI service exposing the brain to other applications (Design_Doc §19). Requires the optional `api` extra (`pip install -e ".[api]"`); the core package stays dependency-free.

```text
POST /v1/chat            POST /v1/memory/add      POST /v1/memory/search
POST /v1/feedback        POST /v1/tools/execute
GET  /v1/health          GET  /v1/organs          GET /v1/cells    GET /v1/logs
```

Modules (Design_Doc §19, §20):

- `main.py` — ✅ `create_app(core | config)`: routers, introspection routes, tools route, envelope-preserving error handlers (no stack trace ever crosses the wire)
- `routes_chat.py` — ✅ the cognitive loop over HTTP (§19.3–19.4 shapes)
- `routes_memory.py` — ✅ store and Eq 5.4 search
- `routes_feedback.py` — ✅ grading with the full learning pipeline behind it
- `schemas.py` — ✅ strict Pydantic requests (`extra = "forbid"`) + the one `{success, data, error}` envelope

**Fail-closed over HTTP:** the server has no human attached, so level-4 tools are denied and level-3 stays blocked unless config raises the ceiling.

**Math:** [docs/math_model.md §8](../../docs/math_model.md) — `/v1/health` and `/v1/logs` expose the system statistics; the full §8 metrics (P@k, MRR, latency percentiles) are still pending.

**Status:** Phase 10 implemented with 100% test coverage (`tests/test_api.py`). Reference: [docs/api_reference.md](../../docs/api_reference.md). Plain-language walkthrough: [docs/understanding/phase_10_api_config.md](../../docs/understanding/phase_10_api_config.md).
