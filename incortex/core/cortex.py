"""CortexCore — the central coordinator (Design_Doc §13).

It does no task itself: it understands via the Language Organ, routes via
the Router (Eq 4.2), consults Memory and Reasoning, gates writes through
the Safety Organ, applies the answer-acceptance rule (Eq 4.4), publishes
every step to the MessageBus, and sends feedback to the Learning Organ.
"""

import time

from incortex.core.message import MessageBus, new_message
from incortex.core.router import Router
from incortex.core.scheduler import URGENCY_BY_PRIORITY, Scheduler
from incortex.core.state import SystemState, TaskContext
from incortex.organs import (
    LanguageOrgan,
    LearningOrgan,
    MemoryOrgan,
    ReasoningOrgan,
    SafetyOrgan,
)

TAU_ANSWER = 0.4  # Eq 4.4 answer-acceptance floor
CLARIFICATION_TEMPLATE = (
    "I'm not confident enough to answer that (chain confidence {chain:.2f}). "
    "Could you rephrase, or teach me more about it first?"
)
# Storing a memory is a local write: level 2, low estimated risk (Eq 7.1 inputs).
STORE_ACTION = {"action": "store_memory", "permission_level": 2,
                "harm_probability": 0.05, "impact": 0.1}


class CortexCore:
    def __init__(self, language=None, memory=None, reasoning=None,
                 learning=None, safety=None, tools=None, clock=time.time):
        self.language = language or LanguageOrgan()
        self.memory = memory or MemoryOrgan()
        self.reasoning = reasoning or ReasoningOrgan()
        self.learning = learning or LearningOrgan()
        self.safety = safety or SafetyOrgan()
        self.tools = tools  # optional ToolOrgan; the muscle system (Phase 7)
        self.bus = MessageBus()
        self.state = SystemState()
        self._clock = clock
        self._scheduler = Scheduler(clock=clock)
        self._escalated_clusters = set()
        self._router = Router()
        self._router.register(self.language,
                              intents=("teach", "remember", "explain", "chat"))
        self._router.register(self.memory, intents=("teach", "remember", "explain"))
        self._router.register(self.reasoning, intents=("explain",))

    # -- the cognitive loop (Eq 4.1) ------------------------------------------

    def handle(self, text, session_id="default"):
        """Route one user request through the right Organs and answer it."""
        inbound = self._publish("user", "cortex", "user_input", text, session_id)
        # Single-task flow today; the queue is the seam for future multi-tasking.
        self._scheduler.submit(inbound, urgency=URGENCY_BY_PRIORITY[inbound.priority])
        current = self._scheduler.pop().payload
        context = TaskContext(task_id=current.message_id,
                              session_id=session_id, raw_text=text)

        # Understand (Language Organ)
        understanding = self.language.understand(text)
        context.cleaned_text = understanding.content["text"]
        context.intent = understanding.content["intent"]
        context.add_stage("understand", understanding.confidence)
        context.use_organ(self.language.name)

        # Select relevant Organs (Router, Eq 4.2)
        routed = {organ.name for organ in
                  self._router.route(context.cleaned_text, context.intent).selected}

        reply_override = self._consult_memory(context, routed, session_id)
        self._consult_reasoning(context, routed, session_id)

        # Respond (Language Organ), unless the safety gate already spoke
        if reply_override is not None:
            context.reply = reply_override
        else:
            response = self.language.respond(context.intent, context.cleaned_text,
                                             context.memory_results)
            context.add_stage("respond", response.confidence)
            context.reply = response.content["reply"]

        # Accept or ask for clarification (Eq 4.4)
        context.chain_confidence = context.chain()
        context.accepted = context.chain_confidence >= TAU_ANSWER
        if not context.accepted:
            context.reply = CLARIFICATION_TEMPLATE.format(
                chain=context.chain_confidence)

        self._publish("cortex", "user", "system_event", context.reply,
                      session_id, confidence=context.chain_confidence)
        self.state.record_task(context)
        return context

    def _consult_memory(self, context, routed, session_id):
        """Store or retrieve via the Memory Organ. Returns a reply override
        when the safety gate refuses a store."""
        if self.memory.name not in routed:
            return None
        if context.intent in ("teach", "remember"):
            gate = self.safety.check(**STORE_ACTION)
            self._publish("cortex", "safety_organ", "safety_check",
                          gate.content, session_id)
            if gate.content["decision"] != "execute":
                context.use_organ(self.safety.name)
                context.add_stage("safety_gate", 1.0)  # a confident refusal
                return (f"The safety gate said '{gate.content['decision']}' "
                        f"for storing memories, so I did not store that.")
            stored = self.memory.store(context.cleaned_text)
            context.add_stage("store", stored.confidence)
            context.use_organ(self.memory.name)
            self._publish("memory_organ", "cortex", "memory_result",
                          stored.content, session_id, confidence=stored.confidence)
        elif context.intent == "explain":
            retrieved = self.memory.retrieve(context.cleaned_text)
            context.memory_results = retrieved.content["results"]
            context.add_stage("retrieve", retrieved.confidence)
            context.use_organ(self.memory.name)
            self._publish("memory_organ", "cortex", "memory_result",
                          retrieved.content, session_id,
                          confidence=retrieved.confidence)
        return None

    def _consult_reasoning(self, context, routed, session_id):
        """Think over the retrieved evidence; discard it if it cannot support
        an answer — a weak word-overlap match must not become a reply."""
        if self.reasoning.name not in routed or context.intent != "explain":
            return
        reasoned = self.reasoning.reason(context.cleaned_text,
                                         context.memory_results)
        context.add_stage("reason", reasoned.confidence)
        context.use_organ(self.reasoning.name)
        self._publish("reasoning_organ", "cortex", "reasoning_result",
                      reasoned.content, session_id, confidence=reasoned.confidence)
        if not reasoned.content["supported"]:
            context.memory_results = []

    # -- learning (Design_Doc §13.1 step 10) -----------------------------------

    def feedback(self, success, rating=None, session_id="default"):
        """Grade the session's last task and teach every organ that took part."""
        context = self.state.last_context(session_id)
        if context is None:
            raise ValueError(f"no task to rate in session '{session_id}'")
        organs = {organ.name: organ for organ in
                  (self.language, self.memory, self.reasoning)}
        participants = [cell
                        for name in context.organs_used if name in organs
                        for cell in organs[name].cells]
        message = {"success": success}
        if rating is not None:
            message["rating"] = rating
        result = self.learning.distribute(message, participants,
                                          description=context.cleaned_text)
        self.state.record_learning(result.content["learning_score"])
        self._publish("user", "learning_organ", "feedback_event",
                      message, session_id)
        self._publish("learning_organ", "cortex", "learning_update",
                      result.content, session_id)
        self._escalate_weaknesses(session_id)
        return result

    def _escalate_weaknesses(self, session_id):
        """§16.4 — a mistake that keeps recurring becomes a remembered fact,
        stored once per cluster with maximum importance."""
        for cluster in self.learning.tracker.known_weaknesses():
            if cluster.cluster_id in self._escalated_clusters:
                continue
            self._escalated_clusters.add(cluster.cluster_id)
            warning = (f"Known weakness: I keep failing at "
                       f"'{cluster.representative}' ({cluster.count} times so far).")
            self.memory.store(warning, importance=1.0)
            self._publish("learning_organ", "memory_organ", "error_event",
                          warning, session_id)

    # -- introspection ----------------------------------------------------------

    def health_check(self):
        organs = [self.language, self.memory, self.reasoning,
                  self.learning, self.safety]
        if self.tools is not None:
            organs.append(self.tools)
        return {
            "organs": [organ.health_check() for organ in organs],
            "system": self.state.snapshot(),
        }

    def _publish(self, source, target, message_type, payload,
                 session_id, confidence=None):
        message = new_message(source, target, message_type, payload,
                              session_id=session_id, confidence=confidence,
                              clock=self._clock)
        self.bus.publish(message)
        return message
