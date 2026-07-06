"""IntentCell — classifies what the user wants.

Phase 1 implementation: keyword scoring over intent classes, turned into a
probability distribution with a temperature softmax (Eq 1.3) and scored with
entropy confidence (Eq 1.4). The keyword scorer is a placeholder for a model-
backed classifier; the surrounding math contract will not change.
"""

import re

from incortex.cells.base_cell import BaseCell, require_nonempty_text
from incortex.cells.cell_math import entropy_confidence, softmax

INTENT_KEYWORDS = {
    "teach": ("teach", "teach yourself", "learn", "study"),
    "remember": ("remember", "i like", "i prefer", "my favorite", "note that"),
    "explain": ("explain", "what is", "what are", "how does", "why",
                "tell me about", "describe"),
    "chat": ("hello", "hey", "thanks", "thank you", "bye", "good morning"),
}
# Laplace-style floor so unmatched intents keep a little probability mass —
# without it a single keyword hit would look absolutely certain.
BASE_SCORE = 0.1
SOFTMAX_TEMPERATURE = 0.5


class IntentCell(BaseCell):
    def __init__(self, name="intent_cell"):
        super().__init__(name, "intent")

    def _validate(self, message):
        require_nonempty_text(self.name, message)

    def _process(self, message):
        text = " ".join(message.lower().split())
        labels = list(INTENT_KEYWORDS)
        scores = [
            BASE_SCORE + self._keyword_hits(text, INTENT_KEYWORDS[label])
            for label in labels
        ]
        probabilities = softmax(scores, temperature=SOFTMAX_TEMPERATURE)  # Eq 1.3
        distribution = dict(zip(labels, probabilities))
        intent = max(distribution, key=distribution.get)
        content = {"intent": intent, "distribution": distribution}
        return content, entropy_confidence(probabilities)  # Eq 1.4

    @staticmethod
    def _keyword_hits(text, keywords):
        hits = 0
        for keyword in keywords:
            if " " in keyword:
                hits += keyword in text
            else:
                # Word-boundary match so "hi" never fires inside "this".
                hits += re.search(rf"\b{re.escape(keyword)}\b", text) is not None
        return hits
