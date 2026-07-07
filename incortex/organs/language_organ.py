"""LanguageOrgan — understands user language and generates replies (Design_Doc §12.3).

Phase 3 wraps the LanguageTissue; later phases add context, summarization,
and dialogue tissues behind the same understand/respond interface.
"""

from incortex.organs.base_organ import BaseOrgan, OrganOutput
from incortex.tissues import LanguageTissue

CAPABILITIES = (
    "explain", "describe", "tell", "say", "chat", "hello", "hi",
    "talk", "text", "word", "summarize", "teach", "learn",
)


class LanguageOrgan(BaseOrgan):
    def __init__(self, name="language_organ"):
        super().__init__(name, capability_keywords=CAPABILITIES)
        self._language = LanguageTissue()
        self.add_tissue(self._language, critical=True)

    def understand(self, text):
        """Clean raw text and classify its intent."""
        output = self._language.process(text)
        return self._wrap(output)

    def respond(self, intent, text, memory_results):
        """Generate the reply for an understood request."""
        output = self._language.respond(intent, text, memory_results)
        return self._wrap(output)

    def process(self, message):
        return self.understand(message)

    def _wrap(self, tissue_output):
        return OrganOutput(
            organ_name=self.name,
            content=tissue_output.content,
            confidence=tissue_output.confidence,
            stage_outputs=(tissue_output,),
        )
