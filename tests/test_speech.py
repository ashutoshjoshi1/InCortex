"""Phase 6 tests — the voice system.

Covers the Ear (speech-to-text) and Mouth (text-to-speech) contracts, the
Whisper confidence math (log-probability -> probability), the SpeechOrgan,
and the voice conversation loop — including the new listen-confidence gate:
a mumbled transcript is asked to repeat before the brain is bothered.
"""

import math

import pytest

from incortex.core import CortexCore
from incortex.interfaces.voice import (
    FAREWELL,
    LISTEN_THRESHOLD,
    REPEAT_PROMPT,
    VoiceInterface,
)
from incortex.organs import SpeechOrgan
from incortex.speech import (
    BaseEar,
    BaseMouth,
    ScriptedEar,
    SilentMouth,
    SystemVoiceMouth,
    Transcript,
    TypedEar,
    Utterance,
    WhisperEar,
)


class FakeMouth(BaseMouth):
    """Records everything it is asked to speak."""

    def __init__(self):
        self.spoken = []

    def speak(self, text):
        self.spoken.append(text)
        return Utterance(text=text, spoken=True, engine="fake")


class FakeWhisperModel:
    def __init__(self, text=" Hello world ", logprobs=(-0.223, -0.223)):
        self.text = text
        self.logprobs = logprobs
        self.calls = []

    def transcribe(self, path):
        self.calls.append(path)
        return {
            "text": self.text,
            "segments": [{"avg_logprob": lp} for lp in self.logprobs],
        }


# ---------------------------------------------------------------------------
# Transcript and Utterance envelopes
# ---------------------------------------------------------------------------


class TestEnvelopes:
    def test_transcript_validation(self):
        Transcript(text="", confidence=1.0, source="typed")  # empty is allowed
        with pytest.raises(ValueError):
            Transcript(text=42, confidence=1.0, source="typed")
        with pytest.raises(ValueError):
            Transcript(text="hi", confidence=1.5, source="typed")
        with pytest.raises(ValueError):
            Transcript(text="hi", confidence=1.0, source="  ")

    def test_utterance_validation(self):
        with pytest.raises(ValueError):
            Utterance(text="", spoken=True, engine="say")
        with pytest.raises(ValueError):
            Utterance(text="hi", spoken="yes", engine="say")
        with pytest.raises(ValueError):
            Utterance(text="hi", spoken=True, engine=" ")

    def test_base_contracts_are_abstract(self):
        with pytest.raises(NotImplementedError):
            BaseEar().listen()
        with pytest.raises(NotImplementedError):
            BaseMouth().speak("hello")


# ---------------------------------------------------------------------------
# Ears
# ---------------------------------------------------------------------------


class TestScriptedEar:
    def test_plays_transcripts_in_order(self):
        ear = ScriptedEar(["first", Transcript("second", 0.6, "scripted")])
        assert ear.listen().text == "first"
        assert ear.listen().confidence == pytest.approx(0.6)

    def test_plain_strings_are_fully_confident(self):
        assert ScriptedEar(["hello"]).listen().confidence == 1.0

    def test_exhaustion_is_a_hangup(self):
        ear = ScriptedEar([])
        with pytest.raises(EOFError):
            ear.listen()


class TestTypedEar:
    def test_reads_and_trims(self):
        ear = TypedEar(reader=lambda prompt: "  hello there  ")
        transcript = ear.listen()
        assert transcript.text == "hello there"
        assert transcript.confidence == 1.0
        assert transcript.source == "typed"


class TestWhisperEar:
    def test_confidence_is_exp_of_mean_logprob(self):
        # exp(-0.223) = 0.800 — log-probability becomes a [0,1] confidence
        ear = WhisperEar(model=FakeWhisperModel())
        transcript = ear.listen("audio.wav")
        assert transcript.text == "Hello world"
        assert transcript.confidence == pytest.approx(math.exp(-0.223), abs=1e-3)
        assert transcript.source == "whisper"

    def test_no_segments_means_neutral_confidence(self):
        model = FakeWhisperModel(logprobs=())
        assert WhisperEar(model=model).listen("a.wav").confidence == 0.5

    def test_needs_an_audio_path(self):
        with pytest.raises(ValueError):
            WhisperEar(model=FakeWhisperModel()).listen()

    def test_missing_dependency_says_how_to_install(self):
        def failing_importer(name):
            raise ImportError("no module")

        ear = WhisperEar(importer=failing_importer)
        with pytest.raises(ImportError, match="openai-whisper"):
            ear.listen("audio.wav")

    def test_lazy_loading_uses_the_importer(self):
        class FakeModule:
            @staticmethod
            def load_model(name):
                assert name == "base"
                return FakeWhisperModel(text="loaded")

        ear = WhisperEar(importer=lambda name: FakeModule)
        assert ear.listen("a.wav").text == "loaded"


# ---------------------------------------------------------------------------
# Mouths
# ---------------------------------------------------------------------------


class TestSilentMouth:
    def test_echoes_instead_of_speaking(self):
        lines = []
        mouth = SilentMouth(printer=lines.append)
        utterance = mouth.speak("hello")
        assert utterance.spoken is False
        assert utterance.engine == "silent"
        assert lines == ["(spoken) hello"]


class TestSystemVoiceMouth:
    def test_runs_the_platform_command(self):
        calls = []

        def runner(argv, check):
            calls.append((tuple(argv), check))

        mouth = SystemVoiceMouth(command="say", runner=runner)
        utterance = mouth.speak("hello world")
        assert calls == [(("say", "hello world"), True)]
        assert utterance.spoken is True
        assert utterance.engine == "say"

    def test_voice_option_for_say(self):
        calls = []
        mouth = SystemVoiceMouth(command="say", voice="Samantha",
                                 runner=lambda argv, check: calls.append(argv))
        mouth.speak("hi")
        assert calls == [["say", "-v", "Samantha", "hi"]]

    def test_autodetects_an_available_command(self):
        mouth = SystemVoiceMouth(which=lambda cmd: "/usr/bin/espeak"
                                 if cmd == "espeak" else None,
                                 runner=lambda argv, check: None)
        assert mouth.speak("hi").engine == "espeak"

    def test_no_command_anywhere_fails_loudly(self):
        with pytest.raises(RuntimeError, match="text-to-speech"):
            SystemVoiceMouth(which=lambda cmd: None)

    def test_command_failure_is_reported(self):
        def failing_runner(argv, check):
            raise RuntimeError("boom")

        mouth = SystemVoiceMouth(command="say", runner=failing_runner)
        with pytest.raises(RuntimeError):
            mouth.speak("hello")

    def test_rejects_empty_text(self):
        mouth = SystemVoiceMouth(command="say", runner=lambda argv, check: None)
        with pytest.raises(ValueError):
            mouth.speak("   ")


# ---------------------------------------------------------------------------
# SpeechOrgan
# ---------------------------------------------------------------------------


class TestSpeechOrgan:
    def test_hear_wraps_the_ear(self):
        organ = SpeechOrgan(ear=ScriptedEar([Transcript("hello", 1.0, "scripted")]))
        out = organ.hear()
        assert out.content["text"] == "hello"
        assert out.content["source"] == "scripted"
        assert out.confidence == pytest.approx(0.85)  # 0.7*1.0 + 0.3*0.5 blend

    def test_say_wraps_the_mouth(self):
        mouth = FakeMouth()
        out = SpeechOrgan(mouth=mouth).say("good morning")
        assert mouth.spoken == ["good morning"]
        assert out.content["spoken"] is True

    def test_process_dispatches(self):
        organ = SpeechOrgan(ear=ScriptedEar(["hi"]), mouth=FakeMouth())
        assert organ.process({"action": "hear"}).content["text"] == "hi"
        assert organ.process({"action": "say", "text": "yo"}).content["spoken"] is True
        with pytest.raises(ValueError):
            organ.process({"action": "dance"})
        with pytest.raises(ValueError):
            organ.process("not a dict")

    def test_health_covers_both_cells(self):
        report = SpeechOrgan().health_check()
        assert report["status"] == "active"
        names = {cell["name"] for component in report["components"]
                 for cell in ([component] if "confidence" in component else [])}
        assert {"ear_cell", "mouth_cell"} <= names

    def test_mouth_cell_rejects_empty_text(self):
        with pytest.raises(ValueError):
            SpeechOrgan().say("   ")

    def test_mouth_cell_rejects_non_dict_messages(self):
        from incortex.cells import MouthCell
        with pytest.raises(ValueError):
            MouthCell(FakeMouth()).process("not a dict")

    def test_ear_cell_validates_its_message(self):
        from incortex.cells import EarCell
        cell = EarCell(ScriptedEar(["hi"]))
        with pytest.raises(ValueError):
            cell.process("not a dict")
        with pytest.raises(ValueError):
            cell.process({"audio": 42})


# ---------------------------------------------------------------------------
# VoiceInterface — the conversation loop
# ---------------------------------------------------------------------------


def make_voice(script, core=None):
    mouth = FakeMouth()
    speech = SpeechOrgan(ear=ScriptedEar(script), mouth=mouth)
    core = core or CortexCore()
    return VoiceInterface(core, speech, output=lambda line: None), mouth, core


class TestVoiceInterface:
    def test_full_conversation_is_spoken(self):
        voice, mouth, _ = make_voice([
            "Teach yourself what photosynthesis is.",
            "What is photosynthesis?",
            "goodbye",
        ])
        voice.run()
        spoken = " | ".join(mouth.spoken)
        assert "I have learned" in spoken
        assert "From memory" in spoken
        assert mouth.spoken[-1] == FAREWELL

    def test_mumble_is_asked_to_repeat_without_bothering_the_brain(self):
        # Listen confidence 0.2 blends to 0.29 < 0.4 -> repeat prompt,
        # and the Cortex never sees the utterance
        voice, mouth, core = make_voice([
            Transcript("mumble mumble", 0.2, "scripted"),
            "goodbye",
        ])
        voice.run()
        assert REPEAT_PROMPT in mouth.spoken
        assert core.state.snapshot()["tasks_handled"] == 0

    def test_quit_words_end_the_loop_with_a_farewell(self):
        voice, mouth, _ = make_voice(["Goodbye."])
        voice.run()
        assert mouth.spoken[-1] == FAREWELL

    def test_hangup_ends_gracefully(self):
        voice, mouth, _ = make_voice([])  # ear exhausted immediately
        voice.run()
        assert mouth.spoken[-1] == FAREWELL

    def test_empty_utterances_are_skipped(self):
        voice, mouth, core = make_voice(["   ", "goodbye"])
        voice.run()
        assert core.state.snapshot()["tasks_handled"] == 0

    def test_listen_threshold_matches_the_answer_floor(self):
        assert LISTEN_THRESHOLD == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Phase 6 success criterion (Design_Doc §21): the user can speak to InCortex
# and hear a spoken response.
# ---------------------------------------------------------------------------


class TestPhase6SuccessCriteria:
    def test_speech_in_speech_out(self):
        voice, mouth, _ = make_voice([
            Transcript("Teach yourself what gravity is.", 0.95, "whisper"),
            "goodbye",
        ])
        voice.run()
        replies = [text for text in mouth.spoken if "learned" in text.lower()]
        assert replies, "a spoken utterance in should produce a spoken reply out"
