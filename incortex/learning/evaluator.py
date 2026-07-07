"""SelfEvaluator — is the brain's confidence honest? (Eq 6.7)

Collects (predicted confidence, actual outcome) pairs and reports the two
standard calibration measures: the Brier score (mean squared gap between
confidence and outcome; 0.25 is the 'always say 0.5' baseline to beat)
and the Expected Calibration Error (bin predictions by confidence, compare
each bin's claimed confidence against its actual accuracy).
"""

BASELINE_BRIER = 0.25  # the score of always predicting 0.5
DEFAULT_BINS = 10


class SelfEvaluator:
    def __init__(self):
        self._samples = []  # (confidence, outcome as 0/1)

    def record(self, confidence, outcome):
        """One prediction meeting reality."""
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be a number in [0, 1]")
        if not isinstance(outcome, bool):
            raise ValueError("outcome must be a bool")
        self._samples.append((float(confidence), 1.0 if outcome else 0.0))

    def brier(self):
        """Eq 6.7 — mean squared error of confidence vs. outcome; None if no data."""
        if not self._samples:
            return None
        return sum((confidence - outcome) ** 2
                   for confidence, outcome in self._samples) / len(self._samples)

    def ece(self, bins=DEFAULT_BINS):
        """Eq 6.7 — expected calibration error over confidence bins; None if no data."""
        if not self._samples:
            return None
        binned = [[] for _ in range(bins)]
        for confidence, outcome in self._samples:
            index = min(int(confidence * bins), bins - 1)
            binned[index].append((confidence, outcome))
        total = len(self._samples)
        error = 0.0
        for bucket in binned:
            if not bucket:
                continue
            mean_confidence = sum(c for c, _ in bucket) / len(bucket)
            accuracy = sum(o for _, o in bucket) / len(bucket)
            error += (len(bucket) / total) * abs(accuracy - mean_confidence)
        return error

    def report(self):
        brier = self.brier()
        return {
            "samples": len(self._samples),
            "brier": brier,
            "ece": self.ece(),
            "baseline_brier": BASELINE_BRIER,
            "beats_baseline": brier is not None and brier < BASELINE_BRIER,
        }
