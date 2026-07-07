# InCortex Roadmap

Condensed from [Design_Doc.md §21](Design_Doc.md). Each phase builds on the last — the rule is: **do not build the full brain first. Build one Cell, make it work, then grow.**

**Definition of done for every phase:** deliverables implemented, tests passing, and a plain-language walkthrough of every function added to [docs/understanding/](docs/understanding/).

## Phase 0 — Project Foundation ✅

**Goal:** Repository and basic project structure.

- README, ROADMAP, CONTRIBUTING, LICENSE
- Basic Python package + CLI starter
- Project documentation

**Done when:** the project installs locally and runs with `python scripts/run_cli.py`.

## Phase 1 — Cell System ✅

**Goal:** Build the smallest unit of intelligence.

- `BaseCell`, `TextCell`, `IntentCell`, `MemoryCell`, `FeedbackCell`
- Cell health checks, unit tests

**Done when:** a Cell can receive input, process it, return output, store feedback, and report health.

## Phase 2 — Tissue System ✅

**Goal:** Group Cells into cooperative units.

- `BaseTissue`, `LanguageTissue`, `MemoryTissue`, `LearningTissue`
- Message passing between Cells

**Done when:** multiple Cells complete one task together (`input → IntentCell → MemoryCell → ResponseCell`).

## Phase 3 — Organ System ✅

**Goal:** Specialized brain-like subsystems.

- `LanguageOrgan`, `MemoryOrgan`, `ReasoningOrgan`, `LearningOrgan`, `SafetyOrgan`

**Done when:** a full task passes through multiple Organs.

## Phase 4 — Cortex Core ✅

**Goal:** Central brain coordinator.

- `CortexCore`, Router, Scheduler, MessageBus, TaskContext, SystemState

**Done when:** the Cortex Core routes a user request through the right Organs and generates a response.

## Phase 5 — Memory and Learning ✅

**Goal:** Remember and improve.

- Short-term, long-term, and vector memory
- Feedback system, mistake tracker, learning log

**Done when:** the system remembers a topic (or a preference) and uses it later.

## Phase 6 — Voice System ✅

**Goal:** Add Ear and Mouth.

- Speech-to-text, text-to-speech, voice interface, conversation loop

**Done when:** the user can speak to InCortex and hear a spoken response.

## Phase 7 — Tool/Muscle System ✅

**Goal:** Perform actions safely.

- Tool registry; file, search, code, and API tools
- Permission and approval system

**Done when:** InCortex uses tools only after safety approval.

## Phase 8 — Development Organ ✅

**Goal:** Help develop itself safely.

- Codebase reader, issue analyzer, test runner, patch suggester, GitHub integration

**Done when:** InCortex can suggest code changes and draft pull requests, but cannot merge without human approval.

## Phase 9 — Advanced Learning ✅ *(fine-tuning deferred to v1.0 per §12.7)*

**Goal:** Deeper self-learning.

- Self-evaluation, skill library, curriculum learning, experiment tracking, fine-tuning pipeline

**Done when:** the system can test multiple strategies, compare performance, and improve future behavior.

## Learning Capability Timeline

| Learning Type          | Version | Description                               |
| ---------------------- | ------- | ----------------------------------------- |
| Memory Learning        | v0.1    | Stores useful facts and corrections       |
| Feedback Learning      | v0.1    | Learns from user ratings and corrections  |
| Error Learning         | v0.2    | Tracks repeated mistakes                  |
| Skill Learning         | v0.3    | Builds reusable task skills               |
| Self-Evaluation        | v0.4    | Scores its own outputs                    |
| Curriculum Learning    | v0.5    | Chooses what to learn next                |
| Fine-Tuning            | v1.0    | Controlled model improvement              |
| Reinforcement Learning | v1.5    | Reward-based improvement                  |
| Self-Code Improvement  | v2.0    | Suggests code changes with human approval |
