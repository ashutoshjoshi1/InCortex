"""Voice demo — the full speech loop with no audio hardware needed.

A ScriptedEar plays a fixed conversation and a SilentMouth prints what
would be spoken, so this runs anywhere (including CI). Swap in TypedEar +
SystemVoiceMouth (see scripts/run_voice.py) for the real thing.

Run:  python examples/voice_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from incortex.core import CortexCore
from incortex.interfaces.voice import VoiceInterface
from incortex.organs import SpeechOrgan
from incortex.speech import ScriptedEar, SilentMouth, Transcript

CONVERSATION = [
    "Teach yourself what photosynthesis is.",
    "What is photosynthesis?",
    Transcript("mmmble mmble hmm", 0.2, "scripted"),  # a mumble: watch the gate
    "goodbye",
]


def main():
    speech = SpeechOrgan(ear=ScriptedEar(CONVERSATION), mouth=SilentMouth())
    VoiceInterface(CortexCore(), speech).run()


if __name__ == "__main__":
    main()
