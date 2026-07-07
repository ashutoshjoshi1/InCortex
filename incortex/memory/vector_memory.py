"""Vector memory — hashed embeddings with clipped-cosine similarity (Eq 5.1).

Phase 5 replaces the Jaccard word-overlap stand-in with real vector math:
each text becomes a fixed-dimension vector by feature-hashing its content
words and their character trigrams (so morphological relatives like
"photosynthesis"/"photosynthesize" land near each other). Deterministic
and dependency-free; neural embeddings can replace HashingEmbedder later
without touching anything downstream.
"""

import math
import zlib

from incortex.cells.cell_math import CONTENT_STOPWORDS, clip01, tokenize

DEFAULT_DIMENSIONS = 1024  # few enough collisions that unrelated stays ~0
MIN_DIMENSIONS = 8
TRIGRAM_WEIGHT = 0.3  # tokens dominate; trigrams add morphological affinity


def content_words(text):
    """Tokens that carry meaning — grammar glue and command verbs removed."""
    return [token for token in tokenize(text) if token not in CONTENT_STOPWORDS]


def cosine_similarity(vector_a, vector_b):
    """Raw cosine; zero vectors are similar to nothing."""
    if len(vector_a) != len(vector_b):
        raise ValueError("vectors must have the same dimensions")
    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def similarity01(vector_a, vector_b):
    """Eq 5.1 (as amended) — cosine clipped to [0, 1]; unrelated stays 0."""
    return clip01(cosine_similarity(vector_a, vector_b))


class HashingEmbedder:
    """Deterministic feature-hashing embedder: words + character trigrams."""

    def __init__(self, dimensions=DEFAULT_DIMENSIONS):
        if dimensions < MIN_DIMENSIONS:
            raise ValueError(f"dimensions must be at least {MIN_DIMENSIONS}")
        self._dimensions = dimensions

    def embed(self, text):
        """Text -> L2-normalized vector. Stopword-only text -> zero vector."""
        vector = [0.0] * self._dimensions
        for token in content_words(text):
            self._add_feature(vector, token, 1.0)
            for start in range(len(token) - 2):
                self._add_feature(vector, "#" + token[start:start + 3],
                                  TRIGRAM_WEIGHT)
        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0.0:
            vector = [value / norm for value in vector]
        return tuple(vector)

    def _add_feature(self, vector, feature, weight):
        """Signed feature hashing: an independent hash bit decides the sign,
        so bucket collisions between unrelated features cancel in expectation
        instead of accumulating into fake similarity."""
        # crc32 is stable across runs, unlike Python's randomized str hash
        encoded = feature.encode("utf-8")
        bucket = zlib.crc32(encoded) % self._dimensions
        sign = 1.0 if zlib.crc32(b"sign:" + encoded) & 1 else -1.0
        vector[bucket] += sign * weight


class VectorIndex:
    """In-RAM id -> embedding map with brute-force similarity search."""

    def __init__(self, embedder):
        self._embedder = embedder
        self._vectors = {}

    def add(self, memory_id, text):
        self._vectors[memory_id] = self._embedder.embed(text)

    def remove(self, memory_id):
        self._vectors.pop(memory_id, None)

    def similarities(self, text):
        """Similarity of the query to every indexed entry; zeros omitted."""
        query = self._embedder.embed(text)
        scores = {}
        for memory_id, vector in self._vectors.items():
            similarity = similarity01(query, vector)
            if similarity > 0.0:
                scores[memory_id] = similarity
        return scores
