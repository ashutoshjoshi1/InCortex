# API Reference

The InCortex REST API (Design_Doc §19). Start it with:

```bash
pip install -e ".[api]"
python scripts/run_api.py [config.toml]     # interactive docs at /docs
```

## The envelope

Every response — success, validation failure, or unknown route — uses one shape:

```json
{"success": true, "data": { ... }, "error": null}
{"success": false, "data": null, "error": "readable message"}
```

Validation failures are `400` with field-level messages; unknown tools/routes are `404`. Stack traces are never exposed.

## Endpoints

### `POST /v1/chat`

One trip through the cognitive loop.

```json
{"message": "Teach yourself what photosynthesis is.", "session_id": "default"}
```

→ `data`: `response`, `accepted` (the Eq 4.4 gate verdict), `confidence` (chain confidence), `intent`, `organs_used`, `memory_updated`, `feedback_requested`, `session_id`.

A low-confidence chain returns an honest clarification request with `accepted: false` — the API never pretends.

### `POST /v1/memory/add`

```json
{"content": "a fact worth keeping", "importance": 0.8}
```

→ `data`: `stored`, `copies`, `confidence`. Importance is optional (0–1).

### `POST /v1/memory/search`

```json
{"query": "photosynthesis", "top_k": 3}
```

→ `data.results`: ranked records with `content`, `score` (the Eq 5.4 triad), `similarity`, `importance`, `memory_type`. `top_k` is 1–50.

### `POST /v1/feedback`

```json
{"success": true, "rating": 1.0, "session_id": "default"}
```

Grades the session's most recent task (Eq 6.1–6.2), teaches every organ that took part, feeds calibration (Eq 6.7) and skill/weakness escalation. → `data`: `learning_score`, `band`, `normalized_rating`, `running_score`, `events`. With no task to rate: `400`.

### `POST /v1/tools/execute`

```json
{"tool": "search_memory", "request": {"query": "cats"}}
```

Runs one gated tool. → `data`: `tool`, `decision` (`executed` / `approved_and_executed` / `denied` / `blocked` / `disabled`), `executed`, `success`, `output`, `error`.

**Fail-closed over HTTP:** the server has no human attached, so level-4 tools (e.g. `run_python`) come back `denied`. Level-3 tools are `blocked` unless `safety.max_auto_level` is raised in config. Unknown tool → `404`; no ToolOrgan configured → `400`.

### `GET /v1/health`

The full recursive report: every organ → tissue → cell, plus the system snapshot (tasks handled, acceptance rate, confidence and learning EMAs).

### `GET /v1/organs` · `GET /v1/cells`

Summaries: organs as `{name, status, health}`; cells flattened across all organs with their per-cell statistics.

### `GET /v1/logs?count=20`

The recent brain-activity trail (Design_Doc §17) from the message bus: `message_type`, `source`, `target`, `session_id`, `confidence`, `created_at`, `payload`. `count` is 1–200.

## Configuration

See [incortex.toml.example](../incortex.toml.example) — TOML form of Design_Doc §24 (`[memory]`, `[learning]`, `[safety]`, `[tools]`, `[api]`), loaded strictly: unknown keys are startup errors.

## Not yet implemented

Rate limiting and authentication are deployment-level concerns for a production setup (see the security rules in Design_Doc §25); the MVP API binds to `127.0.0.1` by default.
