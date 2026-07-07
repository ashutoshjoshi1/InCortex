"""SkillBuilder — recurring successes become reusable skills (Eq 6.6).

The mirror image of the MistakeTracker: task descriptions are clustered by
embedding similarity, but here BOTH outcomes count into each cluster's
record, because a skill is a success *rate*, not a success count. A
cluster is promoted to a skill only with enough evidence (n >= 5) and a
high enough Beta-smoothed rate ((k+1)/(n+2) >= 0.8) — the same rule of
succession that keeps small samples from sneaking through.
"""

from dataclasses import dataclass, field

from incortex.memory.vector_memory import HashingEmbedder, similarity01

TAU_SKILL_SIMILARITY = 0.85
N_MIN = 5          # Eq 6.6 minimum evidence
TAU_SKILL = 0.8    # Eq 6.6 smoothed success threshold
MAX_EXAMPLES = 5


@dataclass
class SkillCluster:
    skill_id: int
    representative: str
    trials: int = 0
    successes: int = 0
    examples: list = field(default_factory=list)

    @property
    def smoothed_success(self):
        """Eq 1.5 / 6.6 — the rule of succession: (k+1)/(n+2)."""
        return (self.successes + 1) / (self.trials + 2)

    @property
    def is_skill(self):
        """Eq 6.6 — enough evidence AND a high enough smoothed rate."""
        return self.trials >= N_MIN and self.smoothed_success >= TAU_SKILL


class SkillBuilder:
    def __init__(self, similarity_threshold=TAU_SKILL_SIMILARITY, embedder=None):
        self._embedder = embedder or HashingEmbedder()
        self._threshold = similarity_threshold
        self._clusters = []  # (SkillCluster, embedding)

    def record(self, success, description):
        """Record one task outcome under its behavioral pattern."""
        if not isinstance(success, bool):
            raise ValueError("success must be a bool")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        embedding = self._embedder.embed(description)
        cluster = self._closest(embedding)
        if cluster is None:
            cluster = SkillCluster(skill_id=len(self._clusters),
                                   representative=description)
            self._clusters.append((cluster, embedding))
        cluster.trials += 1
        if success:
            cluster.successes += 1
        if len(cluster.examples) < MAX_EXAMPLES:
            cluster.examples.append(description)
        return cluster

    def _closest(self, embedding):
        best, best_similarity = None, 0.0
        for cluster, cluster_embedding in self._clusters:
            similarity = similarity01(embedding, cluster_embedding)
            if similarity >= self._threshold and similarity > best_similarity:
                best, best_similarity = cluster, similarity
        return best

    @property
    def clusters(self):
        return tuple(cluster for cluster, _ in self._clusters)

    def promoted(self):
        """The clusters that currently qualify as skills (Eq 6.6)."""
        return tuple(cluster for cluster, _ in self._clusters
                     if cluster.is_skill)
