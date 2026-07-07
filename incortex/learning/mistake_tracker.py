"""MistakeTracker — clusters failures and watches the error trend (Eq 6.5).

Failure descriptions are embedded and clustered by similarity: a new
failure joins the closest existing cluster above the threshold or founds
its own. A cluster that keeps growing is a 'known weakness' the system
should remember. The error trend compares the newer half of recent
outcomes against the older half — negative means genuinely improving.
"""

from collections import deque
from dataclasses import dataclass, field

from incortex.memory.vector_memory import HashingEmbedder, similarity01

TAU_MISTAKE = 0.85  # Eq 6.5 cluster similarity threshold
DEFAULT_WINDOW = 50
DEFAULT_WEAKNESS_COUNT = 3
MAX_EXAMPLES = 5
MIN_TREND_SAMPLES = 4


@dataclass
class MistakeCluster:
    cluster_id: int
    representative: str
    count: int = 1
    examples: list = field(default_factory=list)


class MistakeTracker:
    def __init__(self, window=DEFAULT_WINDOW,
                 similarity_threshold=TAU_MISTAKE, embedder=None):
        self._embedder = embedder or HashingEmbedder()
        self._threshold = similarity_threshold
        self._clusters = []  # (MistakeCluster, embedding)
        self._outcomes = deque(maxlen=window)
        self._total_tasks = 0

    def record(self, success, description=None):
        """Record one task outcome; failures are clustered. Returns the
        failure's cluster, or None for a success."""
        if not isinstance(success, bool):
            raise ValueError("success must be a bool")
        if description is not None and not isinstance(description, str):
            raise ValueError("description must be a string")
        self._total_tasks += 1
        self._outcomes.append(success)
        if success:
            return None
        text = description or "unspecified mistake"
        embedding = self._embedder.embed(text)
        cluster = self._closest_cluster(embedding)
        if cluster is None:
            cluster = MistakeCluster(cluster_id=len(self._clusters),
                                     representative=text, examples=[text])
            self._clusters.append((cluster, embedding))
        else:
            cluster.count += 1
            if len(cluster.examples) < MAX_EXAMPLES:
                cluster.examples.append(text)
        return cluster

    def _closest_cluster(self, embedding):
        best, best_similarity = None, 0.0
        for cluster, cluster_embedding in self._clusters:
            similarity = similarity01(embedding, cluster_embedding)
            if similarity >= self._threshold and similarity > best_similarity:
                best, best_similarity = cluster, similarity
        return best

    @property
    def clusters(self):
        return tuple(cluster for cluster, _ in self._clusters)

    def repeat_rate(self, cluster):
        """Eq 6.5 — how often this mistake occurs across all recorded tasks."""
        return cluster.count / max(1, self._total_tasks)

    def error_trend(self):
        """Eq 6.5 delta-E — newer-half error rate minus older-half.

        Negative means improving; zero when there is too little data.
        """
        outcomes = list(self._outcomes)
        if len(outcomes) < MIN_TREND_SAMPLES:
            return 0.0

        def error_rate(slice_):
            return sum(1 for outcome in slice_ if not outcome) / len(slice_)

        half = len(outcomes) // 2
        return error_rate(outcomes[half:]) - error_rate(outcomes[:half])

    def known_weaknesses(self, min_count=DEFAULT_WEAKNESS_COUNT):
        """Clusters that have recurred enough to be worth remembering."""
        return tuple(cluster for cluster, _ in self._clusters
                     if cluster.count >= min_count)
