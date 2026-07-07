# `speech/` — Ear and Mouth Device Adapters

The speech-to-text and text-to-speech providers behind the Speech Organ (Design_Doc §12.8). Providers are swappable behind two tiny contracts; confidence follows the §0 convention (every score in [0, 1]).

Modules:

- `ear.py` — ✅ `Transcript`, `BaseEar`, `ScriptedEar` (tests/demos), `TypedEar` (dependency-free default), `WhisperEar` (real audio via the optional `voice` extra; confidence = exp(mean log-probability))
- `mouth.py` — ✅ `Utterance`, `BaseMouth`, `SilentMouth` (echo, CI-safe), `SystemVoiceMouth` (macOS `say` / Linux `espeak` — real audio, zero dependencies)

Planned providers: microphone capture, Vosk/Deepgram ears, Piper/Coqui mouths (§12.8 lists the candidates).

**Status:** Phase 6 implemented with 100% test coverage (`tests/test_speech.py`). Plain-language walkthrough: [docs/understanding/phase_6_voice_system.md](../../docs/understanding/phase_6_voice_system.md).
