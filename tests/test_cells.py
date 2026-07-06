"""Phase 1 tests — the Cell system.

Pins the equations from docs/math_model.md to exact numbers:
confidence (Eq. 1.4-1.6), health (Eq. 1.8-1.9), tissue-free cell contract
(Design_Doc §9.3), memory retrieval (Eq. 5.2, 5.4), and learning scores
(Eq. 6.1-6.2). Property tests follow math_model.md §11.
"""

import math

import pytest

from incortex.cells import (
    BaseCell,
    CellFeedback,
    FeedbackCell,
    IntentCell,
    MemoryCell,
    TextCell,
)
from incortex.cells.cell_math import (
    clip01,
    entropy_confidence,
    ema_update,
    exponential_decay,
    jaccard_similarity,
    softmax,
    tokenize,
)


class EchoCell(BaseCell):
    """Minimal concrete Cell used to test the BaseCell contract."""

    def __init__(self, raw_confidence=1.0):
        super().__init__("echo", "test")
        self._raw = raw_confidence

    def _process(self, message):
        return message, self._raw


class ExplodingCell(BaseCell):
    def __init__(self):
        super().__init__("boom", "test")

    def _process(self, message):
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# Math helpers (math_model.md §11 property tests)
# ---------------------------------------------------------------------------


class TestCellMath:
    def test_clip01_bounds(self):
        assert clip01(-0.5) == 0.0
        assert clip01(1.5) == 1.0
        assert clip01(0.42) == 0.42

    def test_softmax_sums_to_one(self):
        p = softmax([1.0, 2.0, 3.0])
        assert sum(p) == pytest.approx(1.0)
        assert all(0.0 <= x <= 1.0 for x in p)

    def test_softmax_low_temperature_is_winner_take_all(self):
        # Eq 2.1 limit: T -> 0
        p = softmax([1.0, 2.0, 3.0], temperature=1e-3)
        assert max(p) > 0.999

    def test_softmax_high_temperature_is_uniform(self):
        # Eq 2.1 limit: T -> inf
        p = softmax([1.0, 2.0, 3.0], temperature=1e6)
        assert all(x == pytest.approx(1 / 3, abs=1e-3) for x in p)

    def test_entropy_confidence_limits(self):
        # Eq 1.4: one-hot -> 1, uniform -> 0
        assert entropy_confidence([1.0, 0.0, 0.0]) == pytest.approx(1.0)
        assert entropy_confidence([1 / 3] * 3) == pytest.approx(0.0, abs=1e-9)

    def test_entropy_confidence_in_range(self):
        c = entropy_confidence([0.6, 0.3, 0.1])
        assert 0.0 < c < 1.0

    def test_ema_moves_toward_sample(self):
        # Eq 1.7
        assert ema_update(1.0, 0.0, alpha=0.1) == pytest.approx(0.9)
        assert ema_update(0.0, 1.0, alpha=0.1) == pytest.approx(0.1)

    def test_exponential_decay_halves_at_half_life(self):
        # Eq 5.2: value halves exactly every half-life
        assert exponential_decay(0.0, half_life=100.0) == pytest.approx(1.0)
        assert exponential_decay(100.0, half_life=100.0) == pytest.approx(0.5)
        assert exponential_decay(200.0, half_life=100.0) == pytest.approx(0.25)

    def test_jaccard_similarity(self):
        a = frozenset({"a", "b", "c"})
        assert jaccard_similarity(a, a) == 1.0
        assert jaccard_similarity(a, frozenset({"x", "y"})) == 0.0
        assert jaccard_similarity(frozenset(), frozenset()) == 0.0

    def test_tokenize(self):
        assert tokenize("Hello, World! It's fine.") == ["hello", "world", "it's", "fine"]


# ---------------------------------------------------------------------------
# BaseCell contract (Design_Doc §9.3, math_model.md §1)
# ---------------------------------------------------------------------------


class TestBaseCellContract:
    def test_fresh_cell_reports_honest_history_confidence(self):
        # Eq 1.5 with n=0: (0+1)/(0+2) = 0.5
        assert EchoCell().historical_confidence == pytest.approx(0.5)

    def test_fresh_cell_is_active(self):
        # Seeds: success EMA 1.0 (no failures observed), confidence EMA 0.5,
        # latency EMA 0 -> h = 0.5*1.0 + 0.3*0.5 + 0.2*1.0 = 0.85 (Eq 1.8)
        report = EchoCell().health_check()
        assert report["status"] == "active"
        assert report["health"] == pytest.approx(0.85)

    def test_process_blends_raw_and_historical_confidence(self):
        # Eq 1.6: c = 0.7*raw + 0.3*hist = 0.7*1.0 + 0.3*0.5 = 0.85
        out = EchoCell(raw_confidence=1.0).process("hi")
        assert out.confidence == pytest.approx(0.85)
        assert out.raw_confidence == pytest.approx(1.0)
        assert out.content == "hi"

    def test_confidence_always_in_range(self):
        # §11 property 1: scores stay in [0,1] even for out-of-range raw values
        for raw in (-2.0, 0.0, 0.5, 1.0, 42.0):
            out = EchoCell(raw_confidence=raw).process("x")
            assert 0.0 <= out.confidence <= 1.0
            assert 0.0 <= out.raw_confidence <= 1.0

    def test_learn_updates_historical_confidence(self):
        # Eq 1.5 after 3 successes: (3+1)/(3+2) = 0.8
        cell = EchoCell()
        for _ in range(3):
            cell.learn(CellFeedback(success=True))
        assert cell.historical_confidence == pytest.approx(0.8)
        # Eq 1.6: next output blends the improved history
        assert cell.process("x").confidence == pytest.approx(0.7 * 1.0 + 0.3 * 0.8)

    def test_learn_accepts_plain_dicts(self):
        cell = EchoCell()
        cell.learn({"success": True, "rating": 0.9})
        assert cell.health_check()["feedback_count"] == 1

    def test_learn_rejects_bad_feedback(self):
        cell = EchoCell()
        with pytest.raises(ValueError):
            cell.learn({"rating": 0.5})  # missing success
        with pytest.raises(ValueError):
            cell.learn(CellFeedback(success=True, rating=2.0))  # out of range

    def test_failures_degrade_health_monotonically(self):
        # §11 property 2: health never rises as failures accumulate
        cell = EchoCell()
        scores = [cell.health_check()["health"]]
        for _ in range(30):
            cell.learn(CellFeedback(success=False))
            scores.append(cell.health_check()["health"])
        assert all(b <= a for a, b in zip(scores, scores[1:]))
        assert cell.health_check()["status"] == "failing"  # Eq 1.9

    def test_some_failures_mean_degraded(self):
        cell = EchoCell()
        for _ in range(6):
            cell.learn(CellFeedback(success=False))
        assert cell.health_check()["status"] == "degraded"

    def test_process_error_is_recorded_and_reraised(self):
        cell = ExplodingCell()
        before = cell.health_check()["health"]
        with pytest.raises(RuntimeError):
            cell.process("x")
        report = cell.health_check()
        assert report["errors"] == 1
        assert report["health"] < before

    def test_receive_then_process_then_emit(self):
        cell = EchoCell()
        cell.receive("stored input")
        out = cell.process()
        assert out.content == "stored input"
        assert cell.emit() is out

    def test_emit_before_process_returns_none(self):
        assert EchoCell().emit() is None

    def test_process_without_message_or_receive_raises(self):
        with pytest.raises(ValueError):
            EchoCell().process()

    def test_receive_rejects_none(self):
        with pytest.raises(ValueError):
            EchoCell().receive(None)

    def test_health_check_shape(self):
        report = EchoCell().health_check()
        for key in ("name", "type", "status", "health", "confidence",
                    "processed", "errors", "feedback_count"):
            assert key in report

    def test_constructor_validates_names(self):
        with pytest.raises(ValueError):
            EchoCell.__bases__[0]("", "test")  # BaseCell with empty name


# ---------------------------------------------------------------------------
# TextCell
# ---------------------------------------------------------------------------


class TestTextCell:
    def test_cleans_whitespace(self):
        out = TextCell().process("  hello   world \n")
        assert out.content["text"] == "hello world"
        assert out.content["word_count"] == 2

    def test_clean_text_scores_higher_than_symbols(self):
        clean = TextCell().process("this is a normal sentence").raw_confidence
        noisy = TextCell().process("@# $% ^& *! ~~").raw_confidence
        assert clean > noisy

    def test_rejects_empty_and_non_string(self):
        cell = TextCell()
        with pytest.raises(ValueError):
            cell.process("   ")
        with pytest.raises(ValueError):
            cell.process(123)


# ---------------------------------------------------------------------------
# IntentCell (Eq 1.3 softmax, Eq 1.4 entropy confidence)
# ---------------------------------------------------------------------------


class TestIntentCell:
    @pytest.mark.parametrize(
        ("text", "intent"),
        [
            ("Teach yourself what photosynthesis is.", "teach"),
            ("Remember that I like very simple explanations.", "remember"),
            ("Explain neural networks.", "explain"),
            ("hello there", "chat"),
        ],
    )
    def test_mvp_demo_intents(self, text, intent):
        assert IntentCell().process(text).content["intent"] == intent

    def test_distribution_sums_to_one(self):
        dist = IntentCell().process("Explain gravity").content["distribution"]
        assert sum(dist.values()) == pytest.approx(1.0)

    def test_clear_intent_more_confident_than_ambiguous(self):
        cell = IntentCell()
        clear = cell.process("Remember that I like short answers.").raw_confidence
        vague = cell.process("the weather over mountains").raw_confidence
        assert clear > vague + 0.1

    def test_ambiguous_input_has_near_zero_confidence(self):
        # No keywords -> uniform distribution -> Eq 1.4 gives ~0
        out = IntentCell().process("zzz qqq vvv")
        assert out.raw_confidence == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# MemoryCell (Eq 5.2 recency, Eq 5.4 retrieval score)
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class TestMemoryCell:
    def test_store_then_retrieve(self):
        cell = MemoryCell()
        cell.process({"action": "store", "content": "photosynthesis makes food from sunlight"})
        out = cell.process({"action": "retrieve", "query": "what is photosynthesis"})
        results = out.content["results"]
        assert len(results) == 1
        assert "photosynthesis" in results[0]["content"]
        assert 0.0 <= results[0]["score"] <= 1.0

    def test_more_similar_ranks_higher(self):
        cell = MemoryCell()
        cell.process({"action": "store", "content": "the moon orbits the earth"})
        cell.process({"action": "store", "content": "photosynthesis needs sunlight water and carbon dioxide"})
        results = cell.process(
            {"action": "retrieve", "query": "photosynthesis sunlight water"}
        ).content["results"]
        assert "photosynthesis" in results[0]["content"]

    def test_newer_memory_ranks_higher_at_equal_similarity(self):
        # Eq 5.2: recency decays with half-life
        clock = FakeClock()
        cell = MemoryCell(half_life_seconds=100.0, clock=clock)
        cell.process({"action": "store", "content": "python is a snake"})
        clock.now = 100.0
        cell.process({"action": "store", "content": "python is a snake"})
        results = cell.process({"action": "retrieve", "query": "python snake"}).content["results"]
        assert len(results) == 2
        assert results[0]["stored_at"] > results[1]["stored_at"]

    def test_irrelevant_memories_not_returned(self):
        # sim = 0 entries are excluded no matter how fresh (math §5.4 intent)
        cell = MemoryCell()
        cell.process({"action": "store", "content": "the moon orbits the earth"})
        results = cell.process({"action": "retrieve", "query": "quantum chromodynamics"}).content["results"]
        assert results == []

    def test_top_k_is_respected(self):
        cell = MemoryCell()
        for i in range(5):
            cell.process({"action": "store", "content": f"cats like fish variant {i}"})
        results = cell.process(
            {"action": "retrieve", "query": "cats like fish", "top_k": 2}
        ).content["results"]
        assert len(results) == 2

    def test_store_confidence_is_certain(self):
        out = MemoryCell().process({"action": "store", "content": "a fact"})
        assert out.raw_confidence == pytest.approx(1.0)

    def test_retrieve_confidence_is_top_score(self):
        cell = MemoryCell()
        cell.process({"action": "store", "content": "cats like fish"})
        out = cell.process({"action": "retrieve", "query": "cats like fish"})
        assert out.raw_confidence == pytest.approx(out.content["results"][0]["score"])

    def test_validates_messages(self):
        cell = MemoryCell()
        with pytest.raises(ValueError):
            cell.process({"action": "explode"})
        with pytest.raises(ValueError):
            cell.process({"action": "store", "content": "   "})
        with pytest.raises(ValueError):
            cell.process({"action": "store", "content": "x", "importance": 3.0})
        with pytest.raises(ValueError):
            cell.process("not a dict")


# ---------------------------------------------------------------------------
# FeedbackCell (Eq 6.1 normalization, Eq 6.2 learning score)
# ---------------------------------------------------------------------------


class TestFeedbackCell:
    def test_rating_normalization(self):
        # Eq 6.1: 4 on a 1-5 scale -> 0.75
        out = FeedbackCell().process(
            {"success": True, "rating": 4, "rating_min": 1, "rating_max": 5}
        )
        assert out.content["normalized_rating"] == pytest.approx(0.75)

    def test_perfect_task_scores_high_band(self):
        # Eq 6.2: 0.4*1 + 0.4*1 = 0.8 -> high (matches math §9 worked example)
        out = FeedbackCell().process({"success": True, "rating": 1.0})
        assert out.content["learning_score"] == pytest.approx(0.8)
        assert out.content["band"] == "high"

    def test_success_without_rating_uses_success_as_proxy(self):
        out = FeedbackCell().process({"success": True})
        assert out.content["learning_score"] == pytest.approx(0.8)

    def test_failure_with_penalty_is_low_band_and_clipped(self):
        # §11 property 1: clip keeps L in [0,1]
        out = FeedbackCell().process(
            {"success": False, "rating": 0.0, "correction_severity": 1.0, "penalty": True}
        )
        assert out.content["learning_score"] == 0.0
        assert out.content["band"] == "low"

    def test_correction_lowers_score_into_medium(self):
        # 0.4 + 0.4 - 0.3*1.0 = 0.5 -> medium
        out = FeedbackCell().process(
            {"success": True, "rating": 1.0, "correction_severity": 1.0}
        )
        assert out.content["learning_score"] == pytest.approx(0.5)
        assert out.content["band"] == "medium"

    def test_validates_messages(self):
        cell = FeedbackCell()
        with pytest.raises(ValueError):
            cell.process({"rating": 1.0})  # missing success
        with pytest.raises(ValueError):
            cell.process({"success": True, "rating": 9, "rating_min": 1, "rating_max": 5})
        with pytest.raises(ValueError):
            cell.process({"success": True, "correction_severity": -1})


# ---------------------------------------------------------------------------
# Boundary guards — the remaining fail-fast branches
# ---------------------------------------------------------------------------


class TestBoundaryGuards:
    def test_math_helper_guards(self):
        with pytest.raises(ValueError):
            softmax([1.0, 2.0], temperature=0)
        with pytest.raises(ValueError):
            exponential_decay(1.0, half_life=0)
        assert entropy_confidence([1.0]) == 1.0  # single option: nothing to doubt

    def test_constructor_validates_cell_type(self):
        with pytest.raises(ValueError):
            BaseCell("named", "")

    def test_base_cell_process_is_abstract(self):
        with pytest.raises(NotImplementedError):
            BaseCell("bare", "base").process("x")

    def test_learn_rejects_non_feedback_objects(self):
        cell = EchoCell()
        with pytest.raises(ValueError):
            cell.learn(42)
        with pytest.raises(ValueError):
            cell.learn(CellFeedback(success="yes"))  # non-bool success

    def test_feedback_cell_rejects_bad_shapes(self):
        cell = FeedbackCell()
        with pytest.raises(ValueError):
            cell.process("not a dict")
        with pytest.raises(ValueError):
            cell.process({"success": True, "rating": "five"})
        with pytest.raises(ValueError):
            cell.process({"success": True, "rating": 1, "rating_min": 5, "rating_max": 5})
        with pytest.raises(ValueError):
            cell.process({"success": True, "penalty": "yes"})

    def test_memory_cell_rejects_bad_top_k(self):
        with pytest.raises(ValueError):
            MemoryCell().process({"action": "retrieve", "query": "x", "top_k": 0})


# ---------------------------------------------------------------------------
# Success criteria (Design_Doc §21 Phase 1) — one test per criterion
# ---------------------------------------------------------------------------


class TestPhase1SuccessCriteria:
    def test_a_cell_can_receive_process_output_learn_and_report(self):
        cell = IntentCell()
        cell.receive("Explain neural networks.")          # receive input
        out = cell.process()                              # process input
        assert out.content["intent"] == "explain"         # return output
        cell.learn(CellFeedback(success=True))            # store feedback
        report = cell.health_check()                      # report health
        assert report["feedback_count"] == 1
        assert report["status"] in {"active", "degraded", "failing"}
