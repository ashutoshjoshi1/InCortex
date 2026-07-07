"""Advanced learning demo — strategies compete, the brain calibrates.

Three explanation styles are tested against a (deterministic, simulated)
user who strongly prefers simple language. Watch UCB explore all three,
then converge on the winner — and the calibration report say whether the
system's confidence was honest.

Run:  python examples/strategy_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.learning import SelfEvaluator, StrategyBank

# What the simulated user actually thinks of each style (unknown to the bank).
TRUE_RATINGS = {"simple-english": 0.9, "formal-tone": 0.5, "dense-jargon": 0.1}
ROUNDS = 45


def main():
    bank = StrategyBank()
    for name in TRUE_RATINGS:
        bank.add(name, f"respond in {name.replace('-', ' ')}")
    evaluator = SelfEvaluator()

    for round_number in range(1, ROUNDS + 1):
        strategy = bank.select()                 # Eq 6.4: explore vs exploit
        rating = TRUE_RATINGS[strategy]
        bank.record(strategy, rating)            # Eq 6.3: value update
        evaluator.record(bank.q_value(strategy), rating >= 0.5)
        if round_number in (3, 15, ROUNDS):
            print(f"after round {round_number}:")
            for row in bank.compare():
                print(f"  {row['strategy']:<15} Q={row['q_value']:.3f} "
                      f"trials={row['trials']}")

    print("\nexperiments tracked:", len(bank.experiments))
    print("winner:", bank.compare()[0]["strategy"])
    report = evaluator.report()
    print(f"calibration: brier={report['brier']:.3f} ece={report['ece']:.3f} "
          f"(baseline 0.25, beats it: {report['beats_baseline']})")


if __name__ == "__main__":
    main()
