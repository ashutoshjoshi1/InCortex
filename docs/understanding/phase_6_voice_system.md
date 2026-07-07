# Understanding Phase 6 — The Voice System

This document explains **every function built in Phase 6 in plain language**, continuing the series ([Phase 1](phase_1_cell_system.md) · [Phase 2](phase_2_tissue_system.md) · [Phase 3](phase_3_organ_system.md) · [Phase 4](phase_4_cortex_core.md) · [Phase 5](phase_5_memory_learning.md)). Equation references point into [math_model.md](../math_model.md).

Phase 6 gave the brain an **Ear and a Mouth** — and one genuinely new piece of math: *hearing has a confidence too*. A transcript the ear isn't sure about is asked to repeat itself before the brain is ever bothered.

---

## The Big Picture

The design goals for this phase pulled in opposite directions: real speech needs heavy libraries (Whisper models are gigabytes), but this project's zero-dependency discipline has been a feature since Phase 1. The resolution:

- **The Mouth works today, dependency-free.** macOS ships a `say` command (Linux has `espeak`); the `SystemVoiceMouth` shells out to it — a "System voice API" straight from the design doc's own §12.8 list. Run `python scripts/run_voice.py` on a Mac and the replies are *actually spoken aloud*.
- **The Ear is a contract with three providers.** A `TypedEar` (the keyboard "transcribes" at confidence 1.0 — keyboards don't mumble) makes the loop usable immediately; a `ScriptedEar` makes it testable; and a `WhisperEar` does real audio transcription the moment `openai-whisper` is installed (`pip install openai-whisper` — declared as the project's first *optional* dependency). Live microphone capture is left as a later refinement, honestly noted.
- **Defaults mirror the design doc's config** (§24: speech disabled by default): a bare `SpeechOrgan()` types and echoes; audio is opt-in.

---

## `speech/ear.py` — the Ear

### `Transcript` (a frozen record)
What an ear heard: the text, a **confidence** in 0–1 (the same convention every score in this project follows), and which provider heard it. Empty text is allowed (silence happens); bad confidences and blank sources are not.

### `BaseEar.listen(audio=None)`
The contract every ear implements. One extra rule: an ear signals "the conversation is over" (hang-up, end of input) by raising `EOFError` — the loop treats that as a polite goodbye, never a crash.

### `ScriptedEar`
Replays a fixed list of transcripts, then hangs up. Plain strings become full-confidence transcripts; explicit `Transcript` objects let a test inject a mumble. This is how the whole voice loop is tested deterministically.

### `TypedEar`
The dependency-free default: reads a line from the keyboard and wraps it as a transcript with confidence 1.0. Ctrl-D (end of input) raises `EOFError` naturally — a hang-up for free.

### `WhisperEar`
Real speech-to-text via OpenAI's Whisper, with three careful behaviors:

1. **Lazy loading** — the heavy model is only imported and loaded on first use, and if the library isn't installed the error says exactly how to fix it (`pip install openai-whisper`). The importer is injectable, so tests exercise both paths without Whisper present.
2. **Honest confidence from real math** — Whisper reports each segment's mean token *log-probability*. Exponentiating the average turns it back into a probability: a crisp recording scores near 1, a mumbled one genuinely lower (the test pins exp(−0.223) ≈ 0.80). No segments → a neutral 0.5, the same "no evidence either way" convention as a newborn Cell.
3. **Audio files only for now** — calling it without a path explains that microphone capture is a later refinement rather than pretending.

---

## `speech/mouth.py` — the Mouth

### `Utterance` (a frozen record)
What a mouth said: the text, whether it was *actually spoken* as audio (the SilentMouth echoes instead), and through which engine.

### `BaseMouth.speak(text)`
The contract: return an `Utterance`, or raise — a mouth never silently fails to speak.

### `SilentMouth`
Prints `(spoken) …` instead of making sound. This is the CI-safe, test-safe, annoy-nobody default — and what the demo uses so running it doesn't make your laptop suddenly talk.

### `SystemVoiceMouth`
The real one. On construction it finds the platform's voice command (`say`, `espeak`, or `spd-say`, checked in that order) and fails loudly with advice if none exists. `speak(text)` runs the command (macOS voices selectable via the `voice` option), converts any subprocess failure into a clear error, and returns a spoken-for-real `Utterance`. The command runner and the command finder are both injectable, so every path is tested without producing audio.

---

## The new Cells

### `cells/ear_cell.py` — `EarCell`
An ear wearing the standard Cell contract. The crucial line: **the transcript's confidence becomes the cell's raw confidence**, so hearing enters the same mathematical world as every other stage — blended with the cell's track record (Eq 1.6), degrading chains it joins (Eq 3.1). A fresh cell hearing a perfect transcript reports 0.85 (0.7·1.0 + 0.3·0.5), exactly like every other newborn cell.

### `cells/mouth_cell.py` — `MouthCell`
A mouth wearing the Cell contract — this is the design doc's own "SpeechCell: convert response to voice" (§9.1). Speaking either works or raises, so confidence is 1.0 and failures land in the cell's error count like any other crash.

---

## `organs/speech_organ.py` — the Speech Organ

### `SpeechOrgan(ear=None, mouth=None)`
Wraps the two cells (both critical — an organ that can't hear *or* can't speak is failing) around any ear/mouth providers. Defaults: `TypedEar` + `SilentMouth`.

### `hear(audio=None)` / `say(text)` / `process(message)`
Listen once; speak once; or dispatch a `{"action": "hear"/"say"}` message. Everything returns the standard `OrganOutput`, and health rolls up through `health_check()` like every other organ.

---

## `interfaces/voice.py` — the conversation loop

### `VoiceInterface(core, speech, output=print)`
Ties one brain to one speech organ. The `output` callback prints the bracketed status lines (`[heard … | listen confidence 0.85]`) — informational only, injectable so tests run silent.

### `run()` / `run_once()`
The design doc's speech flow (§12.8), one turn at a time:

1. **Listen.** A hang-up (`EOFError`) → speak the farewell, end.
2. **Skip silence.** Empty transcripts don't wake the brain.
3. **Quit words** ("goodbye", "stop", …, punctuation ignored) → farewell, end.
4. **The listen gate** — the new math: if the heard confidence is below **0.4** (deliberately the same floor as the Cortex's answer-acceptance rule, Eq 4.4), speak *"I didn't catch that clearly — could you say it again?"* and loop. The test proves the brain is never invoked: zero tasks handled after a mumble.
5. **Think.** `core.handle(text)` — everything from Phases 1–5.
6. **Report the full chain** — listening confidence composed with the brain's chain confidence via the geometric mean (Eq 3.1): now the *complete* pipeline from ear to answer carries one number.
7. **Speak the reply.**

---

## Launchers and demo

### `scripts/run_voice.py`
The real thing on a Mac: persistent brain (same builder as the CLI — memory survives between voice sessions too), `TypedEar`, and `build_mouth()` which tries the system voice and gracefully falls back to the echoing mouth with an explanation. Type to talk; replies are spoken aloud.

### `examples/voice_demo.py`
The whole loop with zero hardware: a scripted four-line conversation (teach → ask → **a deliberate mumble** → goodbye) through a printing mouth. Watching it run shows every Phase 6 behavior in ten lines of output, including the mumble being asked to repeat.

---

## The tests — what the 36 new checks prove

`tests/test_speech.py`:

- **Envelopes validate** (bad confidences, blank sources/engines rejected; empty transcript text allowed — silence is real).
- **Ears behave**: scripted order and hang-up-on-empty; typed trimming; Whisper's log-probability math to three decimals; the neutral 0.5 with no segments; the install hint when the dependency is missing; lazy loading through the injected importer.
- **Mouths behave**: the exact command lines (`["say", "hello world"]`, voice flags included) captured by fake runners; auto-detection walking the candidate list; loud failure when no command exists anywhere; empty text rejected.
- **The organ** wires both cells (0.85 blend confirmed), dispatches, reports both cells in its health.
- **The loop**: a full spoken conversation (taught → answered from memory → farewell last); the **mumble test** — repeat prompt spoken, brain untouched; quit words, hang-ups, and silence all handled; and the listen threshold pinned to the Eq 4.4 floor.
- **The Phase 6 success criterion** has a named test: a speech-sourced transcript in, a spoken reply out.
