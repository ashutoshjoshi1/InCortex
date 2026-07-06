# `memory/` — Memory Layer

Stores and retrieves knowledge across memory types: working, short-term, long-term, episodic, semantic, procedural, preference, and error memory. MVP storage: SQLite (structured), ChromaDB/FAISS (vector), JSONL (event logs).

Planned modules (Design_Doc §12.4, §15, §20):

- `memory_record.py` — `MemoryRecord` schema with importance scoring
- `short_term.py`, `long_term.py`, `vector_memory.py`, `episodic_memory.py`
- `memory_manager.py` — storage, retrieval, cleanup, compression

**Math:** [docs/math_model.md §5](../../docs/math_model.md) — embedding similarity, forgetting curve, 7-factor importance, retrieval score, retention/compression, working-memory knapsack (Eq. 5.1–5.6).

**Status:** scaffolding only — built in Phase 5.
