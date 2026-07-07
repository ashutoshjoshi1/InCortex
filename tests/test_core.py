"""Phase 4 tests — the Cortex Core.

Pins math_model.md §4 to exact numbers: routing threshold and fallback
(Eq 4.2), starvation-free scheduling priority (Eq 4.3, uncapped age),
and answer acceptance (Eq 4.4). Ends with the Phase 4 success criterion
from Design_Doc §21: the Cortex routes a user request through the right
Organs and generates a response.
"""

import dataclasses

import pytest

from incortex.core import (
    CortexCore,
    CortexMessage,
    MessageBus,
    Router,
    Scheduler,
    SystemState,
    TaskContext,
    new_message,
)
from incortex.core.cortex import TAU_ANSWER
from incortex.core.router import TAU_ROUTE
from incortex.organs import LanguageOrgan, MemoryOrgan, ReasoningOrgan, SafetyOrgan


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


# ---------------------------------------------------------------------------
# CortexMessage (Design_Doc §14)
# ---------------------------------------------------------------------------


class TestCortexMessage:
    def test_factory_fills_the_envelope(self):
        clock = FakeClock()
        clock.now = 42.0
        message = new_message("user", "cortex", "user_input", "hello", clock=clock)
        assert len(message.message_id) == 32  # uuid4 hex
        assert message.session_id == "default"
        assert message.priority == "normal"
        assert message.created_at == 42.0
        assert message.payload == "hello"

    def test_rejects_unknown_message_type(self):
        with pytest.raises(ValueError):
            new_message("user", "cortex", "telepathy", "hello")

    def test_rejects_bad_priority_and_confidence(self):
        with pytest.raises(ValueError):
            new_message("user", "cortex", "user_input", "x", priority="urgent")
        with pytest.raises(ValueError):
            new_message("user", "cortex", "user_input", "x", confidence=1.5)

    def test_rejects_empty_routing_fields(self):
        with pytest.raises(ValueError):
            new_message("", "cortex", "user_input", "x")
        with pytest.raises(ValueError):
            new_message("user", "  ", "user_input", "x")

    def test_messages_are_immutable(self):
        message = new_message("user", "cortex", "user_input", "x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            message.payload = "changed"


# ---------------------------------------------------------------------------
# MessageBus (Design_Doc §14 + §17 brain activity log)
# ---------------------------------------------------------------------------


class TestMessageBus:
    def test_publish_delivers_to_subscribers(self):
        bus = MessageBus()
        seen = []
        bus.subscribe("user_input", seen.append)
        message = new_message("user", "cortex", "user_input", "hello")
        delivered = bus.publish(message)
        assert delivered == 1
        assert seen == [message]

    def test_publish_only_reaches_matching_type(self):
        bus = MessageBus()
        seen = []
        bus.subscribe("memory_result", seen.append)
        bus.publish(new_message("user", "cortex", "user_input", "x"))
        assert seen == []

    def test_every_message_lands_in_history(self):
        bus = MessageBus()
        bus.publish(new_message("user", "cortex", "user_input", "one"))
        bus.publish(new_message("cortex", "user", "system_event", "two"))
        assert [m.payload for m in bus.history()] == ["one", "two"]
        assert [m.payload for m in bus.history(1)] == ["two"]

    def test_history_is_bounded(self):
        bus = MessageBus(history_size=2)
        for i in range(3):
            bus.publish(new_message("user", "cortex", "user_input", i))
        assert [m.payload for m in bus.history()] == [1, 2]

    def test_subscribe_validates(self):
        bus = MessageBus()
        with pytest.raises(ValueError):
            bus.subscribe("telepathy", print)
        with pytest.raises(ValueError):
            bus.subscribe("user_input", "not callable")

    def test_publish_rejects_non_messages(self):
        with pytest.raises(ValueError):
            MessageBus().publish("just a string")


# ---------------------------------------------------------------------------
# Router (Eq 4.2)
# ---------------------------------------------------------------------------


class TestRouter:
    def make_router(self):
        router = Router()
        self.language = LanguageOrgan()
        self.memory = MemoryOrgan()
        self.reasoning = ReasoningOrgan()
        router.register(self.language, intents=("teach", "remember", "explain", "chat"))
        router.register(self.memory, intents=("teach", "remember", "explain"))
        router.register(self.reasoning, intents=("explain",))
        return router

    def test_intent_affinity_selects_the_serving_organs(self):
        decision = self.make_router().route("What is photosynthesis?", intent="explain")
        names = {organ.name for organ in decision.selected}
        assert names == {"language_organ", "memory_organ", "reasoning_organ"}
        assert decision.fallback_used is False

    def test_chat_reaches_only_the_language_organ(self):
        decision = self.make_router().route("hello there", intent="chat")
        assert {organ.name for organ in decision.selected} == {"language_organ"}

    def test_keyword_relevance_alone_can_route(self):
        # "remember" is a memory capability keyword: 1 / min(2, K) >= tau
        decision = self.make_router().route("remember this", intent=None)
        assert self.memory.name in {organ.name for organ in decision.selected}

    def test_fallback_picks_the_best_organ_when_nothing_passes(self):
        decision = self.make_router().route("zzz qqq vvv", intent=None)
        assert len(decision.selected) == 1
        assert decision.fallback_used is True
        assert max(decision.scores.values()) < TAU_ROUTE

    def test_scores_are_exposed_for_logging(self):
        decision = self.make_router().route("hello", intent="chat")
        assert set(decision.scores) == {"language_organ", "memory_organ", "reasoning_organ"}
        assert all(0.0 <= score <= 1.0 for score in decision.scores.values())

    def test_register_validates(self):
        router = Router()
        with pytest.raises(ValueError):
            router.register("not an organ")
        router.register(LanguageOrgan())
        with pytest.raises(ValueError):
            router.register(LanguageOrgan())  # duplicate name

    def test_empty_router_cannot_route(self):
        with pytest.raises(ValueError):
            Router().route("anything")


# ---------------------------------------------------------------------------
# Scheduler (Eq 4.3 — uncapped age term)
# ---------------------------------------------------------------------------


class TestScheduler:
    def test_priority_formula_exact(self):
        # Eq 4.3: 0.5*0.4 + 0.3*0.6 + 0.2*(30/60) = 0.2 + 0.18 + 0.1 = 0.48
        clock = FakeClock()
        scheduler = Scheduler(age_max_seconds=60.0, clock=clock)
        task = scheduler.submit("job", urgency=0.4, importance=0.6)
        clock.now = 30.0
        assert scheduler.priority(task) == pytest.approx(0.48)

    def test_pops_highest_priority_first(self):
        clock = FakeClock()
        scheduler = Scheduler(clock=clock)
        scheduler.submit("low", urgency=0.2, importance=0.5)
        scheduler.submit("high", urgency=1.0, importance=0.5)
        assert scheduler.pop().payload == "high"
        assert scheduler.pop().payload == "low"

    def test_no_task_starves(self):
        # §11 property 8: age eventually beats any fixed urgency.
        # P_low(150s) = 0.25 + 0.2*150/60 = 0.75 > P_high(fresh) = 0.65
        clock = FakeClock()
        scheduler = Scheduler(age_max_seconds=60.0, clock=clock)
        scheduler.submit("ancient-low", urgency=0.2, importance=0.5)
        clock.now = 150.0
        scheduler.submit("fresh-high", urgency=1.0, importance=0.5)
        assert scheduler.pop().payload == "ancient-low"

    def test_ties_go_to_the_older_task(self):
        scheduler = Scheduler(clock=FakeClock())
        scheduler.submit("first", urgency=0.5, importance=0.5)
        scheduler.submit("second", urgency=0.5, importance=0.5)
        assert scheduler.pop().payload == "first"

    def test_urgency_accepts_priority_names(self):
        scheduler = Scheduler(clock=FakeClock())
        task = scheduler.submit("job", urgency="high")
        assert task.urgency == pytest.approx(1.0)

    def test_len_tracks_the_queue(self):
        scheduler = Scheduler(clock=FakeClock())
        assert len(scheduler) == 0
        scheduler.submit("job")
        assert len(scheduler) == 1

    def test_validation(self):
        scheduler = Scheduler(clock=FakeClock())
        with pytest.raises(ValueError):
            scheduler.submit("job", urgency=1.5)
        with pytest.raises(ValueError):
            scheduler.submit("job", urgency="asap")
        with pytest.raises(ValueError):
            scheduler.submit("job", importance=-0.1)
        with pytest.raises(ValueError):
            scheduler.pop()  # empty
        with pytest.raises(ValueError):
            Scheduler(age_max_seconds=0)


# ---------------------------------------------------------------------------
# TaskContext and SystemState
# ---------------------------------------------------------------------------


class TestTaskContext:
    def test_stages_accumulate_into_chain_confidence(self):
        context = TaskContext(task_id="t1", session_id="s", raw_text="hi")
        context.add_stage("understand", 0.9)
        context.add_stage("retrieve", 0.9)
        context.add_stage("respond", 0.2)
        # Eq 3.1 worked example: geometric mean = 0.545
        assert context.chain() == pytest.approx(0.545, abs=1e-3)

    def test_empty_context_has_zero_chain(self):
        assert TaskContext(task_id="t", session_id="s", raw_text="x").chain() == 0.0

    def test_stage_confidences_are_clipped(self):
        context = TaskContext(task_id="t", session_id="s", raw_text="x")
        context.add_stage("weird", 1.7)
        assert context.stages == [("weird", 1.0)]

    def test_organs_used_deduplicates(self):
        context = TaskContext(task_id="t", session_id="s", raw_text="x")
        context.use_organ("memory_organ")
        context.use_organ("memory_organ")
        assert context.organs_used == ["memory_organ"]


class TestSystemState:
    def make_context(self, session="s", accepted=True, chain=0.8):
        context = TaskContext(task_id="t", session_id=session, raw_text="x")
        context.chain_confidence = chain
        context.accepted = accepted
        return context

    def test_records_tasks_and_smooths_confidence(self):
        state = SystemState()
        state.record_task(self.make_context(chain=0.8))
        state.record_task(self.make_context(chain=0.4, accepted=False))
        snapshot = state.snapshot()
        assert snapshot["tasks_handled"] == 2
        assert snapshot["acceptance_rate"] == pytest.approx(0.5)
        # Eq 1.7: first sample seeds, then 0.9*0.8 + 0.1*0.4 = 0.76
        assert snapshot["confidence_ema"] == pytest.approx(0.76)

    def test_learning_ema(self):
        state = SystemState()
        state.record_learning(0.8)
        state.record_learning(0.3)
        assert state.snapshot()["learning_ema"] == pytest.approx(0.75)

    def test_remembers_the_last_context_per_session(self):
        state = SystemState()
        first = self.make_context(session="a")
        second = self.make_context(session="a")
        other = self.make_context(session="b")
        for context in (first, second, other):
            state.record_task(context)
        assert state.last_context("a") is second
        assert state.last_context("b") is other
        assert state.last_context("missing") is None

    def test_fresh_snapshot(self):
        snapshot = SystemState().snapshot()
        assert snapshot["tasks_handled"] == 0
        assert snapshot["confidence_ema"] is None
        assert snapshot["learning_ema"] is None


# ---------------------------------------------------------------------------
# CortexCore (Eq 4.1 composition, Eq 4.2 routing, Eq 4.4 acceptance)
# ---------------------------------------------------------------------------


class TestCortexCore:
    def test_teach_flows_through_language_and_memory(self):
        core = CortexCore()
        context = core.handle("Teach yourself what photosynthesis is.")
        assert context.intent == "teach"
        assert context.reply.startswith("I have learned")
        assert context.accepted is True
        assert "language_organ" in context.organs_used
        assert "memory_organ" in context.organs_used

    def test_explain_uses_memory_and_reasoning(self):
        core = CortexCore()
        core.handle("Teach yourself what photosynthesis is.")
        context = core.handle("What is photosynthesis?")
        assert "From memory" in context.reply
        assert context.accepted is True
        assert "reasoning_organ" in context.organs_used
        stage_names = [name for name, _ in context.stages]
        assert stage_names == ["understand", "retrieve", "reason", "respond"]

    def test_unknown_topic_fails_the_acceptance_gate(self):
        # Eq 4.4: empty retrieval zeroes the chain -> clarification, not an answer
        core = CortexCore()
        context = core.handle("What is dark matter?")
        assert context.accepted is False
        assert context.chain_confidence < TAU_ANSWER
        assert "not confident" in context.reply
        assert "0.00" in context.reply

    def test_unsupported_reasoning_discards_misleading_evidence(self):
        # Spurious word-overlap match must not become an answer
        core = CortexCore()
        core.handle("Teach yourself what photosynthesis is.")
        context = core.handle("What is dark matter?")
        assert context.memory_results == []
        assert context.accepted is False

    def test_chat_is_routed_to_language_only(self):
        context = CortexCore().handle("hello there")
        assert context.organs_used == ["language_organ"]
        assert context.accepted is True

    def test_safety_gate_can_stop_a_store(self):
        core = CortexCore(safety=SafetyOrgan(blocked_actions=frozenset({"store_memory"})))
        context = core.handle("Teach yourself what photosynthesis is.")
        assert "safety gate" in context.reply.lower()
        memory_cells = core.memory.cells
        assert all(cell.health_check()["processed"] == 0 for cell in memory_cells)

    def test_feedback_teaches_the_organs_that_took_part(self):
        core = CortexCore()
        core.handle("Teach yourself what photosynthesis is.")
        result = core.feedback(success=True, rating=1.0)
        assert result.content["band"] == "high"
        for cell in core.language.cells + core.memory.cells:
            assert cell.health_check()["feedback_count"] == 1
        # Reasoning did not take part in a teach flow — no feedback for it
        for cell in core.reasoning.cells:
            assert cell.health_check()["feedback_count"] == 0
        assert core.state.snapshot()["learning_ema"] == pytest.approx(0.8)

    def test_feedback_without_a_task_is_an_error(self):
        with pytest.raises(ValueError):
            CortexCore().feedback(success=True)

    def test_brain_activity_lands_on_the_bus(self):
        core = CortexCore()
        core.handle("Teach yourself what photosynthesis is.")
        core.feedback(success=True)
        types = [message.message_type for message in core.bus.history()]
        assert types[0] == "user_input"
        assert "safety_check" in types
        assert "memory_result" in types
        assert "system_event" in types
        assert "feedback_event" in types
        assert "learning_update" in types

    def test_final_message_carries_the_chain_confidence(self):
        core = CortexCore()
        context = core.handle("hello there")
        final = [m for m in core.bus.history() if m.message_type == "system_event"][-1]
        assert final.confidence == pytest.approx(context.chain_confidence)

    def test_sessions_are_tracked_separately(self):
        core = CortexCore()
        core.handle("Teach yourself what photosynthesis is.", session_id="alice")
        core.handle("hello there", session_id="bob")
        assert core.state.last_context("alice").intent == "teach"
        assert core.state.last_context("bob").intent == "chat"

    def test_health_check_covers_organs_and_system(self):
        core = CortexCore()
        core.handle("hello there")
        report = core.health_check()
        names = {organ["name"] for organ in report["organs"]}
        assert {"language_organ", "memory_organ", "reasoning_organ",
                "learning_organ", "safety_organ"} <= names
        assert report["system"]["tasks_handled"] == 1


# ---------------------------------------------------------------------------
# Phase 4 success criterion (Design_Doc §21): the Cortex Core routes a user
# request through the right Organs and generates a response.
# ---------------------------------------------------------------------------


class TestPhase4SuccessCriteria:
    def test_the_mvp_demo_conversation(self):
        core = CortexCore()

        taught = core.handle("Teach yourself what photosynthesis is.")
        assert taught.accepted is True

        remembered = core.handle("Remember that I like very simple explanations.")
        assert remembered.intent == "remember"
        assert remembered.accepted is True

        answer = core.handle("What is photosynthesis?")
        assert answer.accepted is True
        assert "photosynthesis" in answer.reply.lower()
        assert set(answer.organs_used) == {"language_organ", "memory_organ",
                                           "reasoning_organ"}

        feedback = core.feedback(success=True, rating=1.0)
        assert feedback.content["band"] == "high"
