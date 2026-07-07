"""Phase 5 tests — the learning system.

Covers the feedback event record (Design_Doc §16.2), the persistent
learning log (JSONL, §15.2), the mistake tracker with similarity
clustering and error trend (Eq 6.5), and the end-to-end loop: repeated
failures become a "known weakness" stored in memory (§16.1).
"""

import json

import pytest

from incortex.core import CortexCore
from incortex.learning import (
    FeedbackEvent,
    LearningLog,
    MistakeTracker,
    SelfEvaluator,
    SkillBuilder,
    StrategyBank,
    new_feedback_event,
)
from incortex.organs import LearningOrgan


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


# ---------------------------------------------------------------------------
# FeedbackEvent (Design_Doc §16.2)
# ---------------------------------------------------------------------------


class TestFeedbackEvent:
    def test_factory_fills_the_event(self):
        clock = FakeClock()
        clock.now = 9.0
        event = new_feedback_event("task-1", success=True, rating=0.9,
                                   correction="simpler words",
                                   user_comment="good", clock=clock)
        assert event == FeedbackEvent("task-1", True, 0.9, "simpler words",
                                      "good", 9.0)

    def test_validation(self):
        with pytest.raises(ValueError):
            new_feedback_event("  ", success=True)
        with pytest.raises(ValueError):
            new_feedback_event("t", success="yes")
        with pytest.raises(ValueError):
            new_feedback_event("t", success=True, rating=1.5)


# ---------------------------------------------------------------------------
# LearningLog (the durable learning history)
# ---------------------------------------------------------------------------


class TestLearningLog:
    def test_records_and_stamps_entries(self):
        clock = FakeClock()
        clock.now = 5.0
        log = LearningLog(clock=clock)
        log.record({"band": "high", "learning_score": 0.8})
        assert len(log) == 1
        entry = log.recent(1)[0]
        assert entry["band"] == "high"
        assert entry["created_at"] == 5.0

    def test_recent_returns_oldest_first(self):
        log = LearningLog(clock=FakeClock())
        log.record({"n": 1})
        log.record({"n": 2})
        assert [entry["n"] for entry in log.recent()] == [1, 2]
        assert [entry["n"] for entry in log.recent(1)] == [2]

    def test_persists_as_jsonl(self, tmp_path):
        path = tmp_path / "learning_log.jsonl"
        log = LearningLog(path, clock=FakeClock())
        log.record({"band": "high"})
        log.record({"band": "low"})
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["band"] == "high"
        reopened = LearningLog(path, clock=FakeClock())
        assert len(reopened) == 2
        assert reopened.recent(1)[0]["band"] == "low"

    def test_validation(self):
        log = LearningLog(clock=FakeClock())
        with pytest.raises(ValueError):
            log.record("not a dict")
        with pytest.raises(ValueError):
            log.record({"bad": object()})  # not JSON-serializable


# ---------------------------------------------------------------------------
# MistakeTracker (Eq 6.5)
# ---------------------------------------------------------------------------


class TestMistakeTracker:
    def test_identical_failures_join_one_cluster(self):
        tracker = MistakeTracker()
        tracker.record(False, "What is dark matter?")
        cluster = tracker.record(False, "What is dark matter?")
        assert cluster.count == 2
        assert len(tracker.clusters) == 1

    def test_different_topics_form_separate_clusters(self):
        tracker = MistakeTracker()
        tracker.record(False, "What is dark matter?")
        tracker.record(False, "Convert my spreadsheet to a chart")
        assert len(tracker.clusters) == 2

    def test_successes_do_not_cluster(self):
        tracker = MistakeTracker()
        assert tracker.record(True) is None
        assert tracker.clusters == ()

    def test_repeat_rate(self):
        # Eq 6.5: cluster hits over total recorded tasks
        tracker = MistakeTracker()
        tracker.record(False, "What is dark matter?")
        cluster = tracker.record(False, "What is dark matter?")
        tracker.record(True)
        assert tracker.repeat_rate(cluster) == pytest.approx(2 / 3)

    def test_error_trend_detects_improvement(self):
        # Eq 6.5 delta-E: newer-half error rate minus older-half; negative = better
        tracker = MistakeTracker()
        for _ in range(4):
            tracker.record(False, "some failure")
        for _ in range(4):
            tracker.record(True)
        assert tracker.error_trend() == pytest.approx(-1.0)

    def test_error_trend_needs_data(self):
        assert MistakeTracker().error_trend() == 0.0

    def test_known_weaknesses_have_a_minimum_count(self):
        tracker = MistakeTracker()
        for _ in range(3):
            tracker.record(False, "What is dark matter?")
        tracker.record(False, "one-off failure about spreadsheets")
        weaknesses = tracker.known_weaknesses(min_count=3)
        assert len(weaknesses) == 1
        assert "dark matter" in weaknesses[0].representative

    def test_validation(self):
        tracker = MistakeTracker()
        with pytest.raises(ValueError):
            tracker.record("yes")
        with pytest.raises(ValueError):
            tracker.record(False, description=42)


# ---------------------------------------------------------------------------
# LearningOrgan (Phase 5 upgrade: log + tracker wired in)
# ---------------------------------------------------------------------------


class TestLearningOrganPhase5:
    def test_score_writes_the_learning_log(self):
        organ = LearningOrgan()
        organ.score({"success": True, "rating": 1.0}, description="a task")
        assert len(organ.log) == 1
        entry = organ.log.recent(1)[0]
        assert entry["band"] == "high"
        assert entry["description"] == "a task"

    def test_failures_reach_the_mistake_tracker(self):
        organ = LearningOrgan()
        organ.score({"success": False}, description="What is dark matter?")
        organ.score({"success": False}, description="What is dark matter?")
        assert len(organ.tracker.clusters) == 1
        assert organ.tracker.clusters[0].count == 2

    def test_distribute_still_teaches_and_now_also_logs(self):
        from incortex.cells import TextCell
        organ = LearningOrgan()
        pupil = TextCell()
        organ.distribute({"success": True, "rating": 1.0}, [pupil],
                         description="a task")
        assert pupil.health_check()["feedback_count"] == 1
        assert len(organ.log) == 1


# ---------------------------------------------------------------------------
# StrategyBank (Eq 6.3 value updates, Eq 6.4 UCB selection) — Phase 9
# ---------------------------------------------------------------------------


class TestStrategyBank:
    def test_add_validates(self):
        bank = StrategyBank()
        bank.add("simple", "plain-English answers")
        with pytest.raises(ValueError):
            bank.add("simple")  # duplicate
        with pytest.raises(ValueError):
            bank.add("   ")

    def test_untried_strategies_go_first_in_order(self):
        bank = StrategyBank()
        bank.add("a")
        bank.add("b")
        assert bank.select() == "a"
        bank.record("a", 1.0)
        assert bank.select() == "b"  # b has never been tried

    def test_value_update_is_exact(self):
        # Eq 6.3 with eta=0.1: Q starts 0; one 0.8 trial -> 0.08; another -> 0.152
        bank = StrategyBank()
        bank.add("s")
        bank.record("s", 0.8)
        assert bank.q_value("s") == pytest.approx(0.08)
        bank.record("s", 0.8)
        assert bank.q_value("s") == pytest.approx(0.152)

    def test_convergence_toward_the_true_reward(self):
        # §11 property 7: a stationary strategy's Q converges to its mean
        bank = StrategyBank()
        bank.add("s")
        for _ in range(200):
            bank.record("s", 0.6)
        assert bank.q_value("s") == pytest.approx(0.6, abs=1e-6)

    def test_ucb_prefers_the_higher_value_at_equal_trials(self):
        bank = StrategyBank()
        bank.add("good")
        bank.add("bad")
        for _ in range(5):
            bank.record("good", 0.9)
            bank.record("bad", 0.1)
        assert bank.select() == "good"

    def test_ucb_exploration_bonus_revisits_the_undertried(self):
        # Eq 6.4: a rarely-tried strategy accumulates bonus until it is retried
        bank = StrategyBank()
        bank.add("favorite")
        bank.add("neglected")
        bank.record("neglected", 0.5)
        for _ in range(200):
            bank.record("favorite", 0.55)
        assert bank.select() == "neglected"

    def test_experiments_are_tracked(self):
        bank = StrategyBank()
        bank.add("s")
        bank.record("s", 0.7)
        bank.record("s", 0.3)
        assert [trial["score"] for trial in bank.experiments] == [0.7, 0.3]
        assert all(trial["strategy"] == "s" for trial in bank.experiments)

    def test_compare_ranks_by_value(self):
        bank = StrategyBank()
        bank.add("weak")
        bank.add("strong")
        for _ in range(10):
            bank.record("strong", 0.9)
            bank.record("weak", 0.2)
        table = bank.compare()
        assert table[0]["strategy"] == "strong"
        assert table[0]["q_value"] > table[1]["q_value"]
        assert table[0]["trials"] == 10

    def test_guards(self):
        bank = StrategyBank()
        with pytest.raises(ValueError):
            bank.select()  # empty bank
        bank.add("s")
        with pytest.raises(ValueError):
            bank.record("missing", 0.5)
        with pytest.raises(ValueError):
            bank.record("s", 1.5)
        with pytest.raises(ValueError):
            bank.q_value("missing")


# ---------------------------------------------------------------------------
# SelfEvaluator (Eq 6.7 calibration) — Phase 9
# ---------------------------------------------------------------------------


class TestSelfEvaluator:
    def test_perfect_predictions_have_zero_brier(self):
        evaluator = SelfEvaluator()
        evaluator.record(1.0, True)
        evaluator.record(0.0, False)
        assert evaluator.brier() == pytest.approx(0.0)
        assert evaluator.ece() == pytest.approx(0.0)

    def test_always_wrong_is_brier_one(self):
        evaluator = SelfEvaluator()
        evaluator.record(1.0, False)
        assert evaluator.brier() == pytest.approx(1.0)

    def test_always_half_is_the_quarter_baseline(self):
        # math_model.md §6.6: Brier 0.25 is the "always say 0.5" baseline
        evaluator = SelfEvaluator()
        evaluator.record(0.5, True)
        evaluator.record(0.5, False)
        assert evaluator.brier() == pytest.approx(0.25)

    def test_ece_detects_overconfidence(self):
        # Claims 90% but is right half the time -> ECE = |0.5 - 0.9| = 0.4
        evaluator = SelfEvaluator()
        evaluator.record(0.9, True)
        evaluator.record(0.9, False)
        assert evaluator.ece() == pytest.approx(0.4)

    def test_report_shape(self):
        evaluator = SelfEvaluator()
        evaluator.record(0.8, True)
        report = evaluator.report()
        assert report["samples"] == 1
        assert 0.0 <= report["brier"] <= 1.0
        assert 0.0 <= report["ece"] <= 1.0
        assert report["baseline_brier"] == 0.25
        assert isinstance(report["beats_baseline"], bool)

    def test_no_data_is_honest(self):
        evaluator = SelfEvaluator()
        assert evaluator.brier() is None
        assert evaluator.ece() is None
        assert evaluator.report()["samples"] == 0

    def test_validation(self):
        evaluator = SelfEvaluator()
        with pytest.raises(ValueError):
            evaluator.record(1.5, True)
        with pytest.raises(ValueError):
            evaluator.record(0.5, "yes")


# ---------------------------------------------------------------------------
# SkillBuilder (Eq 6.6 promotion) — Phase 9
# ---------------------------------------------------------------------------


class TestSkillBuilder:
    def test_similar_tasks_share_a_cluster(self):
        builder = SkillBuilder()
        builder.record(True, "explain photosynthesis simply")
        cluster = builder.record(True, "explain photosynthesis simply")
        assert cluster.trials == 2
        assert cluster.successes == 2
        assert len(builder.clusters) == 1

    def test_different_topics_form_separate_clusters(self):
        builder = SkillBuilder()
        builder.record(True, "explain photosynthesis")
        builder.record(True, "draft a pull request")
        assert len(builder.clusters) == 2

    def test_smoothed_success_uses_the_rule_of_succession(self):
        # Eq 6.6 uses (k+1)/(n+2), the same honesty rule as cell confidence
        builder = SkillBuilder()
        cluster = builder.record(True, "some task")
        assert cluster.smoothed_success == pytest.approx(2 / 3)

    def test_promotion_needs_volume_and_quality(self):
        # Eq 6.6: n >= 5 and (k+1)/(n+2) >= 0.8
        builder = SkillBuilder()
        for _ in range(4):
            builder.record(True, "explain photosynthesis")
        assert builder.promoted() == ()  # only 4 trials: not enough evidence
        builder.record(True, "explain photosynthesis")
        promoted = builder.promoted()  # 5/5 -> smoothed 6/7 = 0.857
        assert len(promoted) == 1
        assert promoted[0].smoothed_success == pytest.approx(6 / 7)

    def test_failures_block_promotion(self):
        builder = SkillBuilder()
        for _ in range(3):
            builder.record(True, "flaky task")
        for _ in range(2):
            builder.record(False, "flaky task")
        # 5 trials but smoothed = 4/7 = 0.571 < 0.8
        assert builder.promoted() == ()

    def test_validation(self):
        builder = SkillBuilder()
        with pytest.raises(ValueError):
            builder.record("yes", "task")
        with pytest.raises(ValueError):
            builder.record(True, "   ")


# ---------------------------------------------------------------------------
# LearningOrgan Phase 9 wiring
# ---------------------------------------------------------------------------


class TestLearningOrganPhase9:
    def test_descriptions_feed_the_skill_builder(self):
        organ = LearningOrgan()
        organ.score({"success": True}, description="explain photosynthesis")
        organ.score({"success": True}, description="explain photosynthesis")
        assert len(organ.skills.clusters) == 1
        assert organ.skills.clusters[0].successes == 2

    def test_record_confidence_feeds_the_evaluator(self):
        organ = LearningOrgan()
        organ.record_confidence(0.8, True)
        assert organ.evaluator.report()["samples"] == 1

    def test_the_organ_carries_a_strategy_bank(self):
        organ = LearningOrgan()
        organ.strategies.add("simple")
        organ.strategies.record("simple", 0.9)
        assert organ.strategies.compare()[0]["strategy"] == "simple"


# ---------------------------------------------------------------------------
# The full loop: repeated failures become remembered weaknesses (§16.1, §16.4)
# ---------------------------------------------------------------------------


class TestWeaknessEscalation:
    def test_three_failures_store_a_known_weakness(self):
        core = CortexCore()
        for _ in range(3):
            core.handle("What is dark matter?")
            core.feedback(success=False)
        stored = [record.content
                  for record in core.memory.manager.long_term.all_records()]
        weaknesses = [content for content in stored if "Known weakness" in content]
        assert len(weaknesses) == 1
        assert "dark matter" in weaknesses[0]
        assert "error_event" in [m.message_type for m in core.bus.history()]

    def test_escalation_happens_only_once_per_cluster(self):
        core = CortexCore()
        for _ in range(5):
            core.handle("What is dark matter?")
            core.feedback(success=False)
        stored = [record.content
                  for record in core.memory.manager.long_term.all_records()]
        assert sum("Known weakness" in content for content in stored) == 1


# ---------------------------------------------------------------------------
# Phase 9 success criterion (Design_Doc §21): the system can test multiple
# strategies, compare performance, and improve future behavior.
# ---------------------------------------------------------------------------


class TestPhase9SuccessCriteria:
    def test_strategies_are_tested_compared_and_the_best_wins(self):
        # Three explanation styles with deterministic reward rates.
        rewards = {"simple": 0.9, "formal": 0.5, "jargon": 0.1}
        bank = StrategyBank()
        for name in rewards:
            bank.add(name)
        for _ in range(60):
            choice = bank.select()          # test multiple strategies (Eq 6.4)
            bank.record(choice, rewards[choice])  # learn from each (Eq 6.3)
        table = bank.compare()              # compare performance
        assert table[0]["strategy"] == "simple"
        assert table[0]["q_value"] > table[1]["q_value"] > table[2]["q_value"]
        # Improved future behavior: the winner got the most trials
        trials = {row["strategy"]: row["trials"] for row in table}
        assert trials["simple"] > trials["formal"]
        assert trials["simple"] > trials["jargon"]
        assert len(bank.experiments) == 60  # every trial tracked

    def test_repeated_success_becomes_a_remembered_skill(self):
        # The mirror image of weakness escalation: reliably good behavior
        # is promoted (Eq 6.6) and stored into memory once.
        core = CortexCore()
        core.handle("Teach yourself what photosynthesis is.")
        core.feedback(success=True, rating=1.0)
        for _ in range(5):
            core.handle("What is photosynthesis?")
            core.feedback(success=True, rating=1.0)
        stored = [record.content
                  for record in core.memory.manager.long_term.all_records()]
        skills = [content for content in stored if "Learned skill" in content]
        assert len(skills) == 1
        assert "photosynthesis" in skills[0].lower()
        # And only once, however often it keeps succeeding
        core.handle("What is photosynthesis?")
        core.feedback(success=True, rating=1.0)
        stored = [record.content
                  for record in core.memory.manager.long_term.all_records()]
        assert sum("Learned skill" in content for content in stored) == 1

    def test_the_brain_calibrates_its_own_confidence(self):
        # Every feedback pairs the chain confidence with the real outcome
        core = CortexCore()
        core.handle("Teach yourself what photosynthesis is.")
        core.feedback(success=True)
        core.handle("What is photosynthesis?")
        core.feedback(success=True)
        report = core.learning.evaluator.report()
        assert report["samples"] == 2
        assert report["brier"] is not None
