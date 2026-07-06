# Understanding Phase 1 — The Cell System

This document explains **every function built in Phase 1 in plain language** — no code reading required. It is written for anyone who wants to understand *what* each piece does and *why* it exists. When you want the exact formulas, follow the equation references into [math_model.md](../math_model.md).

> **Convention:** every completed phase gets a document like this one in `docs/understanding/`.

Phase 1 built the **Cell** — the smallest intelligent unit in InCortex, like a single neuron in a brain. Five files of real code, one demo script, and 57 tests.

---

## The Big Picture

Every Cell, no matter its job, follows the same life cycle:

```text
receive input → process it → give an answer with a confidence →
accept feedback → report its own health
```

Two ideas run through everything below:

1. **Every answer carries a confidence between 0 and 1.** A Cell never just says "here's the answer" — it also says how sure it is.
2. **Every Cell keeps score on itself.** Wins, losses, errors, and speed all feed a health number, so the system can later notice when a part of the brain is struggling.

---

## `cell_math.py` — the shared pocket calculator

Small, pure math functions. "Pure" means: same input always gives the same output, and nothing else in the program changes. Every other file uses these.

### `tokenize(text)`
Chops a sentence into lowercase words. `"Hello, World!"` becomes `["hello", "world"]`. Punctuation is thrown away. This is how Cells compare texts — as bags of words.

### `clip01(value)`
A safety clamp. Whatever number comes in, what comes out is squeezed into the range 0 to 1. If a buggy calculation produces 1.7 or −0.3, this stops the nonsense from spreading. Rule of the house: every score that crosses a boundary is between 0 and 1.

### `softmax(scores, temperature)`
Turns a list of raw scores into **percentages that add up to 100%**. Higher scores get bigger shares. The `temperature` knob controls how bossy the top score is:

- **Cold** (small temperature): winner takes almost everything — near 100% to the best.
- **Hot** (large temperature): everyone gets a nearly equal slice.

InCortex uses a fairly cold 0.5, so a clear winner really dominates. *(Eq 1.3 / 2.1)*

### `entropy_confidence(probabilities)`
Measures how much a probability list has **made up its mind**. If one option holds all the probability → confidence 1 (certain). If every option is equally likely → confidence 0 (a pure shrug). Anything between lands between. This is how a classifier honestly reports "I know" vs "I'm guessing". *(Eq 1.4)*

### `ema_update(previous, sample, alpha)`
A **running average that cares more about recent events** (an "exponential moving average"). Think of your mood: it's mostly what it already was, nudged a little by what just happened. With `alpha = 0.1`, each new event pulls the average 10% of the way toward itself. Cells use this to track their recent success rate, confidence, and speed without storing every event. *(Eq 1.7)*

### `exponential_decay(elapsed, half_life)`
The **forgetting curve**. Returns a freshness value that starts at 1 and halves every `half_life` seconds — exactly like radioactive decay, and very close to how human memory fades. A memory stored 7 days ago (with a 7-day half-life) is worth 0.5; after 14 days, 0.25. *(Eq 5.2)*

### `jaccard_similarity(tokens_a, tokens_b)`
How similar are two texts? Count the words they **share**, divide by all the words they use **combined**. Identical word sets → 1. Nothing in common → 0. This is Phase 1's stand-in for real semantic similarity; Phase 5 will replace it with embedding vectors that understand meaning, not just spelling. *(stands in for Eq 5.1)*

---

## `base_cell.py` — the DNA every Cell shares

This file defines what it means to *be* a Cell. Every concrete Cell (text, intent, memory, feedback…) inherits all of this behavior for free.

### `CellOutput` (a frozen record)
The envelope every answer ships in: which cell produced it, what type it is, the actual content, the final confidence, and the raw confidence before blending. "Frozen" means it can never be modified after creation — an answer, once given, is history.

### `CellFeedback` (a frozen record)
The envelope for feedback a Cell can learn from: did the task succeed (required), an optional 0–1 rating, an optional note.

### `require_nonempty_text(cell_name, message)`
A shared doorman used by text-handling Cells: rejects anything that isn't a non-empty piece of text, with an error message that names the complaining cell.

### `BaseCell.__init__(name, cell_type)`
Birth of a Cell. Checks the name and type are real, then sets up the scoreboard:

- **Feedback counters** start at zero wins out of zero tries.
- **Success average starts at 1.0** — a newborn has no *observed* failures, and health is about noticing failures. Innocent until proven guilty.
- **Confidence average starts at 0.5** — trust must be *earned*. A newborn is honestly unsure.
- **Latency average starts at 0** — nothing measured yet.
- An empty inbox, no last answer, and a feedback log that keeps only the most recent 100 entries.

### `receive(message)`
Drops a message into the Cell's inbox after validating it. Like handing a letter to a worker who will open it when `process()` is called. Rejects `None` outright.

### `process(message=None)`
**The heartbeat of every Cell.** Step by step:

1. Use the message you were handed, or the one waiting in the inbox. Neither? Complain loudly.
2. Validate it (each Cell type defines what "valid" means for it).
3. Start a stopwatch and run the Cell's actual job (`_process` — written by each subclass).
4. **If the job crashes:** count the error, mark it as an observed failure (health drops), and let the crash propagate — no silent swallowing.
5. Clamp the job's raw confidence into 0–1.
6. **Blend confidences**: final confidence = 70% of this call's raw confidence + 30% of the Cell's lifetime track record. A cell that has been wrong a lot cannot suddenly claim to be sure. *(Eq 1.6)*
7. Update the running averages for confidence and speed, bump the processed counter, clear the inbox.
8. Wrap everything in a `CellOutput`, remember it, return it.

### `emit()`
Replays the last answer the Cell produced, or `None` if it has never worked. Useful when another component wants to look at the output again without re-running the job.

### `learn(feedback)`
How a Cell gets better (or admits it's worse). Takes feedback (an object or plain dict), validates it, then:

- adds a win or a loss to the lifetime record,
- nudges the recent success average up or down,
- stores the feedback in the bounded log,
- passes it to the subclass hook `_learn` in case that Cell wants to do something extra.

### `health_check()`
The doctor's report — a small dictionary:

| Field | Meaning |
| ----- | ------- |
| `name`, `type` | who is being examined |
| `status` | `active` / `degraded` / `failing` — the triage color |
| `health` | the underlying 0–1 score |
| `confidence` | lifetime track record (see below) |
| `processed`, `errors`, `feedback_count` | raw counters |

### `historical_confidence` (property)
The Cell's lifetime track record, computed as **(wins + 1) / (total + 2)**. This "rule of succession" has a lovely property: with no history it gives exactly 0.5 (a coin flip — honest ignorance), and 3 wins out of 3 gives 0.8, *not* 1.0, because a short winning streak is not proof of perfection. *(Eq 1.5)*

### `_health_score()` (internal)
Health = **50% recent success rate + 30% recent confidence + 20% speed**. Speed counts for less because a slow-but-correct cell is better than a fast-but-wrong one. *(Eq 1.8)*

### `_status(health)` (internal)
Converts the health number into a triage band: 0.7 and above is `active`, 0.4–0.7 is `degraded`, below 0.4 is `failing`. *(Eq 1.9)*

### `_coerce_feedback(feedback)` (internal)
The bouncer at the feedback door. Accepts a proper `CellFeedback` or a plain dict (which it converts), rejects everything else, and refuses ratings outside 0–1 or a success flag that isn't a real yes/no.

### The three subclass hooks
- `_validate(message)` — "what counts as a valid input for *my* job?" (default: anything non-None)
- `_process(message)` — "*do* my one job; return (content, raw confidence)". Every concrete Cell must write this.
- `_learn(feedback)` — "anything extra I want to do with feedback?" (default: nothing)

---

## `text_cell.py` — the text tidier

The first perception step: takes raw text and cleans it up for everyone downstream.

### `TextCell.__init__(name="text_cell")`
Registers itself as a cell of type `"text"`.

### `_validate(message)`
Only accepts non-empty text. Numbers, `None`, or a string of spaces are rejected at the door.

### `_process(message)`
Collapses messy whitespace (`"  hello   world "` → `"hello world"`), counts words and characters, and reports a confidence equal to **the fraction of chunks that look like words**. A normal sentence scores 1.0; a string of symbols like `"@# $% ^&"` scores 0 — the cell is telling you "this doesn't look like language to me."

---

## `intent_cell.py` — the "what do you want?" detector

Reads a sentence and decides which of four intents the user has: **teach** me something, **remember** this, **explain** something, or just **chat**.

### `INTENT_KEYWORDS` (the lookup table)
Each intent owns a handful of trigger words and phrases ("teach yourself", "i like", "what is", "hello"…). Phase 1 keeps this deliberately simple — the table is a placeholder for a real language model later, but the surrounding math won't change when that upgrade happens.

### `BASE_SCORE` (why every intent starts with 0.1)
Every intent begins with a small free score before counting keyword hits. Without this floor, a single keyword hit would look like absolute certainty. With it, one hit is strong evidence but not fanaticism.

### `IntentCell._process(message)`
1. Lowercase and tidy the sentence.
2. Score each intent: base score + number of its keywords found.
3. Run softmax (cold temperature) to turn scores into percentages.
4. The intent with the biggest share wins.
5. Confidence comes from entropy: clear keyword matches → high; no keywords at all → every intent equally likely → confidence ≈ 0, an honest "I have no idea."

The output includes the full distribution, not just the winner, so later layers can see the runner-ups.

### `_keyword_hits(text, keywords)` (internal)
Counts keyword matches carefully: multi-word phrases match anywhere, but single words must match as **whole words** — this is why "hi" never fires inside the word "this".

---

## `memory_cell.py` — the notebook

Stores facts and finds them again. Phase 1 keeps everything in a simple in-program list; Phase 5 swaps in real databases without changing the ideas.

### `MemoryEntry` (a frozen record)
One remembered fact: its text, its bag of words (pre-computed for fast comparison), how important it is (0–1), and the exact time it was stored.

### `MemoryCell.__init__(name, half_life_seconds, clock)`
Sets up an empty notebook. Two clever knobs:

- `half_life_seconds` — how fast memories fade (default: 7 days).
- `clock` — the source of "now". By default the real clock, but tests inject a fake one so they can **time-travel**: store a memory, jump 100 seconds forward, and check that fading works — deterministically, no waiting.

### `_validate(message)`
Memory messages are little instruction dicts. This checks the shape strictly: the action must be `store` or `retrieve`; a store needs real content; a retrieve needs a real query; importance must be 0–1; `top_k` (how many results you want) must be a positive whole number.

### `_process(message)`
A one-line dispatcher: store requests go to `_store`, retrieve requests to `_retrieve`.

### `_store(message)` (internal)
Writes the fact down: tokenizes it, stamps the current time, notes its importance, appends it to the notebook. Returns what was stored and the new count. Confidence is 1.0 — there is nothing uncertain about the act of writing something down.

### `_retrieve(message)` (internal)
The interesting one. For every memory in the notebook:

1. **Similarity** — how many words does it share with the query? If **zero**, skip it entirely: a fact with no overlap is never relevant, no matter how fresh or important.
2. **Recency** — run the forgetting curve on its age.
3. **Combine**: score = 60% similarity + 20% recency + 20% importance. *(Eq 5.4)*
4. Keep only scores above 0.25 — better to return nothing than to return junk.
5. Sort best-first (ties go to the newer memory), return the top k.

The Cell's confidence for the whole retrieval = the best result's score. Found nothing? Confidence 0 — the honest answer.

---

## `feedback_cell.py` — the report-card writer

Turns messy human feedback ("4 stars", "wrong, I had to fix it") into one clean **learning score** the rest of the brain can act on.

### `_validate(message)` and `_validate_rating(message)` (internal)
Strict shape checks: `success` must be a real yes/no; if a rating is given, its scale must make sense (minimum below maximum) and the rating must sit inside the scale; correction severity must be 0–1.

### `_process(message)`
1. **Normalize the rating** to 0–1 regardless of the original scale: 4 on a 1–5 scale becomes 0.75. *(Eq 6.1)*
2. If no rating was given, use success itself as the stand-in satisfaction signal.
3. **Combine into the learning score**: reward success (up to 0.4) and satisfaction (up to 0.4); subtract up to 0.3 for how much the user had to correct the answer, and 0.3 more if something actually failed (a tool broke, an unsafe action was attempted). Clamp to 0–1. *(Eq 6.2)*
4. Label the band: **high** (≥ 0.7 — keep doing this), **medium** (0.4–0.7 — useful but flawed), **low** (< 0.4 — learn from this mistake).

Its own confidence is always 1.0 because this is pure arithmetic — there is nothing to be unsure about.

---

## `scripts/run_cli.py` — the first conversation

A small command-line program that wires three Cells into a working loop, so Phase 1 is something you can *talk to*, not just test.

### `respond(intent_cell, memory_cell, text)`
The traffic director. Asks the IntentCell what the user wants, then:

- **teach / remember** → store the sentence in the MemoryCell and confirm.
- **explain** → search memory; answer from the best match (showing its score), or admit "I don't know that yet — teach me!"
- anything else → a friendly greeting.

### `give_feedback(cells, feedback_cell, success)`
Runs when you type `good` or `bad`. Every working Cell gets the feedback (their track records move), and the FeedbackCell computes the official learning score and band for display.

### `print_health(cells)`
The brain scan: one line per Cell showing status, health, confidence, and counters — the `health_check()` output made human-readable.

### `main()`
Builds the three Cells, greets you, and loops: read a line, handle the special commands (`health`, `good`/`bad`, `quit`), otherwise route it through `respond`. Ends politely on end-of-input.

---

## The tests — what 57 checks actually prove

`tests/test_cells.py` is organized so each group proves one promise:

- **Math helpers** behave at their extremes: softmax percentages always sum to 100%, certainty reads as 1 and total ignorance as 0, decay halves exactly on schedule.
- **The BaseCell contract** holds: newborn cells report honest 0.5 confidence, confidence blending matches the formula to the decimal, health only ever *falls* as failures pile up, crashes are recorded rather than hidden.
- **Each concrete Cell** does its one job on the exact MVP demo sentences.
- **Boundary guards**: every malformed input is rejected with a clear error instead of causing silent weirdness.
- **The Phase 1 success criteria** from the design doc each have a named test: receive ✓ process ✓ output ✓ learn ✓ report health ✓.
