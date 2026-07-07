"""MouthCell — a Mouth provider wearing the Cell contract.

This is the design doc's SpeechCell ("convert response to voice", §9.1).
Speaking is deterministic — it worked or it raised — so confidence is 1.0
and failures land in the cell's error count like any other cell crash.
"""

from incortex.cells.base_cell import BaseCell


class MouthCell(BaseCell):
    """Message: {"text": str} — the reply to speak aloud."""

    def __init__(self, mouth, name="mouth_cell"):
        super().__init__(name, "mouth")
        self._mouth = mouth

    def _validate(self, message):
        if not isinstance(message, dict):
            raise ValueError(f"{self.name}: message must be a dict")
        text = message.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{self.name}: 'text' must be a non-empty string")

    def _process(self, message):
        utterance = self._mouth.speak(message["text"])
        content = {
            "text": utterance.text,
            "spoken": utterance.spoken,
            "engine": utterance.engine,
        }
        return content, 1.0
