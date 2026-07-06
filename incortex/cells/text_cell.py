"""TextCell — normalizes raw text input and reports basic statistics.

The first perception step of the Input → Language flow. Confidence
(math_model.md §1.2) is the fraction of input chunks that look like words,
so clean prose scores high and symbol noise scores low.
"""

from incortex.cells.base_cell import BaseCell, require_nonempty_text
from incortex.cells.cell_math import tokenize


class TextCell(BaseCell):
    def __init__(self, name="text_cell"):
        super().__init__(name, "text")

    def _validate(self, message):
        require_nonempty_text(self.name, message)

    def _process(self, message):
        cleaned = " ".join(message.split())
        chunks = cleaned.split(" ")
        wordlike = sum(1 for chunk in chunks if any(ch.isalnum() for ch in chunk))
        confidence = wordlike / len(chunks)
        content = {
            "text": cleaned,
            "word_count": len(tokenize(cleaned)),
            "char_count": len(cleaned),
        }
        return content, confidence
