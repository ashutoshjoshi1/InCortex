"""Phase 3 tests — the Organ system.

Pins math_model.md §3 to exact numbers: pipeline confidence (Eq 3.1,
geometric and min modes), organ relevance (Eq 3.2 stand-in), recursive
health (Eq 2.4), and the safety gate (Eq 7.1-7.2) at organ level. Ends
with the Phase 3 success criterion from Design_Doc §21: a full task
passing through multiple Organs.
"""

import pytest

from incortex.cells import BaseCell
from incortex.cells.cell_math import overlap_coefficient, pipeline_confidence, tokenize
from incortex.organs import (
    BaseOrgan,
    LanguageOrgan,
    LearningOrgan,
    MemoryOrgan,
    OrganOutput,
    ReasoningOrgan,
    SafetyOrgan,
)
from incortex.tissues import BaseTissue


class FixedCell(BaseCell):
    def __init__(self, name, raw_confidence=1.0, content="ok"):
        super().__init__(name, "test")
        self._raw = raw_confidence
        self._content = content

    def _process(self, message):
        return self._content, self._raw


def make_failing_tissue(name="sick_tissue"):
    """A tissue whose critical cell has been driven into 'failing'."""
    cell = FixedCell("sick")
    for _ in range(30):
        cell.learn({"success": False})
    tissue = BaseTissue(name)
    tissue.add_cell(cell, critical=True)
    return tissue


def make_healthy_tissue(name="fine_tissue"):
    tissue = BaseTissue(name)
    tissue.add_cell(FixedCell("fine"))
    return tissue


# ---------------------------------------------------------------------------
# New math helpers (Eq 3.1, Eq 3.2 stand-in)
# ---------------------------------------------------------------------------


class TestOrganMath:
    def test_geometric_mean_punishes_the_weak_stage(self):
        # Eq 3.1 worked example from math_model.md §3
        assert pipeline_confidence([0.9, 0.9, 0.2]) == pytest.approx(0.545, abs=1e-3)

    def test_geometric_never_exceeds_arithmetic_mean(self):
        # §11 property 5
        for stages in ([0.9, 0.5], [0.3, 0.8, 0.6], [1.0, 0.1]):
            arithmetic = sum(stages) / len(stages)
            assert pipeline_confidence(stages) <= arithmetic + 1e-12

    def test_min_mode_returns_the_weakest_stage(self):
        assert pipeline_confidence([0.9, 0.4, 0.8], mode="min") == pytest.approx(0.4)

    def test_zero_stage_zeroes_the_chain(self):
        assert pipeline_confidence([1.0, 0.0, 1.0]) == 0.0

    def test_single_stage_is_itself(self):
        assert pipeline_confidence([0.7]) == pytest.approx(0.7)

    def test_guards(self):
        with pytest.raises(ValueError):
            pipeline_confidence([])
        with pytest.raises(ValueError):
            pipeline_confidence([0.5], mode="average")

    def test_overlap_coefficient(self):
        a = frozenset(tokenize("explain photosynthesis"))
        keywords = frozenset({"explain", "describe", "summarize"})
        assert overlap_coefficient(a, keywords) == pytest.approx(0.5)  # 1 / min(2, 3)
        assert overlap_coefficient(a, a) == 1.0
        assert overlap_coefficient(a, frozenset({"unrelated"})) == 0.0
        assert overlap_coefficient(frozenset(), keywords) == 0.0


# ---------------------------------------------------------------------------
# BaseOrgan
# ---------------------------------------------------------------------------


class TestBaseOrgan:
    def test_constructor_validates(self):
        with pytest.raises(ValueError):
            BaseOrgan("")
        with pytest.raises(ValueError):
            BaseOrgan("o", confidence_mode="average")

    def test_add_components_and_flattened_cells(self):
        organ = BaseOrgan("o")
        tissue = make_healthy_tissue()
        loose = FixedCell("loose")
        organ.add_tissue(tissue)
        organ.add_cell(loose)
        names = [cell.name for cell in organ.cells]
        assert names == ["fine", "loose"]

    def test_add_rejects_wrong_types_and_duplicates(self):
        organ = BaseOrgan("o")
        with pytest.raises(ValueError):
            organ.add_tissue(FixedCell("cell-not-tissue"))
        with pytest.raises(ValueError):
            organ.add_cell(make_healthy_tissue())
        organ.add_tissue(make_healthy_tissue("t"))
        with pytest.raises(ValueError):
            organ.add_tissue(make_healthy_tissue("t"))

    def test_process_is_abstract(self):
        with pytest.raises(NotImplementedError):
            BaseOrgan("o").process("x")

    def test_empty_organ_is_failing(self):
        report = BaseOrgan("o").health_check()
        assert report["health"] == 0.0
        assert report["status"] == "failing"

    def test_health_is_mean_when_no_critical_components(self):
        # Same numbers as the tissue tests: mean(0.85, 0.3712) = 0.6106
        organ = BaseOrgan("o")
        organ.add_tissue(make_healthy_tissue())
        organ.add_tissue(make_failing_tissue())
        report = organ.health_check()
        assert report["health"] == pytest.approx(0.611, abs=1e-3)
        assert report["status"] == "degraded"

    def test_critical_component_drags_organ_down(self):
        # Eq 2.4 applied recursively at the organ level
        organ = BaseOrgan("o")
        organ.add_tissue(make_healthy_tissue())
        organ.add_tissue(make_failing_tissue(), critical=True)
        report = organ.health_check()
        assert report["health"] == pytest.approx(0.371, abs=1e-3)
        assert report["status"] == "failing"

    def test_health_report_lists_components(self):
        organ = BaseOrgan("o")
        organ.add_tissue(make_healthy_tissue("t"))
        organ.add_cell(FixedCell("loose"))
        names = [component["name"] for component in organ.health_check()["components"]]
        assert names == ["t", "loose"]

    def test_learn_reaches_every_leaf_cell(self):
        organ = BaseOrgan("o")
        organ.add_tissue(make_healthy_tissue())
        organ.add_cell(FixedCell("loose"))
        organ.learn({"success": True})
        for cell in organ.cells:
            assert cell.health_check()["feedback_count"] == 1

    def test_relevance_matches_capability_keywords(self):
        # Eq 3.2 stand-in: token overlap with the organ's capability words
        organ = BaseOrgan("o", capability_keywords=("explain", "describe", "summarize"))
        assert organ.relevance("explain photosynthesis") == pytest.approx(0.5)
        assert organ.relevance("hello there") == 0.0
        assert organ.relevance("") == 0.0

    def test_pipeline_uses_the_organ_mode(self):
        geometric = BaseOrgan("g")
        conservative = BaseOrgan("c", confidence_mode="min")
        stages = [0.9, 0.4, 0.8]
        assert geometric.pipeline(stages) == pytest.approx(pipeline_confidence(stages))
        assert conservative.pipeline(stages) == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# LanguageOrgan
# ---------------------------------------------------------------------------


class TestLanguageOrgan:
    def test_understand(self):
        out = LanguageOrgan().understand("  Explain   neural networks. ")
        assert isinstance(out, OrganOutput)
        assert out.content["intent"] == "explain"
        assert out.content["text"] == "Explain neural networks."
        assert 0.0 < out.confidence <= 1.0

    def test_respond(self):
        results = [{"content": "a fact about networks", "score": 0.7}]
        out = LanguageOrgan().respond("explain", "neural networks", results)
        assert "a fact about networks" in out.content["reply"]

    def test_process_means_understand(self):
        assert LanguageOrgan().process("hello there").content["intent"] == "chat"

    def test_is_relevant_to_language_requests(self):
        assert LanguageOrgan().relevance("explain photosynthesis to me") > 0.0


# ---------------------------------------------------------------------------
# MemoryOrgan
# ---------------------------------------------------------------------------


class TestMemoryOrgan:
    def test_store_and_retrieve_roundtrip(self):
        organ = MemoryOrgan()
        organ.store("photosynthesis makes food from sunlight")
        out = organ.retrieve("what is photosynthesis")
        assert len(out.content["results"]) == 1
        assert out.confidence == pytest.approx(out.content["results"][0]["score"])

    def test_process_dispatches(self):
        organ = MemoryOrgan()
        organ.process({"action": "store", "content": "a fact"})
        out = organ.process({"action": "retrieve", "query": "a fact"})
        assert len(out.content["results"]) == 1

    def test_is_relevant_to_memory_requests(self):
        assert MemoryOrgan().relevance("remember my favorite color") > 0.0


# ---------------------------------------------------------------------------
# ReasoningOrgan
# ---------------------------------------------------------------------------


class TestReasoningOrgan:
    def test_reason_over_evidence(self):
        organ = ReasoningOrgan()
        evidence = [{"content": "photosynthesis makes food from sunlight", "score": 0.66}]
        out = organ.reason("What is photosynthesis?", evidence)
        assert out.content["supported"] is True
        assert "photosynthesis" in out.content["conclusion"]

    def test_no_evidence_is_an_honest_zero(self):
        out = ReasoningOrgan().reason("What is dark matter?", [])
        assert out.content["supported"] is False
        assert out.confidence == pytest.approx(0.15, abs=1e-2)  # 0.7*0 + 0.3*0.5 blend

    def test_uses_conservative_min_mode(self):
        # math_model.md §10: reasoning organ runs Eq 3.1 in min mode
        organ = ReasoningOrgan()
        assert organ.pipeline([0.9, 0.4, 0.8]) == pytest.approx(0.4)

    def test_process_takes_a_dict(self):
        out = ReasoningOrgan().process(
            {"question": "what is gravity", "evidence": [{"content": "gravity pulls things down", "score": 0.8}]}
        )
        assert out.content["supported"] is True
        with pytest.raises(ValueError):
            ReasoningOrgan().process("not a dict")


# ---------------------------------------------------------------------------
# LearningOrgan
# ---------------------------------------------------------------------------


class TestLearningOrgan:
    def test_score_reports_band_and_running_average(self):
        organ = LearningOrgan()
        out = organ.score({"success": True, "rating": 1.0})
        assert out.content["band"] == "high"
        assert out.content["running_score"] == pytest.approx(0.8)

    def test_distribute_teaches_participating_cells(self):
        organ = LearningOrgan()
        pupils = [FixedCell("a"), FixedCell("b")]
        organ.distribute({"success": True, "rating": 1.0}, pupils)
        for pupil in pupils:
            assert pupil.health_check()["feedback_count"] == 1

    def test_process_means_score(self):
        assert LearningOrgan().process({"success": False}).content["band"] == "low"


# ---------------------------------------------------------------------------
# SafetyOrgan (Eq 7.1-7.2 at organ level + blocklist + decision log)
# ---------------------------------------------------------------------------


class TestSafetyOrgan:
    def test_safe_action_within_ceiling_executes(self):
        out = SafetyOrgan().check("summarize_text", permission_level=1,
                                  harm_probability=0.05, impact=0.2)
        assert out.content["decision"] == "execute"
        assert out.content["risk"] == pytest.approx(0.01)

    def test_level_4_always_requires_a_human(self):
        out = SafetyOrgan().check("run_python", permission_level=4,
                                  harm_probability=0.01, impact=0.01)
        assert out.content["decision"] == "require_approval"

    def test_risky_action_requires_approval_even_at_low_level(self):
        out = SafetyOrgan().check("write_note", permission_level=1,
                                  harm_probability=0.8, impact=0.6)
        assert out.content["decision"] == "require_approval"

    def test_above_ceiling_but_safe_is_blocked(self):
        out = SafetyOrgan().check("call_external_api", permission_level=3,
                                  harm_probability=0.1, impact=0.1)
        assert out.content["decision"] == "block"

    def test_fail_closed_when_risk_is_unknown(self):
        # §11 property 6: missing risk estimates are treated as worst case
        out = SafetyOrgan().check("send_email", permission_level=3)
        assert out.content["risk"] == pytest.approx(1.0)
        assert out.content["decision"] == "require_approval"

    def test_blocklisted_actions_never_run(self):
        # Design_Doc §26.3: "Change safety policy → blocked"
        out = SafetyOrgan().check("change_safety_policy", permission_level=0,
                                  harm_probability=0.0, impact=0.0)
        assert out.content["decision"] == "block"
        assert "blocklist" in out.content["reason"]

    def test_design_doc_safety_examples(self):
        # Design_Doc §26.3 acceptance cases
        organ = SafetyOrgan()
        assert organ.check("delete_all_files", permission_level=5).content["decision"] == "block"
        assert organ.check("run_shell_command", permission_level=5).content["decision"] == "require_approval"
        assert organ.check("send_email", permission_level=3).content["decision"] == "require_approval"

    def test_every_decision_is_logged(self):
        organ = SafetyOrgan()
        organ.check("summarize_text", permission_level=1, harm_probability=0.0, impact=0.0)
        organ.check("change_safety_policy", permission_level=0)
        decisions = organ.decisions
        assert len(decisions) == 2
        assert decisions[0]["decision"] == "execute"
        assert decisions[1]["decision"] == "block"

    def test_log_is_bounded(self):
        organ = SafetyOrgan(log_size=2)
        for i in range(3):
            organ.check(f"action_{i}", permission_level=1, harm_probability=0.0, impact=0.0)
        assert len(organ.decisions) == 2
        assert organ.decisions[0]["action"] == "action_1"

    def test_process_takes_a_dict(self):
        out = SafetyOrgan().process({"action": "read_file", "permission_level": 1,
                                     "harm_probability": 0.0, "impact": 0.0})
        assert out.content["decision"] == "execute"
        with pytest.raises(ValueError):
            SafetyOrgan().process("not a dict")


# ---------------------------------------------------------------------------
# Phase 3 success criterion (Design_Doc §21):
# a full task passes through multiple Organs
# ---------------------------------------------------------------------------


class TestPhase3SuccessCriteria:
    def test_full_task_through_five_organs(self):
        language = LanguageOrgan()
        memory = MemoryOrgan()
        reasoning = ReasoningOrgan()
        learning = LearningOrgan()
        safety = SafetyOrgan()

        # Teach: Language → Memory
        taught = language.understand("Teach yourself what photosynthesis is.")
        assert taught.content["intent"] == "teach"
        memory.store(taught.content["text"])

        # Ask: Language → Memory → Reasoning → Language
        asked = language.understand("What is photosynthesis?")
        retrieved = memory.retrieve(asked.content["text"])
        reasoned = reasoning.reason(asked.content["text"], retrieved.content["results"])
        assert reasoned.content["supported"] is True
        answer = language.respond("explain", asked.content["text"],
                                  retrieved.content["results"])
        assert "photosynthesis" in answer.content["reply"].lower()

        # The chain confidence degrades through the stages (Eq 3.1)
        stages = [asked.confidence, retrieved.confidence,
                  reasoned.confidence, answer.confidence]
        chain = pipeline_confidence(stages)
        assert 0.0 < chain <= max(stages)

        # Safety gates an action before anything would execute
        gate = safety.check("send_email", permission_level=3)
        assert gate.content["decision"] == "require_approval"

        # Learning: one thumbs-up teaches every participating cell
        participants = language.cells + memory.cells + reasoning.cells
        result = learning.distribute({"success": True, "rating": 1.0}, participants)
        assert result.content["band"] == "high"
        for cell in participants:
            assert cell.health_check()["feedback_count"] == 1
