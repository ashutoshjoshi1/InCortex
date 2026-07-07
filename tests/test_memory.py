"""Phase 5 tests — the memory system.

Pins math_model.md §5 to exact numbers: clipped-cosine similarity over
hashed embeddings (Eq 5.1 as amended), the forgetting curve with access
reset (Eq 5.2), the retrieval triad (Eq 5.4), and retention-based archiving
(Eq 5.5). The headline property: memory persists across restarts.
"""

import dataclasses

import pytest

from incortex.memory import (
    HashingEmbedder,
    LongTermMemory,
    MemoryManager,
    MemoryRecord,
    ShortTermMemory,
    VectorIndex,
    VectorMemoryCell,
    cosine_similarity,
    new_memory_record,
    similarity01,
)

WEEK_SECONDS = 7 * 24 * 3600.0


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


# ---------------------------------------------------------------------------
# MemoryRecord (Design_Doc §15.3)
# ---------------------------------------------------------------------------


class TestMemoryRecord:
    def test_factory_fills_the_record(self):
        clock = FakeClock()
        clock.now = 42.0
        record = new_memory_record("the sky is blue", memory_type="semantic",
                                   source="user", importance=0.7,
                                   tags=("sky", "color"), clock=clock)
        assert len(record.memory_id) == 32
        assert record.content == "the sky is blue"
        assert record.created_at == 42.0
        assert record.last_accessed_at == 42.0
        assert record.access_count == 0
        assert record.tags == ("sky", "color")

    def test_records_are_immutable(self):
        record = new_memory_record("a fact")
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.content = "changed"

    def test_validation(self):
        with pytest.raises(ValueError):
            new_memory_record("   ")
        with pytest.raises(ValueError):
            new_memory_record("x", memory_type="telepathic")
        with pytest.raises(ValueError):
            new_memory_record("x", importance=1.5)
        with pytest.raises(ValueError):
            new_memory_record("x", confidence=-0.1)


# ---------------------------------------------------------------------------
# HashingEmbedder and similarity (Eq 5.1 as amended)
# ---------------------------------------------------------------------------


class TestEmbeddingSimilarity:
    def test_identical_text_is_fully_similar(self):
        embedder = HashingEmbedder()
        a = embedder.embed("gravity pulls objects together")
        assert similarity01(a, a) == pytest.approx(1.0)

    def test_unrelated_content_is_zero_not_half(self):
        # The Phase 5 amendment: unrelated must be 0, not 0.5
        embedder = HashingEmbedder()
        a = embedder.embed("photosynthesis sunlight chlorophyll")
        b = embedder.embed("quarterly revenue forecast spreadsheet")
        assert similarity01(a, b) == pytest.approx(0.0, abs=0.05)

    def test_morphological_relatives_share_trigrams(self):
        embedder = HashingEmbedder()
        a = embedder.embed("photosynthesis")
        b = embedder.embed("photosynthesize")
        assert similarity01(a, b) > 0.3

    def test_stopword_only_text_embeds_to_nothing(self):
        embedder = HashingEmbedder()
        empty = embedder.embed("what is it")
        real = embedder.embed("gravity")
        assert similarity01(empty, real) == 0.0

    def test_embedding_is_deterministic_across_instances(self):
        assert (HashingEmbedder().embed("gravity pulls")
                == HashingEmbedder().embed("gravity pulls"))

    def test_dimensions(self):
        assert len(HashingEmbedder(dimensions=64).embed("hello world")) == 64
        with pytest.raises(ValueError):
            HashingEmbedder(dimensions=4)

    def test_cosine_guards(self):
        with pytest.raises(ValueError):
            cosine_similarity((1.0, 0.0), (1.0, 0.0, 0.0))
        assert cosine_similarity((0.0, 0.0), (1.0, 0.0)) == 0.0


class TestVectorIndex:
    def test_add_and_rank(self):
        index = VectorIndex(HashingEmbedder())
        index.add("m1", "gravity pulls objects toward each other")
        index.add("m2", "photosynthesis turns sunlight into food")
        similarities = index.similarities("how does gravity work")
        assert "m1" in similarities
        assert "m2" not in similarities  # zero-similarity ids are omitted

    def test_remove(self):
        index = VectorIndex(HashingEmbedder())
        index.add("m1", "gravity pulls")
        index.remove("m1")
        assert index.similarities("gravity") == {}


# ---------------------------------------------------------------------------
# ShortTermMemory (bounded recency buffer)
# ---------------------------------------------------------------------------


class TestShortTermMemory:
    def test_recent_is_newest_first(self):
        short = ShortTermMemory(capacity=10)
        for text in ("one", "two", "three"):
            short.add(new_memory_record(text))
        assert [record.content for record in short.recent(2)] == ["three", "two"]

    def test_capacity_evicts_the_oldest(self):
        short = ShortTermMemory(capacity=2)
        for text in ("one", "two", "three"):
            short.add(new_memory_record(text))
        assert [record.content for record in short.recent()] == ["three", "two"]
        assert len(short) == 2

    def test_clear(self):
        short = ShortTermMemory(capacity=5)
        short.add(new_memory_record("x"))
        short.clear()
        assert len(short) == 0

    def test_validation(self):
        with pytest.raises(ValueError):
            ShortTermMemory(capacity=0)
        with pytest.raises(ValueError):
            ShortTermMemory(capacity=5).add("not a record")


# ---------------------------------------------------------------------------
# LongTermMemory (SQLite persistence)
# ---------------------------------------------------------------------------


class TestLongTermMemory:
    def test_save_and_get_roundtrip(self):
        store = LongTermMemory()
        record = new_memory_record("the moon orbits the earth",
                                   importance=0.8, tags=("astronomy",))
        store.save(record)
        loaded = store.get(record.memory_id)
        assert loaded == record

    def test_save_is_an_upsert(self):
        store = LongTermMemory()
        record = new_memory_record("a fact")
        store.save(record)
        updated = dataclasses.replace(record, access_count=5)
        store.save(updated)
        assert store.get(record.memory_id).access_count == 5
        assert store.count() == 1

    def test_delete(self):
        store = LongTermMemory()
        record = new_memory_record("a fact")
        store.save(record)
        assert store.delete(record.memory_id) is True
        assert store.get(record.memory_id) is None
        assert store.delete("missing") is False

    def test_archive_hides_but_never_destroys(self):
        # Design_Doc §25.3: memory is compressed or archived, never silently lost
        store = LongTermMemory()
        record = new_memory_record("old fact")
        store.save(record)
        assert store.archive(record.memory_id) is True
        assert store.count() == 0
        assert store.count(include_archived=True) == 1
        assert len(store.all_records(include_archived=True)) == 1

    def test_archived_flag_survives_a_resave(self):
        store = LongTermMemory()
        record = new_memory_record("a fact")
        store.save(record)
        store.archive(record.memory_id)
        store.save(dataclasses.replace(record, access_count=1))
        assert store.count() == 0  # still archived

    def test_save_rejects_non_records(self):
        with pytest.raises(ValueError):
            LongTermMemory().save({"content": "not a record"})

    def test_persists_across_connections(self, tmp_path):
        db_path = tmp_path / "memories.db"
        first = LongTermMemory(db_path)
        record = new_memory_record("persistent fact")
        first.save(record)
        first.close()
        second = LongTermMemory(db_path)
        assert second.get(record.memory_id) == record
        second.close()


# ---------------------------------------------------------------------------
# MemoryManager (Eq 5.2, 5.4, 5.5 orchestrated)
# ---------------------------------------------------------------------------


class TestMemoryManager:
    def make_manager(self, **kwargs):
        clock = FakeClock()
        manager = MemoryManager(clock=clock, **kwargs)
        return manager, clock

    def test_remember_stores_everywhere(self):
        manager, _ = self.make_manager()
        record = manager.remember("gravity pulls objects together")
        assert manager.long_term.get(record.memory_id) == record
        assert manager.short_term.recent(1)[0] is record
        assert manager.stats()["active"] == 1

    def test_recall_scores_the_full_triad(self):
        # Eq 5.4 at t=0 with identical text: 0.6*1 + 0.2*1 + 0.2*0.5 = 0.9
        manager, _ = self.make_manager()
        manager.remember("gravity pulls objects together")
        results = manager.recall("gravity pulls objects together")
        assert results[0]["score"] == pytest.approx(0.9)
        assert results[0]["similarity"] == pytest.approx(1.0)

    def test_recency_decays_with_the_forgetting_curve(self):
        # Eq 5.2: one half-life later the recency term is halved
        manager, clock = self.make_manager()
        manager.remember("gravity pulls objects together")
        clock.now = WEEK_SECONDS  # default half-life is 7 days
        results = manager.recall("gravity pulls objects together")
        assert results[0]["score"] == pytest.approx(0.8)  # 0.6 + 0.2*0.5 + 0.1

    def test_recall_resets_the_forgetting_clock(self):
        # Accessing a memory strengthens it (Eq 5.2 note)
        manager, clock = self.make_manager()
        manager.remember("gravity pulls objects together")
        clock.now = WEEK_SECONDS
        manager.recall("gravity pulls objects together")
        results = manager.recall("gravity pulls objects together")
        assert results[0]["score"] == pytest.approx(0.9)  # recency back to 1.0

    def test_unrelated_queries_recall_nothing(self):
        manager, _ = self.make_manager()
        manager.remember("gravity pulls objects together")
        assert manager.recall("quarterly revenue forecast") == []

    def test_top_k(self):
        manager, _ = self.make_manager()
        for i in range(5):
            manager.remember(f"cats like fish variant {i}")
        assert len(manager.recall("cats like fish", top_k=2)) == 2

    def test_reinforce_raises_importance(self):
        manager, _ = self.make_manager()
        record = manager.remember("a fact", importance=0.5)
        manager.reinforce(record.memory_id, 0.3)
        assert manager.long_term.get(record.memory_id).importance == pytest.approx(0.8)
        manager.reinforce(record.memory_id, 0.9)  # clipped at 1.0
        assert manager.long_term.get(record.memory_id).importance == 1.0
        with pytest.raises(ValueError):
            manager.reinforce("missing", 0.1)

    def test_forget_removes_everywhere(self):
        manager, _ = self.make_manager()
        record = manager.remember("a fact to forget")
        assert manager.forget(record.memory_id) is True
        assert manager.recall("a fact to forget") == []
        assert manager.forget(record.memory_id) is False

    def test_cleanup_archives_the_lowest_retention(self):
        # Eq 5.5: keep the top-budget records by importance * decay
        manager, _ = self.make_manager()
        keep_a = manager.remember("important fact one", importance=0.9)
        keep_b = manager.remember("important fact two", importance=0.7)
        drop_a = manager.remember("trivial fact one", importance=0.2)
        drop_b = manager.remember("trivial fact two", importance=0.1)
        archived = manager.cleanup(budget=2)
        assert archived == 2
        assert manager.stats()["active"] == 2
        assert manager.stats()["archived"] == 2
        active_ids = {record.memory_id for record in manager.long_term.all_records()}
        assert active_ids == {keep_a.memory_id, keep_b.memory_id}
        # Archived records are hidden from recall but never destroyed
        assert manager.recall("trivial") == []
        all_ids = {record.memory_id
                   for record in manager.long_term.all_records(include_archived=True)}
        assert {drop_a.memory_id, drop_b.memory_id} <= all_ids

    def test_recall_survives_a_stale_index_entry(self):
        # If the vector index knows an id the store no longer has, recall
        # skips it instead of crashing
        manager, _ = self.make_manager()
        record = manager.remember("gravity pulls objects together")
        manager.long_term.delete(record.memory_id)  # store-only removal
        assert manager.recall("gravity pulls objects together") == []

    def test_cleanup_under_budget_is_a_no_op(self):
        manager, _ = self.make_manager()
        manager.remember("a fact")
        assert manager.cleanup(budget=10) == 0

    def test_memory_survives_a_restart(self, tmp_path):
        # The Phase 5 headline: remember a topic, restart, use it later
        db_path = tmp_path / "brain.db"
        first = MemoryManager(db_path=db_path)
        first.remember("photosynthesis turns sunlight into food")
        first.close()
        second = MemoryManager(db_path=db_path)
        results = second.recall("photosynthesis sunlight")
        assert len(results) == 1
        assert "photosynthesis" in results[0]["content"]
        second.close()


# ---------------------------------------------------------------------------
# VectorMemoryCell — the manager wearing the Cell contract
# ---------------------------------------------------------------------------


class TestVectorMemoryCell:
    def test_speaks_the_memory_cell_message_schema(self):
        cell = VectorMemoryCell(MemoryManager(clock=FakeClock()))
        stored = cell.process({"action": "store", "content": "cats like fish"})
        assert stored.content["stored"] == "cats like fish"
        assert stored.raw_confidence == pytest.approx(1.0)
        out = cell.process({"action": "retrieve", "query": "cats like fish"})
        results = out.content["results"]
        assert len(results) == 1
        assert out.raw_confidence == pytest.approx(results[0]["score"])
        assert "stored_at" in results[0]  # MemoryTissue merging relies on this

    def test_empty_retrieval_is_zero_confidence(self):
        cell = VectorMemoryCell(MemoryManager(clock=FakeClock()))
        out = cell.process({"action": "retrieve", "query": "anything"})
        assert out.content["results"] == []
        assert out.raw_confidence == 0.0

    def test_validates_like_a_memory_cell(self):
        cell = VectorMemoryCell(MemoryManager(clock=FakeClock()))
        with pytest.raises(ValueError):
            cell.process({"action": "explode"})
        with pytest.raises(ValueError):
            cell.process({"action": "store", "content": "x", "importance": 3.0})
