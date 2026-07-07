# Understanding Phase 3 — The Organ System

This document explains **every function built or changed in Phase 3 in plain language**, continuing the series ([Phase 1](phase_1_cell_system.md) · [Phase 2](phase_2_tissue_system.md)). Equation references point into [math_model.md](../math_model.md).

Phase 3 built the **Organ** — a specialized subsystem made of Tissues and Cells, like a department in a company: Cells are workers, Tissues are teams, and Organs are whole departments with a specialty (language, memory, reasoning, learning, safety). Two new Cells arrived too, because two departments needed their specialists: the ReasoningCell and the SafetyCell.

---

## The Big Picture

Three new ideas run through this phase:

1. **Chain confidence.** When an answer passes through several stages, its trustworthiness must *degrade* — a conclusion built on shaky steps is shaky. You can see this live in the CLI: every reply now shows its chain confidence, and asking about something the system was never taught visibly drops the number.
2. **Relevance.** Every Organ can now answer "how relevant am I to this message?" — the foundation for Phase 4, where a Router will use these scores to decide which departments handle each request.
3. **The safety gate.** Before any risky action would run, it must pass a mathematical gate that is *fail-closed*: when the system doesn't know how dangerous something is, it assumes the worst.

---

## Additions to `cell_math.py`

### `pipeline_confidence(confidences, mode)`
The confidence of a whole chain of stages. *(Eq 3.1)*

- **Geometric mode** (default): multiply all the stage confidences together, then take the n-th root. The key property: one weak stage hurts far more than averaging would admit. Stages of 0.9, 0.9, and 0.2 give **0.545**, not the flattering 0.67 an average would claim. And a stage at zero zeroes the whole chain — you cannot build certainty on a step you know nothing about.
- **Min mode** (conservative): the chain is exactly as trustworthy as its *weakest* stage. Used by safety-relevant organs, where optimism is a bug.

### `overlap_coefficient(tokens_a, tokens_b)`
How much do two word-sets overlap, measured against the *smaller* set: shared words ÷ size of the smaller set. A two-word query hitting one of an organ's ten capability keywords scores 0.5 — kinder to short queries than Phase 1's Jaccard, which would divide by all eleven words combined. This is the Phase 3 stand-in for embedding similarity *(Eq 3.2)*; real semantic vectors arrive in Phase 5.

---

## `reasoning_cell.py` — the thinker *(new Cell)*

Takes a question plus whatever memory retrieved, and thinks in **three explicit steps**, each with its own confidence. The whole chain's confidence is the geometric mean of the steps — so the cell's output confidence *is* the strength of its weakest reasoning.

### `_validate(message)`
The message needs a real question; evidence (optional) must be a list of items each carrying a `content` string, with scores (if present) between 0 and 1.

### `_process(message)`
The three steps:

1. **`identify_focus`** — strip away grammar glue and command verbs ("what", "is", "explain", "teach"…) to find what the question is actually *about*. "What is photosynthesis?" → focus: `photosynthesis`. Confidence 1.0 if any focus words were found, 0 if the question was all filler ("what is it") — and since a zero stage zeroes the chain, a contentless question honestly yields zero confidence.
2. **`match_evidence`** — for each piece of evidence, measure *coverage*: what fraction of the focus words it mentions. Confidence = the best coverage found. No evidence → 0 → the chain collapses to 0, which is exactly right.
3. **`form_conclusion`** — adopt the best-covering evidence as the conclusion (its retrieval score becomes this step's confidence), or admit "I cannot conclude anything — I have no relevant evidence" at a floor confidence of 0.1.

A conclusion is marked **supported** only when evidence covers at least half the focus. The output includes all three steps with their details and confidences — the reasoning is inspectable, never a black box.

Worked example (also a test): "What is photosynthesis?" against evidence scored 0.66 → steps 1.0, 1.0, 0.66 → chain = ∛0.66 ≈ **0.871**.

### `_best_evidence(focus, evidence)` (internal)
Picks the evidence item with the highest coverage; retrieval score breaks ties.

### `_step(name, detail, confidence)` (internal)
Builds one step record with its confidence clamped to 0–1.

---

## `safety_cell.py` — the gatekeeper *(new Cell)*

Every action wanting to run must pass this gate. Actions carry a **permission level** (0 = harmless explanation … 5 = system-level) and optionally estimates of how likely harm is and how bad it would be.

### `_validate(message)`
Strict at the door: a real action name; a permission level that is a genuine integer 0–5 (a sneaky `True` is rejected — in Python `True` counts as 1, so this needs an explicit check); estimates, if given, between 0 and 1.

### `_process(message)`
1. **Risk = harm probability × impact** *(Eq 7.1)* — the classic formula: a likely-but-trivial action and an unlikely-but-catastrophic one can carry the same risk.
2. **Fail-closed defaults**: if either estimate is missing, it is assumed to be **1.0** — the worst case. An action of unknown risk is treated as maximally risky; ignorance can never sneak below the threshold. The output flags `assumed_worst_case` so reviewers can see when this happened.
3. **The gate** *(Eq 7.2)*, checked in order:
   - **Execute** — level within the ceiling (default 2) *and* risk below 0.3.
   - **Require approval** — level 4 or 5 (those always need a human, whatever the numbers), *or* risk ≥ 0.3 at any level.
   - **Block** — above the ceiling but otherwise low-risk (there is no human question to ask; it is simply beyond what configuration allows).

   This ordering reproduces the design doc's own acceptance examples: "send email" → approval, "run shell command" → approval.

Every decision ships with a human-readable `reason` string, and the cell's confidence is always 1.0 — the gate is pure arithmetic, nothing to be unsure about.

---

## `reasoning_tissue.py` — the thinking team *(new Tissue)*

### `ReasoningTissue.__init__` / `reason(question, evidence)` / `process(message)`
A team of one for now: wraps the ReasoningCell (critical), exposing `reason()` and accepting the same dict messages as the cell. Later phases add cells for different reasoning modes behind this same interface.

---

## `base_organ.py` — the DNA every Organ shares

### `OrganOutput` (a frozen record)
The organ-level answer envelope: organ name, content, confidence, and the tissue/cell outputs behind it — same transparency principle as `TissueOutput`.

### `BaseOrgan.__init__(name, capability_keywords, confidence_mode)`
Birth of an Organ: a name, a set of **capability keywords** (the vocabulary of requests this department handles), and a confidence mode — `geometric` for most, `min` for organs where caution beats optimism.

### `add_tissue(tissue, critical=False)` / `add_cell(cell, critical=False)`
Organs are made of Tissues *and* loose Cells (the design doc allows both; the SafetyOrgan holds its gate cell directly). Both go through the same hiring checks: right type, no duplicate names. Critical components cap the organ's health, exactly like critical cells cap a tissue's.

### `cells` (property)
All leaf Cells in the organ, flattened — tissues are unpacked to their member cells, loose cells included as-is. This is how the CLI gathers "everyone who took part" for feedback distribution.

### `pipeline(confidences)`
Combines stage confidences using *this organ's* mode — the ReasoningOrgan gets min-mode caution for free wherever it chains stages. *(Eq 3.1)*

### `relevance(text)`
"How relevant am I to this message?" — overlap between the message's words and the organ's capability keywords, 0 to 1. Empty or non-text messages score 0. Phase 4's Router will call this on every organ and route to those above a threshold. *(Eq 3.2 stand-in)*

### `process(message)`
Deliberately unimplemented in the base class — every department defines its own workflow. Calling it on a bare `BaseOrgan` raises `NotImplementedError`.

### `learn(feedback)`
Feedback flows down through every component to every leaf cell.

### `health_check()`
The recursive health report: mean of component healths, **capped by the weakest critical component** — the same pessimistic rule as tissues, now applied one level up *(Eq 2.4 recursively)*. Cell health rolls into tissue health rolls into organ health; the CLI's `health` command prints all three levels. An organ with no components reports 0.

---

## The five concrete Organs

### `language_organ.py`
Wraps the LanguageTissue (critical). `understand(text)` cleans and classifies; `respond(intent, text, memory_results)` writes the reply; `process` = understand. Capability keywords: explain, describe, chat, teach, and friends.

### `memory_organ.py`
Wraps the MemoryTissue (critical). `store`, `retrieve`, and `process` (dict dispatch) pass straight through — the organ shell is thin now, but it is where Phase 5's short-term/long-term/vector memory tissues will plug in without anything upstream changing. Keywords: remember, recall, know, forget…

### `reasoning_organ.py`
Wraps the ReasoningTissue (critical), and is the first organ to run in **min confidence mode**: per the math model, a reasoning chain is never more trustworthy than its weakest link. `reason(question, evidence)` and dict-based `process`. Keywords: why, how, compare, solve…

### `learning_organ.py`
Wraps the LearningTissue (critical). `score(feedback)` grades one event and updates the running average; `distribute(feedback, cells)` also teaches every participating cell. Keywords: feedback, good, bad, improve…

### `safety_organ.py`
Wraps the SafetyCell (critical, min mode) and adds two department-level duties:

- **`check(action, permission_level, harm_probability, impact)`** — the full gate. First consults the **blocklist**: actions that are *never* allowed regardless of scores (defaults: `change_safety_policy`, `modify_own_code`, `delete_all_files`, `delete_all_memory` — the design doc's non-negotiables, like constitutional limits that no arithmetic can override). Everything else goes through the SafetyCell's gate. Omitted risk estimates are simply not sent, so the cell's fail-closed worst-case defaults kick in.
- **`decisions`** (property) — every decision is logged (action, decision, risk, reason) in a bounded log (default: last 100), satisfying the design doc's "log important actions." The log forgets the oldest entries first.

*(Deliberately deferred: the z-score anomaly flagging of Eq 7.3 belongs with the metrics work in a later phase.)*

---

## `scripts/run_cli.py` — rewired to run on Organs

### `respond(language, memory, reasoning, text)`
The Phase 3 chain: understand → (store | retrieve → **reason**) → reply. New in this phase: every stage's confidence is collected and combined with `pipeline_confidence`, and the reply line shows it: `[chain confidence 0.69]`. Ask about something never taught and watch it fall — the smoke test shows 0.69 for a genuine memory match versus 0.40 for a spurious word-overlap match.

### `give_feedback(learning, organs, success)`
Gathers every leaf cell from the participating organs (via the new `cells` property) and hands them to the LearningOrgan.

### `print_health(organs)`
Now three levels deep: organ → tissue → cell, mirroring the recursive health math.

### `main()`
Builds four Organs (Language, Memory, Reasoning, Learning) and runs the same command loop.

---

## The tests — what the 60 new checks prove

`tests/test_organs.py` (44 tests) plus additions to `test_cells.py` (13) and `test_tissues.py` (3):

- **The chain math** hits its landmark numbers: (0.9, 0.9, 0.2) → 0.545 exactly as the math doc's worked example promises; geometric never beats the plain average; one zero stage kills the chain; min mode returns the weakest link.
- **BaseOrgan keeps its promises**: type and duplicate checks, recursive health with the same 0.611/0.371 numbers as the tissue tests one level down, feedback reaching every leaf cell, relevance scoring by capability keywords.
- **ReasoningCell** shows its work: three named steps, the ∛0.66 ≈ 0.871 worked example, honest zeros for contentless questions and missing evidence, "supported" only above half coverage.
- **SafetyCell** enforces the gate: risk is exactly probability × impact; the gate never *loosens* as risk grows (tested across the whole range — a monotonicity property straight from math §11); missing estimates are worst-cased; `True` is not a valid permission level.
- **SafetyOrgan** reproduces the design doc's §26.3 acceptance examples verbatim — change safety policy → blocked, delete all files → blocked, run shell command → approval, send email → approval — and its decision log is bounded and ordered.
- **The Phase 3 success criterion** has a named test: one task flowing through all five organs — understand, store, retrieve, reason, respond, gate, and learn — with chain confidence degrading along the way.
