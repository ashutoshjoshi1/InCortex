"""The Mouth — text-to-speech providers (Design_Doc §12.8).

- SystemVoiceMouth — the platform's built-in voice command (macOS `say`,
  Linux `espeak`/`spd-say`): real spoken audio with zero dependencies
- SilentMouth      — echoes instead of speaking (CI, tests, quiet mode)
"""

import shutil
import subprocess
from dataclasses import dataclass

VOICE_COMMANDS = ("say", "espeak", "spd-say")


@dataclass(frozen=True)
class Utterance:
    """What a mouth said, and through which engine."""

    text: str
    spoken: bool
    engine: str

    def __post_init__(self):
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("utterance text must be a non-empty string")
        if not isinstance(self.spoken, bool):
            raise ValueError("utterance spoken flag must be a bool")
        if not isinstance(self.engine, str) or not self.engine.strip():
            raise ValueError("utterance engine must be a non-empty string")


class BaseMouth:
    """Contract: speak(text) -> Utterance. Raise on failure, never swallow."""

    def speak(self, text):
        raise NotImplementedError


class SilentMouth(BaseMouth):
    """Echoes what it would have said — for CI and audio-free environments."""

    def __init__(self, printer=print):
        self._printer = printer

    def speak(self, text):
        self._printer(f"(spoken) {text}")
        return Utterance(text=text, spoken=False, engine="silent")


class SystemVoiceMouth(BaseMouth):
    """Speaks through the operating system's own voice command."""

    def __init__(self, command=None, voice=None,
                 runner=subprocess.run, which=shutil.which):
        self._command = command or self._find_command(which)
        self._voice = voice
        self._runner = runner

    @staticmethod
    def _find_command(which):
        for candidate in VOICE_COMMANDS:
            if which(candidate):
                return candidate
        raise RuntimeError(
            f"no system text-to-speech command found (tried {VOICE_COMMANDS}); "
            f"use SilentMouth instead"
        )

    def speak(self, text):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("cannot speak empty text")
        argv = [self._command]
        if self._voice and self._command == "say":
            argv += ["-v", self._voice]
        argv.append(text)
        try:
            self._runner(argv, check=True)
        except Exception as error:
            raise RuntimeError(f"{self._command} failed to speak: {error}") from error
        return Utterance(text=text, spoken=True, engine=self._command)
