"""BaseOrgan — a specialized subsystem made of Tissues and Cells (Design_Doc §12).

An Organ manages its components, aggregates their health recursively
(Eq 2.4), combines multi-stage confidences per Eq 3.1 (geometric by
default, 'min' for conservative organs), and answers "how relevant am I
to this message?" (Eq 3.2) for the Phase 4 Router.
"""

from dataclasses import dataclass
from typing import Any

from incortex.cells.base_cell import BaseCell
from incortex.cells.cell_math import (
    overlap_coefficient,
    pipeline_confidence,
    status_band,
    tokenize,
)
from incortex.tissues.base_tissue import BaseTissue

CONFIDENCE_MODES = ("geometric", "min")


@dataclass(frozen=True)
class OrganOutput:
    """Immutable result of one Organ-level operation."""

    organ_name: str
    content: Any
    confidence: float
    stage_outputs: tuple  # the TissueOutputs / CellOutputs behind this result


class BaseOrgan:
    def __init__(self, name, capability_keywords=(), confidence_mode="geometric"):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("organ name must be a non-empty string")
        if confidence_mode not in CONFIDENCE_MODES:
            raise ValueError(f"confidence_mode must be one of {CONFIDENCE_MODES}")
        self.name = name
        self._capability = frozenset(str(word).lower() for word in capability_keywords)
        self._mode = confidence_mode
        self._components = []  # list of (tissue-or-cell, critical)

    # -- composition ----------------------------------------------------------

    def add_tissue(self, tissue, critical=False):
        self._add(tissue, BaseTissue, "tissue", critical)

    def add_cell(self, cell, critical=False):
        self._add(cell, BaseCell, "cell", critical)

    def _add(self, component, expected_type, kind, critical):
        if not isinstance(component, expected_type):
            raise ValueError(f"{self.name}: only a {kind} can be added here")
        if any(existing.name == component.name for existing, _ in self._components):
            raise ValueError(
                f"{self.name}: a component named '{component.name}' already exists"
            )
        self._components.append((component, critical))

    @property
    def cells(self):
        """Every leaf Cell in this organ, flattened across its tissues."""
        leaves = []
        for component, _ in self._components:
            if isinstance(component, BaseCell):
                leaves.append(component)
            else:
                leaves.extend(component.cells)
        return tuple(leaves)

    # -- organ math -----------------------------------------------------------

    def pipeline(self, confidences):
        """Eq 3.1 — combine stage confidences using this organ's mode."""
        return pipeline_confidence(confidences, mode=self._mode)

    def relevance(self, text):
        """Eq 3.2 stand-in — token overlap between a message and my capabilities."""
        if not isinstance(text, str) or not text.strip():
            return 0.0
        return overlap_coefficient(frozenset(tokenize(text)), self._capability)

    # -- shared duties ----------------------------------------------------------

    def process(self, message):
        """Each concrete Organ defines its own primary flow."""
        raise NotImplementedError

    def learn(self, feedback):
        """Forward feedback to every component (and so to every leaf cell)."""
        for component, _ in self._components:
            component.learn(feedback)

    def health_check(self):
        """Eq 2.4 recursively — mean of components, capped by the weakest critical one."""
        reports = [component.health_check() for component, _ in self._components]
        if reports:
            mean_health = sum(report["health"] for report in reports) / len(reports)
            critical = [
                report["health"]
                for report, (_, is_critical) in zip(reports, self._components)
                if is_critical
            ]
            health = min([mean_health] + critical)
        else:
            health = 0.0  # an organ with no components cannot do its job
        return {
            "name": self.name,
            "status": status_band(health),
            "health": health,
            "components": reports,
        }
