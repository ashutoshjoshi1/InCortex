"""Router — selects which Organs handle a message (Eq 4.2).

An organ's relevance is the stronger of two signals: its keyword relevance
to the message text (Eq 3.2) and its declared intent affinity (1.0 when it
serves the detected intent). Organs at or above the threshold are selected;
if none pass, the single best organ handles it — something must always
answer.
"""

from dataclasses import dataclass, field

from incortex.organs.base_organ import BaseOrgan

TAU_ROUTE = 0.35  # Eq 4.2 routing threshold


@dataclass(frozen=True)
class RoutingDecision:
    selected: tuple
    scores: dict = field(hash=False)
    fallback_used: bool = False


class Router:
    def __init__(self, threshold=TAU_ROUTE):
        self._threshold = threshold
        self._routes = []  # (organ, frozenset of served intents)

    def register(self, organ, intents=()):
        """Add an organ and declare which intents it serves."""
        if not isinstance(organ, BaseOrgan):
            raise ValueError("only BaseOrgan instances can be registered")
        if any(existing.name == organ.name for existing, _ in self._routes):
            raise ValueError(f"an organ named '{organ.name}' is already registered")
        self._routes.append((organ, frozenset(intents)))

    def route(self, text, intent=None):
        """Eq 4.2 — select every organ with relevance >= threshold, or the best one."""
        if not self._routes:
            raise ValueError("no organs registered")
        scores = {
            organ.name: max(
                organ.relevance(text),
                1.0 if intent is not None and intent in intents else 0.0,
            )
            for organ, intents in self._routes
        }
        selected = [organ for organ, _ in self._routes
                    if scores[organ.name] >= self._threshold]
        fallback_used = not selected
        if fallback_used:
            selected = [max((organ for organ, _ in self._routes),
                            key=lambda organ: scores[organ.name])]
        return RoutingDecision(tuple(selected), scores, fallback_used)
