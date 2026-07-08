# Understanding Phase 10 — API & Configuration

This document explains **every function built in Phase 10 in plain language**, continuing the series past the original roadmap ([Phases 1–9](.) each have their own doc). Phase 10 is the first "Beyond v0.1" milestone: the brain became a **service** — anything that speaks HTTP can now chat with it, feed its memory, rate its answers, and read its health — and its tunables moved from code into a **config file**.

---

## The Big Picture

Until now the only doors into the brain were the CLI and the voice loop, both wired by hand in scripts. Phase 10 adds the two pieces that make InCortex usable *by other software*:

1. **`core/config.py`** — one typed, validated home for every tunable the design doc's §24 sketch names (database path, forgetting half-life, safety ceiling, tool sandbox, API address), plus `build_cortex(config)`: hand it a config, get a fully assembled brain whose behavior provably matches the file.
2. **`incortex/api/`** — the §19 REST API, all nine endpoints, built on FastAPI exactly as the design doc specifies. It's the project's first *optional* web dependency (`pip install -e ".[api]"`); the core package still needs nothing.

Two adaptations from the design doc, both deliberate and documented:

- **TOML instead of YAML** for the config file. Python 3.11 ships a TOML parser in the standard library; YAML would have required the project's first mandatory dependency. The §24 structure maps one-to-one.
- **Fail-closed extends to HTTP.** A server has no human at a terminal, so no approver is attached: level-4 tools (like `run_python`) are *denied* over the API, and level-3 stays *blocked* unless the config raises the ceiling. The same principle from Phase 7, now protecting a network surface.

---

## `core/config.py` — the settings, typed and strict

### The five section classes
`MemoryConfig`, `LearningConfig`, `SafetyConfig`, `ToolsConfig`, `ApiConfig` — each a frozen dataclass whose `__post_init__` validates every field at construction (a half-life must be positive, the safety ceiling an integer 0–5, the port 1–65535, and a sneaky `True` is not a valid level — the same boolean trap caught in Phase 3). Wrong values fail at *load time*, not hours later mid-request.

### `CortexConfig`
The aggregate of all five sections, with complete defaults — `CortexConfig()` with no file at all gives a working in-memory brain with tools disabled.

- **`from_dict(data)`** — builds a config from nested dicts, *strictly*: an unknown section (`[telepathy]`) or a misspelled key (`db_pathh`) is an error, not a silent ignore. A typo in a safety setting must never quietly leave the default in place.
- **`to_dict()`** — the round-trip back to plain data (tested: `from_dict(to_dict(c)) == c`).

### `load_config(path)`
Reads TOML via the stdlib `tomllib` and hands it to `from_dict`. A missing file is a loud `FileNotFoundError` — configuration you *thought* you loaded is worse than none.

### `build_cortex(config, approver=None)`
The factory: assembles the MemoryManager (path, half-life, capacity from `[memory]`), the LearningOrgan (with a durable JSONL log if `[learning].log_path` is set), the SafetyOrgan (ceiling from `[safety]`), and — only if `[tools].enabled` — a ToolOrgan with the sandboxed file tools, memory search, and gated Python. **No approver argument means DenyAll**: an unattended, config-built brain never runs level-4 tools. The tests prove each wire: the database path persists across builds, the log file appears, the ceiling actually moves the gate.

---

## `incortex/api/` — the brain over HTTP

### `schemas.py` — the request contracts and the envelope
Five Pydantic request models (`ChatRequest`, `MemoryAddRequest`, `MemorySearchRequest`, `FeedbackRequest`, `ToolExecuteRequest`) with field constraints (non-empty messages, ratings 0–1, `top_k` 1–50) and `extra = "forbid"` — an unknown field in a request is a client bug and is rejected, mirroring the config's strictness.

**`envelope(data, error)`** — every single response is `{"success": …, "data": …, "error": …}`. One shape to parse, whatever happened.

### `routes_chat.py` — `POST /v1/chat`
Calls `core.handle()` and translates the `TaskContext` case file into the §19.4 response: the reply, the acceptance verdict, chain confidence, intent, organs used, whether memory was updated (checked honestly: was there an actual `store` stage? — a safety-gate refusal means `false`), and `feedback_requested` (true for accepted answers — rate the real ones).

### `routes_memory.py` — `POST /v1/memory/add` and `/v1/memory/search`
Direct doors to the Memory Organ: store with optional importance; search with `top_k`, returning the ranked Eq 5.4 results with their scores and similarities.

### `routes_feedback.py` — `POST /v1/feedback`
Grades the session's last task via the full Phase 5/9 pipeline — learning scores, cell track records, calibration, skill and weakness escalation all fire from one HTTP call. No task to rate → the `ValueError` becomes a readable `400`.

### `main.py` — the application factory

**`create_app(core=None, config=None)`** — wraps an existing brain, or builds one from config (defaults if neither). The app carries the core on its state; routers are attached; then two groups of extras:

- **Introspection routes:** `/v1/health` (the full recursive organ→tissue→cell report plus the system snapshot), `/v1/organs` (one-line summaries), `/v1/cells` (every cell flattened across organs, each tagged with its organ), and `/v1/logs?count=N` (the §17 brain-activity trail, with `_printable` converting arbitrary payload objects into JSON-safe text — an odd object in a log line must never crash the log endpoint).
- **The tools route:** `POST /v1/tools/execute` — no ToolOrgan configured → clear `400`; unknown tool name → `404`; otherwise the full Phase 7 gate ladder runs and the decision comes back verbatim. The named test: `run_python` over HTTP is **denied** — nobody is at the terminal to say yes.
- **Error handlers** — the three ways things fail all keep the envelope: Pydantic validation errors become `400`s with field-level messages (`message: String should have at least 1 character`), `ValueError`s from the domain become `400`s with their message, and HTTP errors (including 404s for unknown routes) are wrapped too. **No stack trace ever crosses the wire.**

### One infrastructure fix underneath
FastAPI serves sync endpoints from a threadpool, and SQLite connections refuse to cross threads by default. `LongTermMemory` now connects with `check_same_thread=False` — safe here because every operation is a single statement + commit, which SQLite serializes internally. This is the kind of bug only a real integration surfaces; the API tests now pin it.

---

## Launcher and example config

### `scripts/run_api.py`
Loads the given TOML (or explains the defaults), builds the app, and serves it with uvicorn — printing where the interactive OpenAPI docs live (`/docs`, generated by FastAPI for free). A missing FastAPI install produces a one-line instruction instead of a traceback.

### `incortex.toml.example`
The §24 config in its TOML form, every key commented with its default and meaning — copy, uncomment, run.

---

## The tests — what the 38 new checks prove

`tests/test_config.py` (15) and `tests/test_api.py` (23):

- **Config is strict everywhere**: complete sane defaults; immutable sections; every bad value rejected at construction (including the boolean-as-integer trap); unknown sections *and* unknown keys are load-time errors; missing files are loud; the dict round-trip holds.
- **`build_cortex` wires what the file says**: the database path persists across two separate builds; the learning log lands at its configured path; the ceiling moves the actual gate decision; enabled tools register the expected four; and the unattended brain denies level-4.
- **Every endpoint keeps the envelope** — asserted on every single response in the suite, including validation failures and unknown routes.
- **The chat flow over HTTP** matches the CLI's behavior exactly: teach → learn → answer from memory; the dark-matter question comes back `accepted: false` with the clarification; sessions are separated.
- **Memory, feedback, introspection**: add/search round-trips with importance intact; `top_k` honored; feedback returns the high band and 400s without a task; health/organs/cells/logs have their promised shapes; log payloads with arbitrary objects render safely.
- **The tools endpoint** runs the whole ladder: safe tool executed, level-4 denied (fail-closed over HTTP — the phase's signature test), unknown tool 404, tool-less brain 400.
