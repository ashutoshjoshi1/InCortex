"""StrategyBank — testing strategies against each other (Eq 6.3-6.4).

The bandit core of advanced learning: each strategy keeps a running value
Q updated after every use (Eq 6.3), and selection balances exploiting the
best-known strategy against exploring under-tried ones via the UCB bonus
(Eq 6.4). Every trial is recorded — the experiment tracking of
Design_Doc §21 Phase 9 — and compare() is the model-comparison table.
"""

import math
from collections import deque

ETA = 0.1     # Eq 6.3 learning rate
KAPPA = 1.0   # Eq 6.4 exploration weight
EXPERIMENT_LOG_SIZE = 1000


class StrategyBank:
    def __init__(self, eta=ETA, kappa=KAPPA):
        self._eta = eta
        self._kappa = kappa
        self._strategies = {}  # name -> {"description", "q", "trials"}
        self._total_trials = 0
        self._experiments = deque(maxlen=EXPERIMENT_LOG_SIZE)

    def add(self, name, description=""):
        """Register a strategy worth testing."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("strategy name must be a non-empty string")
        if name in self._strategies:
            raise ValueError(f"strategy '{name}' already exists")
        self._strategies[name] = {"description": description,
                                  "q": 0.0, "trials": 0}

    def select(self):
        """Eq 6.4 — untried strategies first, then UCB argmax."""
        if not self._strategies:
            raise ValueError("no strategies registered")
        for name, stats in self._strategies.items():
            if stats["trials"] == 0:
                return name
        return max(self._strategies,
                   key=lambda name: self._ucb(self._strategies[name]))

    def _ucb(self, stats):
        bonus = self._kappa * math.sqrt(
            math.log(self._total_trials) / stats["trials"])
        return stats["q"] + bonus

    def record(self, name, score):
        """Eq 6.3 — pull the strategy's value toward the observed score."""
        stats = self._get(name)
        if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
            raise ValueError("score must be a number in [0, 1]")
        stats["q"] += self._eta * (score - stats["q"])
        stats["trials"] += 1
        self._total_trials += 1
        self._experiments.append({"strategy": name, "score": float(score)})

    def q_value(self, name):
        return self._get(name)["q"]

    def compare(self):
        """The model-comparison table: strategies ranked by learned value."""
        return sorted(
            ({"strategy": name, "q_value": stats["q"],
              "trials": stats["trials"], "description": stats["description"]}
             for name, stats in self._strategies.items()),
            key=lambda row: -row["q_value"],
        )

    @property
    def experiments(self):
        """Every recorded trial, oldest first (bounded)."""
        return tuple(self._experiments)

    def _get(self, name):
        if name not in self._strategies:
            raise ValueError(f"no strategy named '{name}'")
        return self._strategies[name]
