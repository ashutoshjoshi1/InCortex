"""InCortex voice launcher (Phase 6).

Type your words (the dependency-free ear) and hear the replies spoken
through your system voice — on macOS this uses the built-in `say`.
For real audio transcription, install the voice extra
(pip install openai-whisper) and use WhisperEar with audio files.

Run:  python scripts/run_voice.py [db_path]     (default: data/incortex.db)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_cli import DEFAULT_DB_PATH, build_core  # scripts/ is on sys.path

from incortex.interfaces.voice import VoiceInterface
from incortex.organs import SpeechOrgan
from incortex.speech import SilentMouth, SystemVoiceMouth, TypedEar


def build_mouth():
    """The real system voice when available, a printing echo otherwise."""
    try:
        return SystemVoiceMouth()
    except RuntimeError as error:
        print(f"(no system voice: {error})")
        return SilentMouth()


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    core = build_core(db_path)
    speech = SpeechOrgan(ear=TypedEar(), mouth=build_mouth())
    print("InCortex v0.1 - Cell Genesis (Phase 6: Voice)")
    print(f"Memory: {db_path} ({core.memory.manager.stats()['active']} memories)")
    print("Type to talk - replies are spoken aloud. Say 'goodbye' to end.")
    try:
        VoiceInterface(core, speech).run()
    except KeyboardInterrupt:
        print("\nGoodbye.")


if __name__ == "__main__":
    main()
