# Contributing to InCortex

Thanks for your interest in InCortex! The project is currently in the **design phase** — the architecture is specified in [Design_Doc.md](Design_Doc.md) and implementation follows the phases in [ROADMAP.md](ROADMAP.md).

## Where to Contribute

| Area              | Examples                                        |
| ----------------- | ----------------------------------------------- |
| Core architecture | Cortex Core, router, message bus                |
| Memory systems    | Storage backends, retrieval, importance scoring |
| Learning          | Feedback loops, evaluation, skill building      |
| Speech            | Speech-to-text (Ear), text-to-speech (Mouth)    |
| Tools             | New tool integrations with safety levels        |
| Safety            | Permission rules, approval flows, policy tests  |
| Visualization     | Brain activity dashboards                       |
| Documentation     | Architecture docs, guides, examples             |
| Testing           | Unit, integration, safety, and learning tests   |

## Good First Issues

- Create a new Cell type
- Improve memory search
- Add unit tests
- Improve CLI output
- Write documentation
- Add examples

## Ground Rules

1. **One small job well** — Cells, modules, and PRs should each do one focused thing.
2. **Safety is non-negotiable** — changes to permissions, safety policy, or approval flows get extra scrutiny.
3. **Human approval always** — InCortex itself may draft changes, but only humans merge.
4. **Tests accompany code** — every Cell, Tissue, and Organ ships with tests.
5. **Follow the design doc** — if you want to diverge from [Design_Doc.md](Design_Doc.md), open an issue to discuss first.

## Workflow

1. Open or claim an issue describing the change.
2. Fork and branch from `main`.
3. Keep changes small and focused; add tests and docs.
4. Open a pull request referencing the issue.
