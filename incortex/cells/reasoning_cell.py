"""ReasoningCell — thinks through a question against retrieved evidence.

Phase 3 implementation: a three-step chain (identify the question's focus,
match evidence against it, form a conclusion) whose raw confidence is the
geometric mean of the step confidences (Eq 3.1) — so one shaky step drags
the whole conclusion down, and a step at zero zeroes the chain. The
keyword-based steps are placeholders for model-backed reasoning; the chain
contract will not change.
"""

from incortex.cells.base_cell import BaseCell
from incortex.cells.cell_math import (
    CONTENT_STOPWORDS as STOPWORDS,
    clip01,
    pipeline_confidence,
    tokenize,
)
# A conclusion is 'supported' when evidence covers at least half the focus.
SUPPORT_THRESHOLD = 0.5
DEFAULT_EVIDENCE_SCORE = 0.5
NO_EVIDENCE_CONFIDENCE = 0.1


class ReasoningCell(BaseCell):
    """Message: {"question": str, "evidence"?: [{"content": str, "score"?: float}]}."""

    def __init__(self, name="reasoning_cell"):
        super().__init__(name, "reasoning")

    def _validate(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        question = message.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"{self.name}: 'question' must be a non-empty string")
        evidence = message.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError(f"{self.name}: 'evidence' must be a list")
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("content"), str):
                raise ValueError(f"{self.name}: each evidence item needs a 'content' string")
            score = item.get("score", DEFAULT_EVIDENCE_SCORE)
            if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
                raise ValueError(f"{self.name}: evidence 'score' must be in [0, 1]")

    def _process(self, message):
        evidence = message.get("evidence", [])

        # Step 1 — identify what the question is actually about.
        focus = frozenset(tokenize(message["question"])) - STOPWORDS
        steps = [self._step(
            "identify_focus",
            f"focus words: {sorted(focus)}" if focus else "no content words found",
            1.0 if focus else 0.0,
        )]

        # Step 2 — how well does the evidence cover the focus?
        best_item, coverage = self._best_evidence(focus, evidence)
        steps.append(self._step(
            "match_evidence",
            f"{len(evidence)} evidence items, best coverage {coverage:.2f}",
            coverage,
        ))

        # Step 3 — conclude, or admit there is nothing to conclude from.
        if best_item is not None and coverage > 0.0:
            supported = coverage >= SUPPORT_THRESHOLD
            conclusion = best_item["content"]
            conclusion_confidence = clip01(best_item.get("score", DEFAULT_EVIDENCE_SCORE))
        else:
            supported = False
            conclusion = "I cannot conclude anything - I have no relevant evidence."
            conclusion_confidence = NO_EVIDENCE_CONFIDENCE
        steps.append(self._step("form_conclusion", conclusion, conclusion_confidence))

        chain = pipeline_confidence([step["confidence"] for step in steps])  # Eq 3.1
        content = {
            "conclusion": conclusion,
            "supported": supported,
            "coverage": coverage,
            "steps": steps,
        }
        return content, chain

    @staticmethod
    def _best_evidence(focus, evidence):
        """The item covering the most focus words (score breaks ties)."""
        best_item, best_key = None, (0.0, 0.0)
        for item in evidence:
            tokens = frozenset(tokenize(item["content"]))
            coverage = len(focus & tokens) / len(focus) if focus else 0.0
            key = (coverage, item.get("score", DEFAULT_EVIDENCE_SCORE))
            if key > best_key:
                best_item, best_key = item, key
        return best_item, best_key[0]

    @staticmethod
    def _step(name, detail, confidence):
        return {"name": name, "detail": detail, "confidence": clip01(confidence)}
