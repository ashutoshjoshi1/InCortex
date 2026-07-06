"""ResponseCell — turns an intent plus memory results into a human reply.

The final Cell in the Language Tissue chain (Design_Doc §10). Phase 2 uses
intent-keyed templates; a model-backed generator can replace the templates
later without changing the contract. Its confidence is honest about answer
quality: acknowledgements are certain, answers inherit their memory's
retrieval score, and "I don't know" admits near-zero confidence.
"""

from incortex.cells.base_cell import BaseCell
from incortex.cells.cell_math import clip01

VALID_INTENTS = ("teach", "remember", "explain", "chat")
ACK_CONFIDENCE = 1.0        # storing/acknowledging is a certain act
CHAT_CONFIDENCE = 0.9       # a greeting is almost never the wrong reply
NO_ANSWER_CONFIDENCE = 0.1  # admitting ignorance is honest, not confident


class ResponseCell(BaseCell):
    """Message: {"intent": str, "text": str, "memory_results"?: [{"content", "score"}]}."""

    def __init__(self, name="response_cell"):
        super().__init__(name, "response")

    def _validate(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        if message.get("intent") not in VALID_INTENTS:
            raise ValueError(f"{self.name}: intent must be one of {VALID_INTENTS}")
        text = message.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{self.name}: 'text' must be a non-empty string")
        results = message.get("memory_results", [])
        if not isinstance(results, list):
            raise ValueError(f"{self.name}: memory_results must be a list")
        for item in results:
            if not isinstance(item, dict) or not isinstance(item.get("content"), str):
                raise ValueError(
                    f"{self.name}: each memory result needs a 'content' string"
                )

    def _process(self, message):
        intent = message["intent"]
        text = message["text"].strip()
        results = message.get("memory_results", [])
        if intent == "teach":
            reply, confidence = f"I have learned: {text}", ACK_CONFIDENCE
        elif intent == "remember":
            reply, confidence = "Got it. I will remember that.", ACK_CONFIDENCE
        elif intent == "explain" and results:
            best = results[0]
            score = clip01(best.get("score", 0.0))
            reply = f"From memory (score {score:.2f}): {best['content']}"
            confidence = score  # the answer is only as good as the memory behind it
        elif intent == "explain":
            reply, confidence = "I don't know that yet - teach me!", NO_ANSWER_CONFIDENCE
        else:  # chat
            reply = "Hello! Teach me something, ask me a question, or tell me what to remember."
            confidence = CHAT_CONFIDENCE
        return {"reply": reply, "intent": intent}, confidence
