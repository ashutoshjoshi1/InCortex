# Understanding Phase 7 — The Tool/Muscle System

This document explains **every function built in Phase 7 in plain language**, continuing the series ([Phase 1](phase_1_cell_system.md) · [Phase 2](phase_2_tissue_system.md) · [Phase 3](phase_3_organ_system.md) · [Phase 4](phase_4_cortex_core.md) · [Phase 5](phase_5_memory_learning.md) · [Phase 6](phase_6_voice_system.md)). Equation references point into [math_model.md](../math_model.md).

Phase 7 gave the brain **muscles** — the ability to actually *do* things: read and write files, search its own memory, run code, fetch URLs. And, more importantly, it built the discipline around them: **no tool ever runs without passing the safety gate, and the risky ones need a human to say yes.**

---

## The Big Picture

The design doc's muscle rule (§11) is blunt: *"The brain thinks. Muscles act. Muscles should not make deep decisions."* Phase 7 enforces that with a single choke point. Every tool invocation flows through one method — `ToolOrgan.invoke` — which checks, in order:

1. Is the tool registered and **enabled**?
2. The **safety gate** (the Eq 7.1–7.2 math from Phase 3, now with real consequences), fed the tool's own declared permission level and risk estimates.
3. If the gate says "require approval" — **ask an actual human**. The default approver denies everything, so an unattended brain never runs anything risky.
4. Only then: execute.

You can watch all four outcomes at the CLI: `write_file` executes silently (level 2, low risk), `run_python` prints a real `[approval] Allow 'run_python'? [y/N]` question at your terminal, `api_get` is blocked outright (level 3 is above the default ceiling — no human question, configuration simply forbids it), and a disabled tool is refused by the registry.

---

## `safety/approval.py` — the human in the loop

### `BaseApprover.request(action, reason)`
The contract: given an action and the gate's reason, return yes or no — and **log every decision** (action, reason, granted) in a bounded audit trail, exposed as the `decisions` property. Subclasses implement only `_decide`; the logging cannot be forgotten or bypassed.

### `DenyAllApprover`
The fail-closed default: always no. The reasoning mirrors the SafetyCell's worst-case defaults from Phase 3 — if nobody wired up a real approver, nobody is watching, and an unwatched brain should be granted nothing. Tests confirm a level-4 tool under the default approver is denied without ever executing.

### `CallbackApprover`
Delegates the question to any callable. The CLI wires it to a terminal prompt (`terminal_approver` in `run_cli.py`); a test wires it to a lambda; a future web UI would wire it to a confirmation dialog. Rejects non-callables at construction.

---

## `tools/base_tool.py` — the muscle fiber contract

### `ToolResult` (a frozen record)
The outcome of one execution: which tool, success or not, the output, and the error text if it failed. **Execution failures are captured into this record, never raised** — a broken tool must not crash the brain that used it.

### `BaseTool`
Every tool declares four class attributes the gate reads: `name`, `description`, `permission_level` (0–5), and its `harm_probability`/`impact` estimates (the Eq 7.1 inputs). The defaults are the phase's quiet masterstroke: **level 5, harm 1.0, impact 1.0** — an unconfigured tool is *maximally* restricted. Forgetting to classify a new tool locks it down; it never accidentally opens up.

- **`validate(request)`** — reject malformed requests loudly (a bad request is a caller bug, so it *raises*, unlike execution failures).
- **`execute(request)`** — the template: validate, run `_execute`, capture any failure into a `ToolResult`. One exception to the capturing: `NotImplementedError` propagates, because an unimplemented tool is a programming error, not a runtime failure.
- **`info()`** — the registry card: name, description, level, risk estimates.

---

## `tools/tool_registry.py` — the catalogue

### `ToolRegistry`
The §18.2 registry: `register` (real tools only, no duplicate names), `get` (unknown names are loud errors), `enable`/`disable`/`is_enabled` (a kill-switch per tool — the ToolOrgan refuses disabled tools before even reaching the gate), and `list_tools()` (the catalogue, name-sorted, each entry carrying its enabled flag — what the CLI's `tools` command prints).

---

## The four concrete tools

### `file_tools.py` — `ReadFileTool` (level 1) and `WriteFileTool` (level 2)
Both are **sandboxed**: constructed with a root directory, and `_resolve` enforces the wall — the requested path is resolved to its true location (undoing `../` tricks and symlink hops) and must still be inside the root, *checked at validation time before anything touches the filesystem*. `../outside.txt` and `/etc/passwd` are rejected with a "sandbox" error. Reading also refuses oversized files (default cap 1 MB); writing creates parent directories and reports bytes written. Their permission levels are taken verbatim from the design doc's ladder: read-only = 1, local safe write = 2 — both below the default ceiling, so they run without ceremony.

### `search_tools.py` — `SearchMemoryTool` (level 1)
The brain searching its own long-term memory as a *tool* — the same `MemoryManager.recall` from Phase 5, exposed through the tool contract so external callers get gated access too.

### `python_tool.py` — `RunPythonTool` (level 4)
The canonical always-ask-a-human tool (§12.9: code execution requires approval). Runs the snippet in a **separate interpreter process** — no shell, a hard timeout (default 5s), captured stdout/stderr. Timeouts and non-zero exits become captured failures with the stderr in the error text.

### `api_tool.py` — `ApiTool` (level 3)
HTTP GET with three guards: only `http://`/`https://` schemes (a `file:///etc/passwd` URL is rejected at validation), a response-size cap, and a timeout. Level 3 sits *above* the default ceiling (2) but *below* the always-ask tier (4) — so by default it is **blocked**, and the fix is not persuasion but configuration: raising the SafetyOrgan's ceiling to 3 unlocks it. The tests demonstrate both sides.

---

## `organs/tool_organ.py` — the muscle system

### `ToolOrgan.__init__(registry, safety, approver)`
Assembles the choke point: a registry, its own SafetyOrgan (whose gate cell becomes the organ's critical health-bearing cell), and an approver (default: deny-all). Runs in min-confidence mode — a tool chain is never more trustworthy than its weakest step.

### `invoke(tool_name, request)` — the single door
The four-step sequence from the Big Picture, with every decision path returning the same shaped content: `tool`, `decision` (`executed` / `approved_and_executed` / `denied` / `blocked` / `disabled`), `executed`, `success`, `output`, `error`. Notable details:

- The gate is fed **the tool's own declared** level and risk numbers — a tool cannot understate its danger without lying in its own class definition, which is visible in code review.
- A refusal has confidence **1.0** — refusing is a confident act (same principle as Phase 4's safety-gate stage).
- A tool that executed but failed gets confidence **0.2** — it acted, badly.
- Every invocation lands in the SafetyOrgan's decision log, approved or not.

### `_run` / `_refusal` / `_wrap` (internal)
The two outcome builders (execution vs. refusal) and the envelope-maker — all outputs are standard `OrganOutput`s.

### `process(message)`
Dict dispatch: `{"tool": name, "request": {...}}`, for parity with every other organ.

### One SafetyOrgan upgrade
`SafetyOrgan` now accepts `max_auto_level`, passing it to its gate cell — this is how a deployment consciously raises the ceiling (e.g. to 3, unlocking API calls) instead of editing constants.

---

## `scripts/run_cli.py` — muscles at the terminal

### `terminal_approver(action, reason)`
The human in the loop, literally: prints `[approval] Allow 'run_python'? (level 4 actions always require a human) [y/N]` and reads your answer. Only `y`/`yes` grants.

### `build_tools(memory_manager)`
The default muscle set: sandboxed read/write (rooted at `data/sandbox/`), memory search wired to the same persistent MemoryManager the brain uses, gated Python, and the (blocked-by-default) API tool.

### `parse_tool_command(text)` / `run_tool_command(core, text)`
The tiny command grammar: `tool run_python code=print(6*7)` (multiple arguments joined with `&`). Output shows the decision in brackets — `[executed]`, `[denied]`, `[blocked]` — so the gate's verdict is always visible.

### New commands in `main()`
`tools` lists the catalogue with levels and enabled flags; `tool <name> ...` invokes through the full gate. The smoke test showed the whole ladder in one session: write → read → search (found a memory persisted days earlier) → python denied → python approved (stdout `42`) → api blocked.

---

## The tests — what the 47 new checks prove

`tests/test_safety.py` — the file the design doc's test plan (§26.3) reserves for exactly this:

- **The tool contract**: successes and failures both become `ToolResult`s; validation raises; the fail-closed defaults are pinned (level 5, worst-case risk).
- **The registry**: duplicates and non-tools rejected, enable/disable respected, the catalogue lists accurately.
- **The sandbox holds**: traversal (`../`), absolute paths, and oversized files all refused; write-then-read roundtrips work; permission levels match the design doc's ladder.
- **Code execution is disciplined**: output captured, failures captured, the timeout enforced (a 5-second sleep killed at 0.5s), level pinned at 4.
- **The API tool**: fetches, refuses non-HTTP schemes, refuses oversized responses, level pinned at 3.
- **Approvers**: deny-all denies and logs; callback asks; the log is bounded; non-callables rejected.
- **The organ runs the full ladder**: safe tools execute without bothering anyone; level 4 is denied by default and runs only after a real yes; level 3 is blocked *even with a willing approver* (approval is never an option above the ceiling — only configuration is); raising the ceiling unlocks it; disabled tools refuse; blocklisted names stay blocked; every invocation is gate-logged.
- **The Phase 7 success criterion** has a named test: the same tool, denied then approved, with the human asked both times — *InCortex uses tools only after safety approval.*
