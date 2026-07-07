"""SpeechOrgan — the brain's Ear and Mouth (Design_Doc §12.8).

Wraps an Ear and a Mouth provider in Cells so speech gets health tracking
and learning like every other capability. Defaults are dependency-free and
safe everywhere: a TypedEar (keyboard) and a SilentMouth (echo) — matching
the design doc's speech-disabled-by-default configuration.
"""

from incortex.cells.ear_cell import EarCell
from incortex.cells.mouth_cell import MouthCell
from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.speech import SilentMouth, TypedEar

CAPABILITIES = (
    "speak", "say", "listen", "hear", "voice", "audio",
    "loud", "quiet", "sound", "pronounce",
)


class SpeechOrgan(BaseOrgan):
    def __init__(self, name="speech_organ", ear=None, mouth=None):
        super().__init__(name, capability_keywords=CAPABILITIES)
        self._ear_cell = EarCell(ear or TypedEar())
        self._mouth_cell = MouthCell(mouth or SilentMouth())
        self.add_cell(self._ear_cell, critical=True)
        self.add_cell(self._mouth_cell, critical=True)

    def hear(self, audio=None):
        """Listen once and return the transcript with its confidence."""
        output = self._ear_cell.process({"audio": audio})
        return self._wrap(output)

    def say(self, text):
        """Speak one reply aloud (or echo it, with a SilentMouth)."""
        return self._wrap(self._mouth_cell.process({"text": text}))

    def process(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        action = message.get("action")
        if action == "hear":
            return self.hear(message.get("audio"))
        if action == "say":
            return self.say(message.get("text"))
        raise ValueError(f"{self.name}: action must be 'hear' or 'say'")

    def _wrap(self, cell_output):
        return OrganOutput(
            organ_name=self.name,
            content=cell_output.content,
            confidence=cell_output.confidence,
            stage_outputs=(cell_output,),
        )
