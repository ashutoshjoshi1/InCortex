"""The message system — CortexMessage envelope and MessageBus (Design_Doc §14).

Every part of InCortex communicates through the same immutable envelope,
and every published message lands in the bus's bounded history — which is
the brain activity log of Design_Doc §17.
"""

import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any

# Design_Doc §14.2 — the complete message vocabulary.
MESSAGE_TYPES = frozenset({
    "user_input", "system_event",
    "memory_query", "memory_result",
    "reasoning_request", "reasoning_result",
    "plan_request", "plan_result",
    "tool_request", "tool_result",
    "safety_check", "feedback_event", "learning_update",
    "error_event", "health_check",
})
PRIORITIES = ("low", "normal", "high")
DEFAULT_HISTORY_SIZE = 200


@dataclass(frozen=True)
class CortexMessage:
    """The standard envelope (Design_Doc §14.1). Immutable once created."""

    message_id: str
    session_id: str
    source: str
    target: str
    message_type: str
    payload: Any
    priority: str = "normal"
    confidence: float | None = None
    memory_refs: tuple = ()
    permissions: tuple = ()
    created_at: float = 0.0

    def __post_init__(self):
        for name in ("message_id", "session_id", "source", "target"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"CortexMessage.{name} must be a non-empty string")
        if self.message_type not in MESSAGE_TYPES:
            raise ValueError(f"unknown message_type '{self.message_type}'")
        if self.priority not in PRIORITIES:
            raise ValueError(f"priority must be one of {PRIORITIES}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")


def new_message(source, target, message_type, payload, session_id="default",
                priority="normal", confidence=None, clock=time.time):
    """Build a validated CortexMessage with a fresh id and timestamp."""
    return CortexMessage(
        message_id=uuid.uuid4().hex,
        session_id=session_id,
        source=source,
        target=target,
        message_type=message_type,
        payload=payload,
        priority=priority,
        confidence=confidence,
        created_at=clock(),
    )


class MessageBus:
    """Synchronous publish/subscribe with a bounded activity history."""

    def __init__(self, history_size=DEFAULT_HISTORY_SIZE):
        self._subscribers = {}
        self._history = deque(maxlen=history_size)

    def subscribe(self, message_type, handler):
        """Register a handler for one message type."""
        if message_type not in MESSAGE_TYPES:
            raise ValueError(f"unknown message_type '{message_type}'")
        if not callable(handler):
            raise ValueError("handler must be callable")
        self._subscribers.setdefault(message_type, []).append(handler)

    def publish(self, message):
        """Record the message in history and deliver it. Returns handler count."""
        if not isinstance(message, CortexMessage):
            raise ValueError("only CortexMessage instances can be published")
        self._history.append(message)
        handlers = self._subscribers.get(message.message_type, [])
        for handler in handlers:
            handler(message)
        return len(handlers)

    def history(self, count=None):
        """The most recent messages, oldest first."""
        messages = tuple(self._history)
        return messages if count is None else messages[-count:]
