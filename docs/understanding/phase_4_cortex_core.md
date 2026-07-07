# Understanding Phase 4 — The Cortex Core

This document explains **every function built in Phase 4 in plain language**, continuing the series ([Phase 1](phase_1_cell_system.md) · [Phase 2](phase_2_tissue_system.md) · [Phase 3](phase_3_organ_system.md)). Equation references point into [math_model.md](../math_model.md).

Phase 4 built the **Cortex Core** — the brain's coordinator. It does no thinking of its own: it decides *which departments* (Organs) handle each request, watches the confidence of every step, refuses to give answers it cannot stand behind, and writes everything it does into an activity log.

---

## The Big Picture

Until now, someone outside the system (the CLI script, a test) had to know the flow: "first understand, then retrieve, then reason, then respond." Phase 4 moves that knowledge *inside* the brain. You hand the Cortex a sentence; it does the rest:

```text
receive → understand → route to the right Organs → consult memory →
reason over evidence → safety-gate any writes → respond →
accept or ask for clarification → log everything → learn from feedback
```

Two guardrails are new and worth seeing in action:

1. **The answer-acceptance rule** *(Eq 4.4)*: an answer is only given if the whole chain's confidence clears 0.4. In Phase 3, asking about *dark matter* after teaching photosynthesis produced a misleading "From memory (score 0.47)" answer. Now reasoning notices the evidence doesn't cover the question, the evidence is discarded, the chain confidence collapses to 0.33, and the Cortex says: *"I'm not confident enough to answer that. Could you rephrase, or teach me more about it first?"* The math now prevents bad answers instead of just measuring them.
2. **A fixed equation.** While implementing the scheduler we found a contradiction in our own math spec: Eq 4.3 capped the "age" term of a task's priority, but §11 property 8 promised that no waiting task ever starves. A capped bonus can't keep that promise — a stream of urgent tasks would starve an old one forever. The math doc was amended (the cap is gone) and the code implements the corrected equation. The spec records the amendment.

---

## `message.py` — the envelope and the postal service

### `CortexMessage` (a frozen record)
The standard envelope every internal communication travels in *(Design_Doc §14.1)*: a unique id, session id, source and target, a **message type** from the fixed 15-word vocabulary (`user_input`, `memory_result`, `safety_check`…), the payload, a priority, an optional confidence, and a timestamp. Its birth-time validation rejects unknown types, bad priorities, and out-of-range confidences — and, like all outputs in this project, an envelope can never be altered after it is sealed.

### `new_message(source, target, message_type, payload, ...)`
The stamp machine: builds a validated message with a freshly generated unique id and the current time (clock injectable for tests).

### `MessageBus`
The postal service, and simultaneously the **brain activity log** *(Design_Doc §17)*:

- **`subscribe(message_type, handler)`** — "call me whenever a message of this type is sent." Refuses unknown types and non-callable handlers.
- **`publish(message)`** — records the message in history, then delivers it synchronously to every subscriber of its type; returns how many handlers got it.
- **`history(count=None)`** — the recent traffic, oldest first, bounded (default: last 200). This is what the CLI's new `log` command prints: you can watch the organs talking to each other.

---

## `router.py` — the dispatcher

### `Router.register(organ, intents=())`
Adds an organ to the routing table and records which **intents it serves** (memory serves teach/remember/explain; reasoning serves explain; language serves everything). Type-checked, duplicate-name-checked.

### `Router.route(text, intent=None)` *(Eq 4.2)*
For each organ, relevance is the *stronger* of two signals:

- its **keyword relevance** to the message text (the Phase 3 `relevance()` method), and
- its **intent affinity**: a full 1.0 if the organ serves the detected intent.

Every organ scoring at or above the threshold (0.35) is selected. If *nobody* passes — say the message is pure gibberish — the single best-scoring organ is drafted anyway, because something must always answer; the decision records that this fallback happened. The returned `RoutingDecision` carries the selected organs, all the scores (for logging), and the fallback flag.

This is why a chat greeting only wakes the Language Organ, while "What is photosynthesis?" wakes Language, Memory, and Reasoning together.

---

## `scheduler.py` — the waiting room

### `Scheduler.submit(payload, urgency, importance)`
Queues a task. Urgency can be a number 0–1 or a named priority ("low" 0.2, "normal" 0.5, "high" 1.0). Both knobs validated.

### `Scheduler.priority(task)` *(Eq 4.3, as amended)*
A task's priority = **50% urgency + 30% importance + 20% × (how long it has waited ÷ 60s)** — recomputed live at every pop, so a waiting task keeps climbing. The age term is deliberately *uncapped*: wait long enough and any task outranks any fixed urgency. Concretely (and tested): a low-urgency task that has waited 150 seconds beats a brand-new high-urgency one, 0.75 to 0.65. That's the no-starvation guarantee — like a bakery ticket queue where your number gets louder the longer you hold it.

### `Scheduler.pop()`
Removes and returns the highest-priority task; ties go to the *older* task (fairness). Popping an empty queue is an error, never a silent `None`.

*(Today the Cortex handles one request at a time, so each request is submitted and immediately popped — the queue is the prepared seam for the multi-tasking that tools and async work will need in later phases.)*

---

## `state.py` — the case file and the scoreboard

### `TaskContext` (a mutable record — deliberately)
The **case file** for one request, filled in as the request travels: the raw and cleaned text, the detected intent, every stage's name and confidence, which organs took part, the memory results used, the final reply, the chain confidence, and whether the answer was accepted. Unlike the frozen output envelopes, this is a workspace — it accumulates.

- **`add_stage(name, confidence)`** — record one step (confidence clamped to 0–1).
- **`use_organ(name)`** — note a participant, without duplicates. Feedback later uses exactly this list to decide who gets taught.
- **`chain()`** — the geometric-mean confidence across all recorded stages *(Eq 3.1)* — the number shown after every CLI reply.

### `SystemState`
The long-running **scoreboard**:

- **`record_task(context)`** — counts tasks, tracks the acceptance rate, smooths chain confidence into a running average *(Eq 1.7; the first sample seeds it)*, and remembers each session's most recent case file.
- **`record_learning(score)`** — same smoothing for learning scores: "is the brain improving lately?"
- **`last_context(session_id)`** — the case file feedback needs ("what did we just do for this user?").
- **`snapshot()`** — tasks handled, acceptance rate, both moving averages, session count. Printed by the CLI's `health` command.

---

## `cortex.py` — the coordinator itself

### `CortexCore.__init__(...)`
Assembles the brain: five organs (Language, Memory, Reasoning, Learning, Safety — each replaceable, which is how tests inject a stricter safety organ), a MessageBus, a SystemState, a Scheduler, and a Router pre-registered with each organ's served intents.

### `handle(text, session_id="default")` — one full trip through the loop *(Eq 4.1)*
1. Wrap the input in a `user_input` message, publish it, pass it through the scheduler.
2. Open a `TaskContext` case file.
3. **Understand** — Language Organ cleans and classifies; stage recorded.
4. **Route** *(Eq 4.2)* — the Router picks the organ set from relevance + intent.
5. **Consult memory** (if routed) — see `_consult_memory` below.
6. **Reason** (if routed) — see `_consult_reasoning` below.
7. **Respond** — the Language Organ writes the reply from intent + surviving evidence (unless the safety gate already spoke).
8. **Accept or clarify** *(Eq 4.4)* — chain confidence ≥ 0.4 → the reply stands; below → it is replaced by an honest clarification request quoting the confidence.
9. Publish the final `system_event` (carrying the chain confidence), record the case file in SystemState, return it.

### `_consult_memory(context, routed, session_id)` (internal)
For teach/remember: before anything is written, the **Safety Organ gates the store** ("store_memory", level 2, low estimated risk — a permission check on every write, per §13.1 step 8). If the gate says anything but execute, nothing is stored and the user is told which decision the gate made — that refusal is a *confident* stage, not a failure. If cleared, the fact is stored and a `memory_result` published. For explain: retrieve, record the stage, publish.

### `_consult_reasoning(context, routed, session_id)` (internal)
Runs the Reasoning Organ over the retrieved evidence and — the important part — **discards the evidence if reasoning says it cannot support an answer**. This is what turns Phase 3's spurious word-overlap answer into Phase 4's honest clarification: bad evidence never reaches the response writer.

### `feedback(success, rating=None, session_id="default")`
Finds the session's last case file, gathers the cells of **exactly the organs that took part** (a teach flow teaches language + memory cells but not reasoning — it wasn't there), sends the event through the Learning Organ, smooths the score into SystemState, and publishes `feedback_event` + `learning_update`. Refuses to rate when nothing has been asked yet.

### `health_check()`
The whole brain in one report: all five organs (each recursively down to cells) plus the system snapshot.

### `_publish(...)` (internal)
The one place messages are stamped and sent — every step of `handle` and `feedback` goes through it, which is why the activity log is complete.

---

## `scripts/run_cli.py` — now a thin shell

The CLI no longer knows how the brain works — `main()` just forwards text to `core.handle()` and prints `context.reply` with its chain confidence. `print_health(core)` renders the four-level report (organ → tissue → cell + the system scoreboard line). New **`log`** command: `print_log(core)` prints the recent bus history — message type, who → whom, confidence, payload preview — so you can literally watch the organs converse.

---

## The tests — what the 46 new checks prove

`tests/test_core.py`:

- **CortexMessage** validates its envelope (unknown types, bad priorities, out-of-range confidence, blank fields) and is truly immutable.
- **MessageBus** delivers only to matching subscribers, logs everything, and its history is bounded and ordered.
- **Router** selects exactly {language, memory, reasoning} for an explain question, only language for a chat greeting, routes by keyword alone when no intent is given, and drafts the best organ (flagged) when nothing passes.
- **Scheduler** hits the formula to the decimal (0.5·0.4 + 0.3·0.6 + 0.2·(30/60) = 0.48), and the landmark **no-starvation test**: an ancient low-urgency task beats a fresh high-urgency one 0.75 to 0.65 — the test the original capped equation could never pass.
- **TaskContext / SystemState**: the chain reproduces the 0.545 worked example; moving averages seed-then-smooth exactly (0.8 then 0.4 → 0.76); sessions keep separate case files.
- **CortexCore**: teach and explain flows use the right organs in the right order; the dark-matter question fails the acceptance gate and gets the clarification; misleading evidence is discarded; a blocklisted store is refused with the memory genuinely untouched; feedback reaches exactly the participants (reasoning excluded from a teach flow); the full brain-activity trail lands on the bus; and the final message carries the chain confidence.
- **The Phase 4 success criterion** has a named test: the design doc's MVP demo conversation, end to end, through the Cortex.
