# Understanding Phase 8 — The Development Organ

This document explains **every function built in Phase 8 in plain language**, continuing the series ([Phase 1](phase_1_cell_system.md) · [Phase 2](phase_2_tissue_system.md) · [Phase 3](phase_3_organ_system.md) · [Phase 4](phase_4_cortex_core.md) · [Phase 5](phase_5_memory_learning.md) · [Phase 6](phase_6_voice_system.md) · [Phase 7](phase_7_tool_system.md)).

Phase 8 built the organ that lets InCortex **help develop itself** — read its own codebase, understand bug reports, run its own tests, propose fixes as proper diffs, and bundle them into pull-request drafts. All of it under the design doc's iron rule (§12.10): *InCortex may suggest changes to itself, but it must not approve or merge its own changes.*

---

## The Big Picture

The safe self-development rule is enforced three different ways, layered:

1. **Structurally** — the DevelopmentOrgan simply *has no merge method*. Not a blocked one; an absent one. A test asserts `hasattr(organ, "merge")` is false. You cannot call what does not exist.
2. **Through the gate** — everything action-like rides Phase 7's machinery: reading code is level 1 (no ceremony), running tests is **level 4** (code execution — a real human must say yes at the terminal), GitHub issue creation is level 3 (locked behind the ceiling until configuration raises it). Asking the gate directly about `merge_pull_request` at level 5 sends it to a human, per Eq 7.2.
3. **In the paperwork** — every PR draft's body ends with a fixed note: *"A human must review and merge it — InCortex cannot and will not merge its own changes,"* plus a review checklist.

No new math this phase — it's the Phase 7 gate math applied to a new domain, plus the Phase 5 learning loop fed from a new source: **failed tests become learning events.**

---

## `tools/dev_tools.py` — three new gated abilities

### `ListProjectFilesTool` (level 1)
The codebase inventory: walks the project root and returns every source file (`.py`, `.md`, `.toml`, …) with its size. Three disciplines: hidden directories and `__pycache__` are skipped (noise, and often secrets live in dotfiles); an optional `subdir` narrows the listing but is sandbox-checked exactly like Phase 7's file paths (a `../elsewhere` is rejected at validation); and a file cap (default 500) with an explicit `truncated` flag — the tool never silently pretends a huge repository is small.

### `TestRunnerTool` (level 4)
Runs `pytest` on the project in a **separate process** with a hard timeout. Level 4 because running a test suite *is* running code — the design doc's always-ask-a-human tier.

The subtle design decision: **test failures are data, not errors.** Exit code 0 (all passed) and exit code 1 (some tests failed) both come back as *successful tool executions* carrying `{passed, failed, exit_code, tail}` — because the whole point (§12.10: "learn from failed tests") is to *read* the failures. Only a genuinely broken invocation (collection errors, bad arguments, timeout) becomes a tool failure. The output includes the last five lines of pytest's report for human eyes.

### `CreateGitHubIssueTool` (level 3)
The first real GitHub integration: POSTs an issue to `api.github.com` with a bearer token. Guards: the repo must look like `owner/name`, a missing token fails at *validation* (before any network), and the HTTP transport is injectable — tests verify the exact URL, headers, and JSON payload without touching the network. Level 3 means it is **blocked by default** (above the permission ceiling), exactly like Phase 7's `api_get`: unlocking it is a deliberate configuration act, not a persuasion problem.

---

## `organs/development_organ.py` — the developer

### `DevelopmentOrgan.__init__(project_root, tools, approver, learning, clock)`
Assembles its own gated toolbox by default: a `ToolOrgan` holding `read_file` (Phase 7's sandboxed reader, rooted at the project), `list_project_files`, and `run_tests` — wired to whatever approver you provide (deny-all if none: unattended means nothing risky runs). Optionally takes a `LearningOrgan` so test outcomes feed the learning loop. Runs in min-confidence mode, and its health rides on the gate cell, like the ToolOrgan itself.

### `read_file(path)` / `list_files(subdir=None)` — gated reading
Thin passthroughs to the toolbox: every read of the codebase goes through the gate and lands in the safety decision log. Level 1, so they execute without ceremony — but they are *logged* ceremony-free actions, not ungated ones.

### `run_tests(args="")` — gated execution that teaches
Invokes the test runner through the gate (so a human approves or it doesn't happen), then — the learning hook — if a LearningOrgan is attached and the run executed: a **failing suite is scored as a failed task** (`success=False`, with a description like `"test run 'test_bad.py': 0 passed, 1 failed"`), landing in the learning log and the mistake tracker; a passing suite is scored as a success. Repeated failures of the same kind will cluster and eventually escalate into a remembered weakness — the Phase 5 machinery, fed by development activity. This is the design doc's §16.4 self-learning development loop, running.

### `analyze_issue(title, body="")` — the issue analyzer
Pure computation (nothing to gate). Three steps:

1. **Classify** the issue by keyword families: bug (crash, error, broken…), feature (add, support, implement…), docs (readme, documentation, typo…), test (coverage, flaky…). No match → an honest `"unknown"` at confidence 0.3, versus 0.8 for a clear classification.
2. **Spot file mentions** — a pattern that finds paths like `pkg/math_utils.py` in the text, so the organ knows where to look first.
3. **Plan first steps** — a checklist that always starts with reading the mentioned files (or listing the project if none), then running the tests for a baseline; bugs additionally get "write a failing test that reproduces it" (the TDD discipline this very project is built with); and every plan ends with "suggest a patch and draft a pull request *for human review*."

### `suggest_patch(file_path, find, replace, description)` — the patch suggester
The heart of the phase. Reads the current file **through the gate**, locates the `find` text, and produces a **unified diff** — the standard `--- a/… / +++ b/… / -old / +new` format every code-review tool understands, generated with Python's own `difflib`. The draft (id, file, description, diff, timestamp) is accumulated on the organ for the next PR.

Two honesty guarantees, both tested: **the file itself is never touched** (suggesting is not applying — the test reads the file afterward and finds it unchanged), and a `find` text that doesn't exist returns a clear refusal (`patch: None`, error message) rather than a fabricated diff. An unreadable file likewise refuses instead of crashing.

*(Scope note: the find/replace mechanism is deliberately mechanical — the intelligence that decides* what *to change plugs in later as a model-backed cell. The contract — read gated, diff drafted, file untouched — will not change.)*

### `draft_pull_request(title, description="")` — the PR drafter
Bundles every accumulated patch into a draft: a branch name (`incortex/fix-float-handling-in-add` — slugified, prefixed so InCortex branches are recognizable), and a generated body — the phase's "documentation writer" duty — containing the description, a per-patch summary list, a review checklist, and the fixed human-must-merge note. Status is `"draft"` and there is nothing that can change it to anything else. Drafting with no patches accumulated is refused with a clear error.

### `process(message)` — dict dispatch to `analyze_issue`, for parity with every other organ.

### `_patch_refusal` / `_rewrap` (internal)
The refusal builder and the envelope converter (tool output → this organ's `OrganOutput`).

---

## `examples/dev_demo.py` — the loop, watchable

Builds a throwaway miniature project in a temp directory, then runs the whole story with **you as the human in the loop**: issue analyzed (classified `bug`, file spotted, four steps planned) → code read → tests run *after the terminal asks your permission* → a real unified diff suggested → a PR drafted whose body ends with the merge note — and a final printed proof: `merge method on the organ? False`.

---

## The tests — what the 43 new checks prove

`tests/test_development.py`:

- **The inventory tool** lists real files with sizes, skips caches and dotfiles, narrows by subdir, refuses sandbox escapes, and flags truncation honestly.
- **The test runner** reports exact pass/fail counts; a failing suite comes back as *data* (the learning loop depends on it); a nonsense invocation is a real failure; the timeout kills a 30-second sleep at 2 seconds; level pinned at 4.
- **The GitHub tool** POSTs the exact URL, bearer header, and JSON payload (captured by a fake transport); refuses to run without a token; validates the repo shape; level pinned at 3.
- **The analyzer** classifies all four issue types plus the honest unknown, extracts file mentions, and always proposes concrete first steps.
- **The patch suggester** produces a structurally correct unified diff (the `-`/`+` lines are asserted verbatim), never modifies the file, and refuses cleanly on missing text or unreadable files.
- **The PR drafter** collects patches, generates the branch name and body (merge note asserted), and refuses empty drafts.
- **The iron rule, three ways**: no `merge` attribute exists; `merge_pull_request` at level 5 goes to a human; and running tests is denied under a refusing approver and executes only under a granting one.
- **Learning from tests**: a failing run lands in the learning log as a failure and clusters in the mistake tracker; a passing run lands as a success.
- **The Phase 8 success criterion** has a named test — the full loop: analyze → read → test (approved) → patch → draft PR → and no merge exists.
