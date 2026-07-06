"""Pure math helpers implementing docs/math_model.md equations used by Cells.

Dependency-free functions so every equation is testable in isolation.
Higher layers (Tissues, Organs) will reuse these once their phases begin.
"""

import math
import re

_WORD_RE = re.compile(r"[a-z0-9']+")


def clip01(value):
    """Clamp to [0, 1] — math_model.md §0: every cross-boundary score is normalized."""
    return max(0.0, min(1.0, float(value)))


def softmax(scores, temperature=1.0):
    """Eq 1.3 / 2.1 — temperature softmax. T→0 winner-take-all, T→∞ uniform."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    scaled = [score / temperature for score in scores]
    peak = max(scaled)
    exps = [math.exp(value - peak) for value in scaled]
    total = sum(exps)
    return [value / total for value in exps]


def entropy_confidence(probabilities):
    """Eq 1.4 — c = 1 - H(p)/log K. One-hot → 1, uniform → 0."""
    k = len(probabilities)
    if k <= 1:
        return 1.0
    entropy = -sum(p * math.log(p) for p in probabilities if p > 0)
    return clip01(1.0 - entropy / math.log(k))


def ema_update(previous, sample, alpha):
    """Eq 1.7 — exponential moving average step."""
    return (1.0 - alpha) * previous + alpha * sample


# Eq 2.1 default — cold enough that a clear winner dominates
COMBINATION_TEMPERATURE = 0.5
# Eq 1.9 — status bands shared by Cells and Tissues
STATUS_ACTIVE_THRESHOLD = 0.7
STATUS_DEGRADED_THRESHOLD = 0.4


def confidence_weights(confidences, temperature=COMBINATION_TEMPERATURE):
    """Eq 2.1 — softmax mixing weights over member confidences."""
    return softmax(confidences, temperature=temperature)


def status_band(health):
    """Eq 1.9 — map a health score to active / degraded / failing."""
    if health >= STATUS_ACTIVE_THRESHOLD:
        return "active"
    if health >= STATUS_DEGRADED_THRESHOLD:
        return "degraded"
    return "failing"


def exponential_decay(elapsed, half_life):
    """Eq 5.2 — the forgetting curve. Value halves exactly every half-life."""
    if half_life <= 0:
        raise ValueError("half_life must be positive")
    return clip01(0.5 ** (elapsed / half_life))


def jaccard_similarity(tokens_a, tokens_b):
    """Phase 1 stand-in for embedding similarity (Eq 5.1) — token-set overlap.

    Replaced by vector cosine similarity when Phase 5 adds embeddings.
    """
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def tokenize(text):
    """Lowercase word extraction shared by text-handling Cells."""
    return _WORD_RE.findall(text.lower())
