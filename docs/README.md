# `docs/` — Project Documentation

Deep-dive documentation, split out from [Design_Doc.md](../Design_Doc.md) as each area is implemented.

| Document                                             | Covers                                        | Design Doc source |
| ---------------------------------------------------- | --------------------------------------------- | ----------------- |
| [architecture.md](architecture.md)                   | Layers, Cortex Core, message system            | §7–§8, §13–§14    |
| [biological_model.md](biological_model.md)           | Cell → Tissue → Muscle → Organ → Cortex        | §4, §9–§12        |
| [memory_system.md](memory_system.md)                 | Memory types, storage, importance scoring      | §15               |
| [learning_system.md](learning_system.md)             | Feedback loops, scoring, learning timeline     | §16               |
| [safety_model.md](safety_model.md)                   | Permission levels, approval, ethics            | §11.2, §12.9, §25 |
| [math_model.md](math_model.md)                       | Equations for every layer: confidence, health, memory decay, learning, risk | formalizes §9–§16, §25, §27 |
| [api_reference.md](api_reference.md)                 | REST endpoints and schemas                     | §19               |
| [development_phases.md](development_phases.md)       | Phase-by-phase build plan                      | §21 / ROADMAP.md  |

## Understanding Docs

`understanding/` holds one plain-language document per **completed** phase, explaining every function built in that phase — written for readers, not just coders. This is a standing convention: a phase is not done until its understanding doc exists.

| Document | Phase |
| -------- | ----- |
| [understanding/phase_1_cell_system.md](understanding/phase_1_cell_system.md) | Phase 1 — Cell System |
| [understanding/phase_2_tissue_system.md](understanding/phase_2_tissue_system.md) | Phase 2 — Tissue System |
| [understanding/phase_3_organ_system.md](understanding/phase_3_organ_system.md) | Phase 3 — Organ System |
| [understanding/phase_4_cortex_core.md](understanding/phase_4_cortex_core.md) | Phase 4 — Cortex Core |
| [understanding/phase_5_memory_learning.md](understanding/phase_5_memory_learning.md) | Phase 5 — Memory and Learning |
| [understanding/phase_6_voice_system.md](understanding/phase_6_voice_system.md) | Phase 6 — Voice System |
| [understanding/phase_7_tool_system.md](understanding/phase_7_tool_system.md) | Phase 7 — Tool/Muscle System |
| [understanding/phase_8_development_organ.md](understanding/phase_8_development_organ.md) | Phase 8 — Development Organ |
| [understanding/phase_9_advanced_learning.md](understanding/phase_9_advanced_learning.md) | Phase 9 — Advanced Learning |
| [understanding/phase_10_api_config.md](understanding/phase_10_api_config.md) | Phase 10 — API & Configuration |

`assets/` holds images used by the README and docs.
