# `incortex/` — The InCortex Python Package

This is the main package. It is currently **scaffolding only** — no implementation yet. Each subdirectory maps to one layer of the biological architecture defined in [Design_Doc.md](../Design_Doc.md).

| Directory     | Layer                                        |
| ------------- | -------------------------------------------- |
| `core/`       | Cortex Core — routing, scheduling, messaging |
| `cells/`      | Smallest intelligent processing units        |
| `tissues/`    | Groups of cooperating Cells                  |
| `organs/`     | Specialized intelligence subsystems          |
| `muscles/`    | Action/execution modules                     |
| `memory/`     | Memory types and storage                     |
| `learning/`   | Feedback, evaluation, self-improvement       |
| `safety/`     | Permissions, risk, policy, approval          |
| `tools/`      | Tool registry and controlled abilities       |
| `api/`        | FastAPI service                              |
| `interfaces/` | CLI, web, and voice front-ends               |

Implementation order follows [ROADMAP.md](../ROADMAP.md): Cells first (Phase 1), then Tissues, Organs, and the Cortex Core.
