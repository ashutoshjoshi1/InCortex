"""LanguageTissue — TextCell → IntentCell → ResponseCell as one unit.

The first working example of message passing between Cells (Phase 2
deliverable): the TextCell's cleaned text is handed to the IntentCell,
and the ResponseCell turns intent + memory results into a reply.
"""

from incortex.cells import IntentCell, ResponseCell, TextCell
from incortex.tissues.base_tissue import BaseTissue, TissueOutput


class LanguageTissue(BaseTissue):
    def __init__(self, name="language_tissue"):
        super().__init__(name)
        self._text = TextCell()
        self._intent = IntentCell()
        self._response = ResponseCell()
        self.add_cell(self._text, critical=True)
        self.add_cell(self._intent, critical=True)
        self.add_cell(self._response)

    def process(self, message):
        """Understand raw user text: clean it, then classify the intent."""
        text_output = self._text.process(message)
        cleaned = text_output.content["text"]
        intent_output = self._intent.process(cleaned)
        outputs = (text_output, intent_output)
        content = {
            "text": cleaned,
            "word_count": text_output.content["word_count"],
            "intent": intent_output.content["intent"],
            "distribution": intent_output.content["distribution"],
        }
        return TissueOutput(
            tissue_name=self.name,
            content=content,
            confidence=self.combined_confidence(outputs),
            cell_outputs=outputs,
        )

    def respond(self, intent, text, memory_results):
        """Generate the reply for an understood request via the ResponseCell."""
        output = self._response.process(
            {"intent": intent, "text": text, "memory_results": memory_results}
        )
        return TissueOutput(
            tissue_name=self.name,
            content=output.content,
            confidence=output.confidence,
            cell_outputs=(output,),
        )
