# `scripts/` — Developer Utilities

Scripts (Design_Doc §20):

- `run_cli.py` — ✅ text chat with the full brain; persistent memory (default `data/incortex.db`)
- `run_voice.py` — ✅ voice chat: type to talk, replies spoken via the system voice (Phase 6)
- `run_api.py` — ✅ serve the brain over HTTP from a TOML config (Phase 10; needs the `api` extra)
- `init_db.py` — superseded: the MemoryManager creates its SQLite schema on first use
- `seed_memory.py` — planned: load starter memory records

**Status:** both chat entrypoints run; the API launcher arrives with its phase.
