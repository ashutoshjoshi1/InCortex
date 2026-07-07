# Understanding Phase 5 — Memory and Learning

This document explains **every function built or changed in Phase 5 in plain language**, continuing the series ([Phase 1](phase_1_cell_system.md) · [Phase 2](phase_2_tissue_system.md) · [Phase 3](phase_3_organ_system.md) · [Phase 4](phase_4_cortex_core.md)). Equation references point into [math_model.md](../math_model.md).

Phase 5 gave the brain what it was missing: **memory that survives** (quit the program, come back tomorrow — it still knows) and **learning that accumulates** (a durable history of every graded task, and mistakes that cluster into remembered weaknesses).

---

## The Big Picture

Three upgrades, all visible from the CLI:

1. **Persistence.** Facts now live in a SQLite database, the learning history in a JSONL file. Teach photosynthesis, quit, restart: the banner says "1 memories" and the question gets answered *from a previous life*.
2. **Real vector memory.** The word-overlap (Jaccard) stand-in from Phase 1 is replaced by genuine vector mathematics: texts become 1024-dimensional vectors, compared by cosine similarity. Related texts score high, morphological cousins ("photosynthesis"/"photosynthesize") score moderately, and — crucially — unrelated texts score ~0. The dark-matter question that fooled Jaccard through shared filler words now retrieves *nothing*.
3. **Mistakes become memories.** Fail at the same kind of question three times and the brain stores "Known weakness: I keep failing at 'What is dark matter?'" as a maximally important memory.

**Two more spec bugs were found by implementation and fixed in the math doc** (the Phase 4 tradition continues):

- **Eq 5.1**: the old rescale ½(1+cos) mapped *unrelated* texts to similarity 0.5 — enough to pass the retrieval threshold and flood recall with junk. Amended to a clipped cosine, so unrelated stays 0.
- **Eq 5.4**: freshness (0.2) + importance (0.2 × 0.5) alone add to 0.3, above the 0.25 retrieval threshold — so a brand-new memory could be retrieved with near-zero similarity. Amended with a similarity floor (0.1): recency and importance *rank* relevant memories; they never *resurrect* irrelevant ones.

---

## `memory_record.py` — the archival index card

### `MemoryRecord` (a frozen record)
One remembered fact with everything the math needs: id, type (one of the nine §12.4 memory types — semantic, episodic, preference, error…), the content, its source, **importance** and **confidence** (0–1), tags, and four bookkeeping numbers: created, updated, last-accessed timestamps and an access counter. Immutable — updating a record means creating a corrected copy (`dataclasses.replace`), never scribbling on the original.

### `new_memory_record(content, ...)`
The factory: validates everything (real content, known type, scores in range), stamps id and times, returns the record.

---

## `vector_memory.py` — turning text into geometry

### `content_words(text)`
Tokenizes and drops the shared stopword list (grammar glue + command verbs — now living in `cell_math.CONTENT_STOPWORDS`, shared with the ReasoningCell). "Teach yourself what photosynthesis is" → just `photosynthesis`.

### `HashingEmbedder.embed(text)`
Converts text to a fixed-length (default 1024) numeric vector, deterministically and with zero dependencies:

- each content word adds weight 1.0 to a bucket chosen by hashing the word;
- each 3-letter fragment (trigram) of the word adds 0.3 to its own bucket — this is why "photosynthesis" and "photosynthesize" land near each other (similarity ≈ 0.47): they share most of their fragments;
- the final vector is length-normalized so only *direction* matters, not text length.

Two engineering details worth knowing: the hash is CRC32, not Python's built-in `hash()` (which is randomized per process — embeddings must be identical across restarts so the index can be rebuilt); and every feature also gets a **±1 sign from a second hash**, so when two unrelated words collide into the same bucket their contributions tend to *cancel* rather than accumulate into fake similarity. Stopword-only text embeds to the zero vector — similar to nothing, by design.

When a neural embedding model arrives later, only this class changes; everything downstream speaks "vectors and cosine" already.

### `cosine_similarity(a, b)` / `similarity01(a, b)`
The angle-based similarity of two vectors, and its clipped-to-[0,1] version — **Eq 5.1 as amended**: identical direction → 1, unrelated or opposed → 0.

### `VectorIndex`
The lookup table: `add(id, text)` embeds and stores, `remove(id)` forgets, `similarities(query)` returns every stored id's similarity to the query (zeros omitted). Brute-force search — perfectly fine at this scale, swappable for FAISS/ChromaDB later.

---

## `short_term.py` — the scratchpad

### `ShortTermMemory`
A bounded buffer (default 100) of the most recent memories: `add(record)` (oldest silently falls off at capacity), `recent(n)` (newest first), `clear()`, `len()`. Durability is long-term memory's job; this is the "what just happened" buffer.

---

## `long_term.py` — the vault (SQLite)

### `LongTermMemory`
Durable storage in SQLite — the standard library kind, no new dependencies. Every query is parameterized (no SQL injection by construction).

- **`save(record)`** — insert or update. A subtle promise: re-saving an archived record does *not* quietly un-archive it.
- **`get(memory_id)` / `all_records(include_archived=False)` / `count(...)`** — reads; archived records are hidden unless explicitly asked for.
- **`archive(memory_id)`** — hides a record from normal reads **without destroying it**. This is the design doc's §25.3 promise: the system may tidy, but only an explicit human-controlled `delete(memory_id)` actually removes.
- **`close()`** — releases the database.

The persistence test seals the contract: save, close, reopen from the same file, and the record comes back byte-for-byte equal.

---

## `memory_manager.py` — the librarian

### `MemoryManager.__init__(db_path, ...)`
Opens the three stores (SQLite vault, vector index, short-term buffer) and — the trick that makes restarts work — **rebuilds the vector index from the vault**: since the embedder is deterministic, re-embedding every stored fact reconstructs the exact same vectors the previous run had.

### `remember(content, ...)`
One fact into all three stores; returns the new record.

### `recall(query, top_k=3)` — Eq 5.4, the full triad
For every indexed memory: score = **60% similarity + 20% recency + 20% importance**, where recency follows the Ebbinghaus forgetting curve (Eq 5.2, half-life 7 days). Two gates keep junk out: total score ≥ 0.25 *and* similarity ≥ 0.1 (the amendment). And the biological touch: **recalling a memory resets its forgetting clock** — the tests show a memory aged to score 0.8 jumping back to 0.9 after one access. Used memories stay strong; untouched ones fade.

### `reinforce(memory_id, delta)`
Nudges a memory's importance up (clipped at 1.0) — the practical form of Eq 5.3's "impact" factor: memories that helped successful tasks are worth more.

### `forget(memory_id)`
True deletion, everywhere — the user-controlled kind (§25.3).

### `cleanup(budget)` — Eq 5.5
When the vault exceeds its budget, ranks everything by **retention = importance × freshness** and *archives* (never deletes) the tail. An important-but-old memory outlives a trivial-but-recent one.

### `stats()` / `close()`
Counts for the CLI banner; tidy shutdown.

---

## `vector_memory_cell.py` — the adapter

### `VectorMemoryCell`
The MemoryManager wearing the standard Cell contract: it speaks the *exact* store/retrieve message schema of the Phase 1 MemoryCell (validation shared via the extracted `validate_memory_message`), so it slots into a MemoryTissue unchanged — but behind it sit SQLite, vectors, and the forgetting curve. The Phase 1 `MemoryCell` remains in the codebase as the reference implementation and is still what a bare `MemoryTissue()` creates; the *organ* now builds its tissue around the vector cell.

---

## `learning/feedback.py` — the feedback receipt

### `FeedbackEvent` / `new_feedback_event(...)`
The §16.2 record of one piece of user feedback — task id, success, optional rating/correction/comment, timestamp — validated and frozen. The durable counterpart of the transient feedback dicts flowing through the organs.

---

## `learning/learning_log.py` — the diary

### `LearningLog`
The durable history of every graded task. `record(entry)` stamps a timestamp and appends; with a file path each entry is also written as one JSON line (the JSONL format from the design doc's MVP storage list), and — like all Phase 5 storage — **reloaded on startup**, so the diary continues across restarts. `recent(n)` reads back, oldest first. Entries must be JSON-serializable; the log refuses anything it couldn't faithfully persist.

---

## `learning/mistake_tracker.py` — the pattern-spotter

### `MistakeTracker.record(success, description)`
Every task outcome goes in. Successes just update the statistics. Failures get embedded (same vector math as memory) and **clustered**: a new failure joins the most similar existing cluster above the 0.85 threshold (Eq 6.5's τ) or founds a new one. "What is dark matter?" failed three times = one cluster with count 3, not three separate complaints.

### `repeat_rate(cluster)`
How often this mistake happens: cluster size over all recorded tasks (2 failures in 3 tasks → 0.67).

### `error_trend()` — Eq 6.5's ΔE
Compares the error rate of the *newer half* of recent outcomes against the *older half*. Negative = genuinely improving (the test: four failures then four successes → trend −1.0). Too little data → honest 0.

### `known_weaknesses(min_count=3)`
The clusters that have recurred enough to deserve action.

---

## Wiring changes

### `LearningOrgan` (upgraded)
Now owns a `LearningLog` and a `MistakeTracker`. Both `score(...)` and `distribute(...)` accept an optional `description` (what the task *was*) and, besides their Phase 3 duties, write the diary entry and feed the tracker. Old call sites work unchanged.

### `MemoryOrgan` (upgraded)
Builds its tissue around a `VectorMemoryCell` backed by a `MemoryManager` (in-RAM SQLite by default, a real file when the CLI passes one). Exposes `.manager` so the CLI can show stats. Store/retrieve interfaces unchanged — the Cortex didn't need to learn anything new.

### `CortexCore.feedback(...)` (upgraded)
Passes the task's text as the mistake description, and afterwards runs **weakness escalation** (§16.4): any cluster reaching three failures is stored — once — into memory as `"Known weakness: I keep failing at '...'"` with maximum importance, announced on the bus as an `error_event`. The loop closes: *fail → cluster → remember → (eventually) act differently*.

### `scripts/run_cli.py` (upgraded)
`build_core(db_path)` assembles a persistent brain: SQLite memories plus a JSONL learning log sitting next to the database file (default `data/incortex.db`; pass `:memory:` for an ephemeral one). The banner reports how much the brain already knows: *"Memory: data/incortex.db (1 memories, 0 archived, 1 learning events)"*.

---

## The tests — what the 57 new checks prove

`tests/test_memory.py` (37) and `tests/test_learning.py` (20):

- **Embeddings behave**: identical → 1.0; unrelated → ~0 (the amendment in action); morphological cousins > 0.3; stopword-only text matches nothing; deterministic across instances.
- **The vault keeps its promises**: exact roundtrips, upserts, archived-but-never-destroyed, the archived flag surviving a re-save, and persistence across connections.
- **The librarian does the math**: recall scores land exactly on 0.9 / 0.8 / back-to-0.9 (the forgetting curve and its access reset, computed by hand); unrelated queries return nothing; cleanup archives precisely the lowest-retention records; a stale index entry is skipped, not crashed on.
- **The headline test**: remember a fact, close the manager, open a new one on the same file, recall succeeds — *memory survives a restart*.
- **Learning accumulates**: the diary stamps, orders, persists as valid JSONL, and reloads; identical failures share a cluster while different topics don't; the error trend goes negative when performance improves; and the end-to-end escalation test drives three real failures through the Cortex and finds exactly one "Known weakness" memory in the vault — with a fourth and fifth failure adding nothing twice.
