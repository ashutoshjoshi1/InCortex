"""The Tissue layer — groups of Cells working together (Phase 2)."""

from incortex.tissues.base_tissue import BaseTissue, TissueOutput
from incortex.tissues.language_tissue import LanguageTissue
from incortex.tissues.learning_tissue import LearningTissue
from incortex.tissues.memory_tissue import MemoryTissue

__all__ = [
    "BaseTissue",
    "LanguageTissue",
    "LearningTissue",
    "MemoryTissue",
    "TissueOutput",
]
