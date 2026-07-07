"""The voice interface — the conversation loop (Design_Doc §12.8 speech flow).

Listen → gate on listening confidence → think (CortexCore) → speak.

The listen gate is the new math of this phase: a transcript whose
confidence falls below the same 0.4 floor the Cortex uses for answers
(Eq 4.4) is asked to repeat itself — the brain is never bothered with
something the ear isn't sure it heard.
"""

from incortex.cells.cell_math import pipeline_confidence

LISTEN_THRESHOLD = 0.4  # the Eq 4.4 floor, applied to hearing
GREETING = "InCortex voice interface ready. Say 'goodbye' to end."
FAREWELL = "Goodbye."
REPEAT_PROMPT = "I didn't catch that clearly - could you say it again?"
QUIT_WORDS = frozenset({"quit", "exit", "goodbye", "bye", "stop"})


class VoiceInterface:
    def __init__(self, core, speech, output=print):
        self._core = core
        self._speech = speech
        self._output = output

    def run(self):
        """The full conversation: greet, loop until hangup or quit word."""
        self._speech.say(GREETING)
        while self.run_once():
            pass

    def run_once(self):
        """One turn of the loop. Returns False when the conversation ends."""
        try:
            heard = self._speech.hear()
        except EOFError:
            self._speech.say(FAREWELL)
            return False
        text = heard.content["text"].strip()
        if not text:
            return True
        self._output(f"[heard {text!r} | listen confidence {heard.confidence:.2f}]")
        if text.lower().strip(".!?") in QUIT_WORDS:
            self._speech.say(FAREWELL)
            return False
        if heard.confidence < LISTEN_THRESHOLD:
            self._speech.say(REPEAT_PROMPT)
            return True
        context = self._core.handle(text)
        full_chain = pipeline_confidence([heard.confidence,
                                          context.chain_confidence])
        self._output(f"[chain with listening: {full_chain:.2f}]")
        self._speech.say(context.reply)
        return True
