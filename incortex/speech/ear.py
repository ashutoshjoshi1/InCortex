"""The Ear — speech-to-text providers (Design_Doc §12.8).

Every ear returns a Transcript with an honest confidence in [0, 1]
(the §0 convention), so a mumbled recording carries a low number the
rest of the brain can act on. Providers:

- ScriptedEar  — replays fixed transcripts (tests, demos)
- TypedEar     — 'transcribes' the keyboard: the dependency-free default
- WhisperEar   — real audio transcription when openai-whisper is installed
"""

import importlib
import math
from collections import deque
from dataclasses import dataclass

from incortex.cells.cell_math import clip01

NEUTRAL_CONFIDENCE = 0.5  # honest "no evidence either way"
WHISPER_INSTALL_HINT = (
    "Whisper is not installed. Install the voice extra with: "
    "pip install openai-whisper"
)


@dataclass(frozen=True)
class Transcript:
    """What an ear heard, and how sure it is."""

    text: str
    confidence: float
    source: str

    def __post_init__(self):
        if not isinstance(self.text, str):
            raise ValueError("transcript text must be a string")
        if not isinstance(self.confidence, (int, float)) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("transcript confidence must be in [0, 1]")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("transcript source must be a non-empty string")


class BaseEar:
    """Contract: listen(audio=None) -> Transcript. Raise EOFError on hangup."""

    def listen(self, audio=None):
        raise NotImplementedError


class ScriptedEar(BaseEar):
    """Replays a fixed sequence of transcripts; hangs up when exhausted."""

    def __init__(self, transcripts):
        self._queue = deque(
            item if isinstance(item, Transcript)
            else Transcript(text=item, confidence=1.0, source="scripted")
            for item in transcripts
        )

    def listen(self, audio=None):
        if not self._queue:
            raise EOFError("scripted ear has nothing left to say")
        return self._queue.popleft()


class TypedEar(BaseEar):
    """The dependency-free default: 'transcribes' typed input, confidence 1.0
    (keyboards do not mumble)."""

    def __init__(self, reader=input, prompt="you (voice)> "):
        self._reader = reader
        self._prompt = prompt

    def listen(self, audio=None):
        text = self._reader(self._prompt)  # EOFError propagates: that's a hangup
        return Transcript(text=text.strip(), confidence=1.0, source="typed")


class WhisperEar(BaseEar):
    """Transcribes audio files with OpenAI Whisper (optional dependency).

    Confidence comes from the model itself: Whisper reports each segment's
    mean token log-probability; exponentiating the average turns it back
    into a probability — a mumbled recording genuinely scores lower.
    """

    def __init__(self, model=None, model_name="base",
                 importer=importlib.import_module):
        self._model = model
        self._model_name = model_name
        self._importer = importer

    def listen(self, audio=None):
        if audio is None:
            raise ValueError(
                "WhisperEar needs an audio file path; live microphone capture "
                "is a later refinement"
            )
        result = self._load_model().transcribe(str(audio))
        segments = result.get("segments", [])
        if segments:
            mean_logprob = (sum(segment["avg_logprob"] for segment in segments)
                            / len(segments))
            confidence = clip01(math.exp(mean_logprob))
        else:
            confidence = NEUTRAL_CONFIDENCE
        return Transcript(text=result.get("text", "").strip(),
                          confidence=confidence, source="whisper")

    def _load_model(self):
        if self._model is None:
            try:
                whisper = self._importer("whisper")
            except ImportError as error:
                raise ImportError(WHISPER_INSTALL_HINT) from error
            self._model = whisper.load_model(self._model_name)
        return self._model
