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
