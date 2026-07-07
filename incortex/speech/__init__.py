"""The Speech layer — Ear and Mouth device adapters (Phase 6)."""

from incortex.speech.ear import (
    BaseEar,
    ScriptedEar,
    Transcript,
    TypedEar,
    WhisperEar,
)
from incortex.speech.mouth import (
    BaseMouth,
    SilentMouth,
    SystemVoiceMouth,
    Utterance,
)

__all__ = [
    "BaseEar",
    "BaseMouth",
    "ScriptedEar",
    "SilentMouth",
    "SystemVoiceMouth",
    "Transcript",
    "TypedEar",
    "Utterance",
    "WhisperEar",
]
