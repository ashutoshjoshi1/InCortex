"""EarCell — an Ear provider wearing the Cell contract.

The transcript's own confidence becomes the cell's raw confidence, so a
mumbled recording degrades every chain it enters (Eq 3.1).
"""

from incortex.cells.base_cell import BaseCell


class EarCell(BaseCell):
    """Message: {"audio"?: str | None} — omit audio to capture live input."""

    def __init__(self, ear, name="ear_cell"):
        super().__init__(name, "ear")
        self._ear = ear

    def _validate(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        audio = message.get("audio")
        if audio is not None and not isinstance(audio, str):
            raise ValueError(f"{self.name}: 'audio' must be a path string or None")

    def _process(self, message):
        transcript = self._ear.listen(message.get("audio"))
        content = {"text": transcript.text, "source": transcript.source}
        return content, transcript.confidence
