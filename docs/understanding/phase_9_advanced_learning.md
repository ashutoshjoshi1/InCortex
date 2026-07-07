# Understanding Phase 9 — Advanced Learning

This document explains **every function built in Phase 9 in plain language**, completing the series ([Phase 1](phase_1_cell_system.md) · [Phase 2](phase_2_tissue_system.md) · [Phase 3](phase_3_organ_system.md) · [Phase 4](phase_4_cortex_core.md) · [Phase 5](phase_5_memory_learning.md) · [Phase 6](phase_6_voice_system.md) · [Phase 7](phase_7_tool_system.md) · [Phase 8](phase_8_development_organ.md)). Equation references point into [math_model.md](../math_model.md).

Phase 9 finished the roadmap: the last unimplemented equations of the math model became code. The brain can now **test strategies against each other and let the best one win** (Eq 6.3–6.4), **promote reliably successful behavior into remembered skills** (Eq 6.6 — the mirror image of Phase 5's remembered weaknesses), and **grade its own honesty** — checking whether its confidence numbers actually predict its outcomes (Eq 6.7).

*Honest scope note:* the design doc's Phase 9 list also names a fine-tuning pipeline. Fine-tuning is a v1.0 capability by the doc's own learning timeline (§12.7) and the math model defers it explicitly (§6.7: "these enter at v1.0/v1.5 and will get their own detailed spec"). It is not pretended at here.

---

## The Big Picture

Until now, learning meant *recording*: scores logged, mistakes clustered, memories updated. Phase 9 adds *choosing*: when there is more than one way to do something, the system runs a fair competition, tracks every trial, and shifts future behavior toward what works. The demo makes it visible: three explanation styles, a simulated user who loves plain English — after three rounds each style has one trial; after 45, the winner has 38 of them and a learned value of 0.884.

And a system that grades itself needs its grades audited: the SelfEvaluator is the auditor, fed automatically by every piece of feedback the Cortex receives.

---

## `learning/learning_loop.py` — the strategy competition

### `StrategyBank.add(name, description="")`
Registers a strategy worth testing (a prompt style, a reasoning mode, a retrieval setting…). Duplicates and blank names rejected.

### `select()` — *which strategy should this task use?* (Eq 6.4)
Two rules:

1. **Untried strategies go first** — you cannot rank what you have never tried.
2. After that, **UCB** (Upper Confidence Bound): pick the strategy with the highest *learned value + exploration bonus*, where the bonus, κ·√(ln N / n), grows for strategies that haven't been tried in a while. This solves the classic dilemma: pure exploitation would lock onto an early favorite forever; pure exploration would never profit from what it learned. The bonus guarantees a neglected strategy is always *eventually* re-checked — one test pins this: a strategy ignored for 200 rounds accumulates enough bonus to be selected again, however mediocre its record.

### `record(name, score)` — *how did it go?* (Eq 6.3)
Pulls the strategy's running value Q a fraction (η = 0.1) of the way toward the observed score — the same moving-average idea as cell health, applied to behavior. Exact numbers are tested: starting at 0, one 0.8-score trial gives Q = 0.08; a second gives 0.152; two hundred trials at a constant 0.6 converge to 0.6 within a millionth (§11 property 7). Every trial also lands in the **experiment log** — the phase's experiment-tracking deliverable, bounded at the last 1000 trials.

### `q_value(name)` / `compare()` / `experiments`
The lookup, the **model-comparison table** (strategies ranked by learned value, with trial counts and descriptions), and the trial history. `compare()` is what the demo prints.

---

## `learning/evaluator.py` — the honesty auditor

### `SelfEvaluator.record(confidence, outcome)`
One prediction meeting reality: "I was 74% confident" + "the user said it was right/wrong."

### `brier()` — *how far off were the numbers?* (Eq 6.7)
The average squared gap between confidence and outcome. Perfectly honest predictions score 0; perfectly backwards ones score 1. The number to beat is **0.25** — what you'd score by lazily saying "50%" to everything. A brain below 0.25 is genuinely informative about itself; the tests pin all three landmarks (perfect → 0, always-wrong → 1, always-0.5 → exactly 0.25).

### `ece(bins=10)` — *is 80% really 80%?* (Eq 6.7)
Groups predictions into confidence bins and compares each bin's *claimed* confidence with its *actual* accuracy. A system that says "90%" but is right half the time gets an ECE contribution of |0.5 − 0.9| = 0.4 — the overconfidence test pins exactly this.

### `report()`
Samples, both scores, the 0.25 baseline, and a plain `beats_baseline` verdict. With no data, the scores are honestly `None` — no fabricated calibration.

---

## `learning/skill_builder.py` — the mirror of the mistake tracker

### `SkillCluster` (record)
One behavioral pattern: its representative description, trials, successes, examples — plus two computed properties:

- **`smoothed_success`** — (successes+1)/(trials+2), the *rule of succession* yet again (the same formula as newborn-cell confidence in Phase 1). Five wins out of five gives 6/7 ≈ 0.857, not a cocky 1.0.
- **`is_skill`** — the Eq 6.6 promotion rule: **at least 5 trials AND smoothed success ≥ 0.8**. Both are needed: four perfect trials fail on volume (tested); five trials with two failures fail on quality (4/7 ≈ 0.571 — tested). Small samples cannot sneak through.

### `SkillBuilder.record(success, description)`
Clusters task descriptions by embedding similarity (the same vector machinery as memory and the mistake tracker) — but with one crucial difference from the MistakeTracker: **both successes and failures count into a cluster**, because a skill is a success *rate*, not a success count. A flaky behavior can never be promoted by counting only its good days.

### `clusters` / `promoted()`
All patterns seen; the ones currently qualifying as skills.

---

## The wiring — closing the loop

### `LearningOrgan` (upgraded)
Now carries all three: `skills` (fed automatically — every scored event with a description lands in the SkillBuilder), `strategies` (the bank, ready for anything that wants to test alternatives), and `evaluator`, reachable via the new **`record_confidence(confidence, success)`**.

### `CortexCore.feedback(...)` (upgraded)
Two new lines with real consequences:

1. **Self-evaluation is automatic**: every feedback pairs the task's chain confidence with the actual outcome — the brain's honesty is audited continuously, for free.
2. **`_escalate_skills`** — the mirror of Phase 5's weakness escalation: when a cluster crosses the Eq 6.6 bar, the Cortex stores *"Learned skill: I am reliably good at 'What is photosynthesis?' (5/5 successes)"* into memory at importance 0.9, once per skill, announced on the bus. The brain's self-image now records both what it's bad at *and* what it's good at.

### `examples/strategy_demo.py`
The whole phase in 45 deterministic rounds: three styles registered, UCB exploring then converging (Q table printed at rounds 3, 15, 45), every experiment tracked, and a closing calibration report that beats the 0.25 baseline.

---

## The tests — what the 28 new checks prove

Added to `tests/test_learning.py`:

- **The bank does the math**: untried-first ordering; the exact 0.08 → 0.152 value updates; convergence to a stationary reward within 10⁻⁶; UCB preferring the better strategy at equal trials *and* revisiting a strategy neglected for 200 rounds; experiments tracked; the comparison table ranked correctly; empty banks, unknown strategies, and out-of-range scores all loud errors.
- **The auditor knows its landmarks**: Brier 0 / 1 / 0.25 for perfect / backwards / always-half; ECE catching a 90%-claiming coin-flipper at exactly 0.4; honest `None` with no data.
- **Promotion is strict**: similar tasks cluster while different topics don't; the rule of succession computed exactly; four perfect trials rejected on volume, five flaky ones on quality.
- **The wiring holds**: descriptions flow from `score()` into the skill builder; `record_confidence` reaches the evaluator; the organ carries a working bank.
- **The Phase 9 success criterion** has three named tests: (1) three strategies with hidden reward rates are tested, compared, and the best one wins the most trials — *test, compare, improve*; (2) five successful answers to the same question become exactly one "Learned skill" memory, never duplicated; (3) every Cortex feedback feeds the calibration report.
