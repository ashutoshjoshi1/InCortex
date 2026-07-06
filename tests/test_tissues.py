"""Phase 2 tests — the Tissue system.

Pins math_model.md §2 to exact numbers: confidence-weighted combination
(Eq 2.1-2.2), tissue confidence and conservative health (Eq 2.4), plus the
Phase 2 success criterion from Design_Doc §21:
input → IntentCell → MemoryCell → ResponseCell.
"""

import pytest

from incortex.cells import BaseCell, MemoryCell, ResponseCell
from incortex.cells.cell_math import confidence_weights, status_band
from incortex.tissues import (
    BaseTissue,
    LanguageTissue,
    LearningTissue,
    MemoryTissue,
    TissueOutput,
)


class FixedCell(BaseCell):
    """Returns a fixed answer with a fixed raw confidence."""

    def __init__(self, name, raw_confidence=1.0, content="ok"):
        super().__init__(name, "test")
        self._raw = raw_confidence
        self._content = content

    def _process(self, message):
        return self._content, self._raw


class PickyCell(BaseCell):
    """Only accepts strings starting with 'ok' — used to test routing."""

    def __init__(self, name="picky"):
        super().__init__(name, "test")

    def _validate(self, message):
        if not (isinstance(message, str) and message.startswith("ok")):
            raise ValueError("picky cell rejects this")

    def _process(self, message):
        return f"picky:{message}", 1.0


def make_failing_cell(name="sick"):
    """A cell driven into 'failing' by 30 negative feedbacks (as in Phase 1 tests)."""
    cell = FixedCell(name)
    for _ in range(30):
        cell.learn({"success": False})
    return cell


# ---------------------------------------------------------------------------
# New math helpers (Eq 2.1, Eq 1.9 as shared function)
# ---------------------------------------------------------------------------


class TestTissueMath:
    def test_confidence_weights_sum_to_one(self):
        weights = confidence_weights([0.9, 0.5, 0.1])
        assert sum(weights) == pytest.approx(1.0)

    def test_higher_confidence_gets_more_weight(self):
        weights = confidence_weights([0.9, 0.5])
        assert weights[0] > weights[1]

    def test_equal_confidence_means_equal_weight(self):
        weights = confidence_weights([0.6, 0.6])
        assert weights[0] == pytest.approx(weights[1])

    def test_status_band(self):
        assert status_band(0.85) == "active"
        assert status_band(0.5) == "degraded"
        assert status_band(0.1) == "failing"


# ---------------------------------------------------------------------------
# BaseTissue (Design_Doc §10.1 responsibilities)
# ---------------------------------------------------------------------------


class TestBaseTissue:
    def test_add_cell_and_list(self):
        tissue = BaseTissue("t")
        cell = FixedCell("a")
        tissue.add_cell(cell)
        assert tissue.cells == (cell,)

    def test_add_cell_rejects_non_cells_and_duplicates(self):
        tissue = BaseTissue("t")
        with pytest.raises(ValueError):
            tissue.add_cell("not a cell")
        tissue.add_cell(FixedCell("a"))
        with pytest.raises(ValueError):
            tissue.add_cell(FixedCell("a"))

    def test_get_cell(self):
        tissue = BaseTissue("t")
        cell = FixedCell("a")
        tissue.add_cell(cell)
        assert tissue.get_cell("a") is cell
        with pytest.raises(ValueError):
            tissue.get_cell("missing")

    def test_constructor_validates_name(self):
        with pytest.raises(ValueError):
            BaseTissue("")

    def test_empty_tissue_cannot_process(self):
        with pytest.raises(ValueError):
            BaseTissue("t").process("x")

    def test_empty_tissue_is_failing(self):
        report = BaseTissue("t").health_check()
        assert report["health"] == 0.0
        assert report["status"] == "failing"

    def test_broadcast_routes_only_to_accepting_cells(self):
        # "Send messages to the right Cell" — PickyCell rejects, FixedCell accepts
        tissue = BaseTissue("t")
        tissue.add_cell(FixedCell("always"))
        tissue.add_cell(PickyCell("picky"))
        out = tissue.process("not for picky")
        assert set(out.content) == {"always"}
        out = tissue.process("ok for both")
        assert set(out.content) == {"always", "picky"}

    def test_no_accepting_cell_raises(self):
        tissue = BaseTissue("t")
        tissue.add_cell(PickyCell("picky"))
        with pytest.raises(ValueError):
            tissue.process("rejected by all")

    def test_combined_confidence_favors_the_confident_cell(self):
        # Eq 2.1 + 2.4: raws (1.0, 0.5) blend to (0.85, 0.5);
        # softmax([0.85, 0.5] / T=0.5) -> weights (0.668, 0.332);
        # c_T = 0.668*0.85 + 0.332*0.5 = 0.734
        tissue = BaseTissue("t")
        tissue.add_cell(FixedCell("sure", raw_confidence=1.0))
        tissue.add_cell(FixedCell("unsure", raw_confidence=0.5))
        out = tissue.process("x")
        assert out.confidence == pytest.approx(0.734, abs=1e-3)
        assert out.confidence > (0.85 + 0.5) / 2  # beats the plain average
        assert out.confidence <= 0.85  # never exceeds the best member

    def test_returns_tissue_output(self):
        tissue = BaseTissue("t")
        tissue.add_cell(FixedCell("a"))
        out = tissue.process("x")
        assert isinstance(out, TissueOutput)
        assert out.tissue_name == "t"
        assert len(out.cell_outputs) == 1

    def test_learn_propagates_to_all_cells(self):
        tissue = BaseTissue("t")
        tissue.add_cell(FixedCell("a"))
        tissue.add_cell(FixedCell("b"))
        tissue.learn({"success": True})
        for cell in tissue.cells:
            assert cell.health_check()["feedback_count"] == 1

    def test_health_is_mean_when_no_critical_cells(self):
        # Eq 2.4: healthy 0.85 + failing 0.3712 -> mean 0.6106 (degraded)
        tissue = BaseTissue("t")
        tissue.add_cell(FixedCell("fine"))
        tissue.add_cell(make_failing_cell())
        report = tissue.health_check()
        assert report["health"] == pytest.approx(0.611, abs=1e-3)
        assert report["status"] == "degraded"

    def test_critical_cell_drags_tissue_down(self):
        # Eq 2.4: a tissue is only as healthy as its weakest critical cell
        tissue = BaseTissue("t")
        tissue.add_cell(FixedCell("fine"))
        tissue.add_cell(make_failing_cell(), critical=True)
        report = tissue.health_check()
        assert report["health"] == pytest.approx(0.371, abs=1e-3)
        assert report["status"] == "failing"

    def test_health_report_includes_all_cells(self):
        tissue = BaseTissue("t")
        tissue.add_cell(FixedCell("a"))
        tissue.add_cell(FixedCell("b"))
        report = tissue.health_check()
        assert [cell["name"] for cell in report["cells"]] == ["a", "b"]


# ---------------------------------------------------------------------------
# LanguageTissue — TextCell → IntentCell (→ ResponseCell)
# ---------------------------------------------------------------------------


class TestLanguageTissue:
    def test_understand_cleans_and_classifies(self):
        out = LanguageTissue().process("  Teach   yourself what photosynthesis is. ")
        assert out.content["text"] == "Teach yourself what photosynthesis is."
        assert out.content["intent"] == "teach"
        assert 0.0 < out.confidence <= 1.0
        assert len(out.cell_outputs) == 2  # text cell handed off to intent cell

    def test_respond_teach(self):
        out = LanguageTissue().respond("teach", "the sky is blue", [])
        assert "learned" in out.content["reply"].lower()

    def test_respond_explain_uses_memory(self):
        results = [{"content": "photosynthesis makes food from sunlight", "score": 0.66}]
        out = LanguageTissue().respond("explain", "what is photosynthesis", results)
        assert "photosynthesis makes food" in out.content["reply"]
        assert out.confidence > 0.3

    def test_respond_explain_without_memory_admits_ignorance(self):
        out = LanguageTissue().respond("explain", "what is dark matter", [])
        assert "teach me" in out.content["reply"].lower()
        assert out.cell_outputs[0].raw_confidence == pytest.approx(0.1)

    def test_has_three_cells(self):
        assert len(LanguageTissue().cells) == 3


# ---------------------------------------------------------------------------
# MemoryTissue — merged retrieval across MemoryCells
# ---------------------------------------------------------------------------


class TestMemoryTissue:
    def test_store_then_retrieve(self):
        tissue = MemoryTissue()
        tissue.store("photosynthesis makes food from sunlight")
        out = tissue.retrieve("what is photosynthesis")
        assert len(out.content["results"]) == 1
        assert out.confidence == pytest.approx(out.content["results"][0]["score"])

    def test_merges_results_across_cells(self):
        # Two memory cells with different facts: retrieval sees both notebooks
        cell_a, cell_b = MemoryCell("mem_a"), MemoryCell("mem_b")
        cell_a.process({"action": "store", "content": "cats like fish"})
        cell_b.process({"action": "store", "content": "cats like sleeping"})
        tissue = MemoryTissue(memory_cells=[cell_a, cell_b])
        results = tissue.retrieve("what do cats like").content["results"]
        contents = {result["content"] for result in results}
        assert contents == {"cats like fish", "cats like sleeping"}

    def test_deduplicates_identical_facts(self):
        tissue = MemoryTissue(memory_cells=[MemoryCell("mem_a"), MemoryCell("mem_b")])
        tissue.store("the moon orbits the earth")  # stored in both cells
        results = tissue.retrieve("moon orbits").content["results"]
        assert len(results) == 1

    def test_top_k_applies_after_merging(self):
        tissue = MemoryTissue()
        for i in range(5):
            tissue.store(f"cats like fish variant {i}")
        results = tissue.retrieve("cats like fish", top_k=2).content["results"]
        assert len(results) == 2

    def test_empty_retrieval_has_zero_confidence(self):
        out = MemoryTissue().retrieve("anything at all")
        assert out.content["results"] == []
        assert out.confidence == 0.0

    def test_process_dispatches_like_a_memory_cell(self):
        tissue = MemoryTissue()
        tissue.process({"action": "store", "content": "a fact"})
        out = tissue.process({"action": "retrieve", "query": "a fact"})
        assert len(out.content["results"]) == 1
        with pytest.raises(ValueError):
            tissue.process({"action": "explode"})
        with pytest.raises(ValueError):
            tissue.process("not a dict")

    def test_store_passes_importance_through(self):
        tissue = MemoryTissue()
        tissue.store("a crucial fact", importance=1.0)
        result = tissue.retrieve("crucial fact").content["results"][0]
        assert result["importance"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# LearningTissue — score aggregation and feedback distribution
# ---------------------------------------------------------------------------


class TestLearningTissue:
    def test_scores_feedback_events(self):
        out = LearningTissue().process({"success": True, "rating": 1.0})
        assert out.content["learning_score"] == pytest.approx(0.8)
        assert out.content["band"] == "high"

    def test_tracks_running_score(self):
        tissue = LearningTissue()
        first = tissue.process({"success": True, "rating": 1.0})
        assert first.content["running_score"] == pytest.approx(0.8)
        second = tissue.process({"success": False, "rating": 0.0})
        # EMA (Eq 1.7): 0.9*0.8 + 0.1*0.0 = 0.72
        assert second.content["running_score"] == pytest.approx(0.72)
        assert second.content["events"] == 2

    def test_distribute_teaches_other_cells(self):
        tissue = LearningTissue()
        pupils = [FixedCell("a"), FixedCell("b")]
        result = tissue.distribute({"success": True, "rating": 1.0}, pupils)
        assert result.content["band"] == "high"
        for pupil in pupils:
            report = pupil.health_check()
            assert report["feedback_count"] == 1
            assert report["confidence"] > 0.5  # track record moved up


# ---------------------------------------------------------------------------
# Phase 2 success criterion (Design_Doc §21):
# input → IntentCell → MemoryCell → ResponseCell
# ---------------------------------------------------------------------------


class TestPhase2SuccessCriteria:
    def test_cells_cooperate_across_tissues_on_one_task(self):
        language = LanguageTissue()
        memory = MemoryTissue()

        # Teach: input → IntentCell (via LanguageTissue) → MemoryCell
        taught = language.process("Teach yourself what photosynthesis is.")
        assert taught.content["intent"] == "teach"
        memory.store(taught.content["text"])
        ack = language.respond("teach", taught.content["text"], [])
        assert "learned" in ack.content["reply"].lower()

        # Ask: input → IntentCell → MemoryCell → ResponseCell
        asked = language.process("What is photosynthesis?")
        assert asked.content["intent"] == "explain"
        found = memory.retrieve(asked.content["text"])
        answer = language.respond("explain", asked.content["text"], found.content["results"])
        assert "photosynthesis" in answer.content["reply"].lower()
        assert "from memory" in answer.content["reply"].lower()
        assert answer.confidence > 0.3
