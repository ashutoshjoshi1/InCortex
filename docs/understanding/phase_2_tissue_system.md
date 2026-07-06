# Understanding Phase 2 — The Tissue System

This document explains **every function built or changed in Phase 2 in plain language**, continuing the convention started with [phase_1_cell_system.md](phase_1_cell_system.md). Equation references point into [math_model.md](../math_model.md).

Phase 2 built the **Tissue** — a group of Cells working together, like muscle fibers bundling into muscle. One new Cell joined too (the ResponseCell), because the phase's goal was a full chain: *input → IntentCell → MemoryCell → ResponseCell → reply*.

---

## The Big Picture

A single Cell does one small job. A Tissue turns several Cells into a **team** with four standing duties:

1. **Route** — hand each message only to the Cells that can handle it.
2. **Combine** — merge several Cell answers into one, trusting confident Cells more.
3. **Teach** — pass feedback down to every member.
4. **Triage** — report a collective health that never hides a sick critical member.

---

## Additions to `cell_math.py`

### `confidence_weights(confidences, temperature)`
Given each team member's confidence, computes **how much say each member gets** in the combined answer. It is softmax (from Phase 1) applied to confidences with a cold default temperature of 0.5, so a clearly more confident Cell dominates without completely silencing the others. Two Cells at 0.85 and 0.50 confidence get roughly a 67% / 33% split of the vote. *(Eq 2.1)*

### `status_band(health)`
The triage rule — health 0.7 and above is `active`, 0.4–0.7 `degraded`, below 0.4 `failing`. This existed inside `BaseCell` in Phase 1; it moved here so Cells **and** Tissues use the identical rule. *(Eq 1.9)*

---

## Additions to `base_cell.py`

### `BaseCell.accepts(message)` *(new)*
Asks a Cell "*could* you handle this message?" without actually running it. Internally it just runs the Cell's own validator and reports pass/fail instead of raising an error. Tissues use this to route messages to the right members — the simple Phase 2 stand-in for the learned gating of Eq 2.3.

*(Also changed: the private `_status` helper was removed; `health_check` now calls the shared `status_band` above. Behavior is identical.)*

---

## `response_cell.py` — the reply writer *(new Cell)*

The last link in the chain: takes an **intent** plus whatever memory found, and writes the actual sentence the user reads.

### `ResponseCell.__init__(name="response_cell")`
Registers a cell of type `"response"`.

### `_validate(message)`
The message must be a dict with a known intent (`teach`, `remember`, `explain`, or `chat`), real text, and — if memory results are attached — a proper list where every item carries a `content` string.

### `_process(message)`
Picks the reply by intent, and — importantly — sets an **honest confidence** for each kind of answer:

| Situation | Reply | Confidence | Why |
| --------- | ----- | ---------- | --- |
| teach | "I have learned: …" | 1.0 | acknowledging a stored fact is a certain act |
| remember | "Got it. I will remember that." | 1.0 | same |
| explain, memory found something | "From memory (score …): …" | *the memory's own score* | an answer is only as trustworthy as the memory behind it |
| explain, memory empty | "I don't know that yet — teach me!" | 0.1 | admitting ignorance is honest, not confident |
| chat | a friendly greeting | 0.9 | a greeting is almost never the wrong reply |

Phase 2 uses fixed templates; a language model can replace them later without changing this contract.

---

## `base_tissue.py` — the DNA every Tissue shares

### `TissueOutput` (a frozen record)
The tissue-level answer envelope: which tissue produced it, the combined content, the combined confidence, and — for transparency — the individual `CellOutput`s behind it. You can always look inside a team decision and see who said what.

### `BaseTissue.__init__(name)`
Birth of a Tissue: checks the name, starts with an empty member list and an empty set of "critical" member names.

### `cells` (property)
A read-only tuple of the member Cells — outsiders can look at the team but cannot secretly modify it.

### `add_cell(cell, critical=False)`
Hires a new member. Rejects anything that isn't a real Cell and refuses duplicate names. Marking a member **critical** means the whole tissue's health can never look better than that member's health — right for cells the tissue cannot function without.

### `get_cell(name)`
Finds a member by name, or complains clearly if no such member exists.

### `process(message)`
The default team behavior — a **broadcast**: ask every member "do you accept this?" (via `accepts`), run all who say yes, and combine their answers. If nobody accepts, that's an error — a tissue should never silently swallow a message. Specialized tissues override this with their own flows.

### `combine(outputs)`
The default merger: collects each member's content under its name, and computes the team confidence (below). Returns a `TissueOutput`.

### `combined_confidence(outputs)`
The team's confidence in its combined answer: each member's confidence, weighted by `confidence_weights`. The result always lands **between the weakest and strongest member, pulled toward the strongest** — the team believes its confident members more, but one loud voice never becomes more certain than it actually is. *(Eq 2.1 + 2.4)*

### `learn(feedback)`
Feedback flows down: every member Cell receives it and updates its own track record. One "that was wrong" teaches the whole team.

### `health_check()`
The tissue triage report. Collective health = **the average of all members, capped by the sickest critical member** *(Eq 2.4)*. So a tissue with nine healthy cells and one failing critical cell reports *failing* — deliberately pessimistic, because averages hide emergencies. An empty tissue reports health 0: a team with no members cannot do its job. The report includes every member's full health line.

---

## `language_tissue.py` — the understanding team

### `LanguageTissue.__init__(name="language_tissue")`
Assembles the fixed team: a TextCell and IntentCell (both **critical** — without them nothing works) and a ResponseCell (non-critical: even if replies degrade, understanding still functions).

### `process(message)`
Phase 2's first real **message passing between Cells**: the TextCell cleans the raw input, and its *output* becomes the IntentCell's *input*. The result carries the cleaned text, word count, winning intent, and the full intent distribution, with a confidence combining both cells' confidences.

### `respond(intent, text, memory_results)`
The speaking half: feeds intent + text + memory results to the ResponseCell and wraps the reply as a `TissueOutput`. Kept separate from `process` because in the real loop, memory retrieval happens *between* understanding and responding.

---

## `memory_tissue.py` — the library with many notebooks

### `MemoryTissue.__init__(name, memory_cells=None)`
Starts with the memory cells you give it (all marked critical — a memory system with a failing store is a failing memory system), or one fresh MemoryCell by default. Phase 5 will slot in specialized short-term/long-term/vector cells here.

### `store(content, importance=None)`
Writes the fact into **every** member notebook. Confidence is the *minimum* across members — storing only counts as certain if every copy succeeded.

### `retrieve(query, top_k=3)`
Asks every notebook, then merges: if the same fact appears in several notebooks, only the **best-scoring copy** survives (deduplication); everything is sorted best-first (ties go to the newer memory) and cut to `top_k`. Confidence = the best merged score, or 0 if nothing was found.

### `process(message)`
Accepts the same instruction dicts as a single MemoryCell (`store` / `retrieve`) so anything that talked to a MemoryCell can talk to a whole MemoryTissue without changing its message format.

---

## `learning_tissue.py` — the report-card office

### `LearningTissue.__init__(name="learning_tissue")`
A team of one (the FeedbackCell, critical), plus two counters: the running learning score and the number of events seen.

### `process(message)`
Scores one feedback event via the FeedbackCell (Eq 6.1–6.2), then updates the **running score** — a moving average (Eq 1.7) answering the question "is this system getting better lately?" One great score after ten bad ones only nudges it up 10%.

### `distribute(message, cells)`
The full feedback moment: score the event, then convert it into a `CellFeedback` (success + the normalized rating) and **teach it to every cell that took part in the task**. This is how one user thumbs-up moves the track record of the intent cell, the memory cell, and the response cell all at once — the first working piece of the design doc's learning loop.

---

## `scripts/run_cli.py` — rewired to run on Tissues

Same conversation, new anatomy: the loop now talks to three Tissues instead of individual Cells.

### `respond(language, memory, text)`
The Phase 2 success chain in four lines: `language.process` understands the input; teach/remember intents store into `memory`; explain intents retrieve from it; `language.respond` writes the reply. The ad-hoc reply templates that lived in this script in Phase 1 moved into the ResponseCell, where they can be tested and given honest confidences.

### `give_feedback(learning, tissues, success)`
Gathers every cell from the participating tissues and hands them to `LearningTissue.distribute` — then reports the score, its band, and the running average.

### `print_health(tissues)`
The brain scan, now two-level: one line per tissue (collective health), indented lines per member cell.

### `main()`
Builds the three Tissues and runs the same command loop as before (`health`, `good`/`bad`, `quit`).

---

## The tests — what the 41 new checks prove

`tests/test_tissues.py` (33 tests) plus additions to `test_cells.py` (8 tests):

- **The new math** behaves: weights sum to 100%, confident members get more say, the triage bands sit exactly at 0.7 / 0.4.
- **BaseTissue keeps its promises**: rejects non-cells and duplicate names, routes only to accepting members, errors loudly when nobody accepts, combines confidence to the exact predicted number (0.734 for members at 0.85 and 0.50), and lets one failing *critical* cell drag the whole tissue to `failing` while a non-critical one only pulls the average.
- **Each concrete Tissue** does its specialty: LanguageTissue hands cleaned text from cell to cell; MemoryTissue merges notebooks, deduplicates identical facts, and honors `top_k` after merging; LearningTissue's running score follows the moving-average formula to the decimal.
- **ResponseCell** gives the exact honest confidences from its table above.
- **The Phase 2 success criterion** has a named test: input → IntentCell → MemoryCell → ResponseCell, teaching photosynthesis and getting it back "From memory" with real confidence.
