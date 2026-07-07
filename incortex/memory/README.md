# `memory/` — Memory Layer

Stores and retrieves knowledge across memory types: working, short-term, long-term, episodic, semantic, procedural, preference, and error memory. MVP storage: SQLite (structured), ChromaDB/FAISS (vector), JSONL (event logs).

Modules (Design_Doc §12.4, §15, §20):

- `memory_record.py` — ✅ immutable `MemoryRecord` with the nine §12.4 memory types
- `short_term.py` — ✅ bounded newest-first buffer
- `long_term.py` — ✅ SQLite persistence; archive-never-destroy (§25.3)
- `vector_memory.py` — ✅ signed feature-hashing embedder + clipped-cosine similarity + index
- `vector_memory_cell.py` — ✅ the manager wearing the Cell contract (drop-in for MemoryCell)
- `memory_manager.py` — ✅ Eq 5.4 retrieval triad, forgetting curve with access reset, reinforce, retention-based cleanup
- `episodic_memory.py` — planned (arrives with experience tracking)

**Math:** [docs/math_model.md §5](../../docs/math_model.md) — embedding similarity, forgetting curve, importance, retrieval score, retention (Eq. 5.1–5.5). *Two equations were amended in Phase 5: Eq 5.1 (clipped cosine instead of the ½(1+cos) rescale) and Eq 5.4 (a similarity floor so freshness can't resurrect irrelevant memories).*

**Status:** Phase 5 implemented with 100% test coverage (`tests/test_memory.py`). Plain-language walkthrough: [docs/understanding/phase_5_memory_learning.md](../../docs/understanding/phase_5_memory_learning.md).
