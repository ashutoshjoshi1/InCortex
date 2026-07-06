"""BaseTissue — a group of Cells working together (Design_Doc §10).

A Tissue manages its Cells, routes messages to the ones that accept them,
combines their outputs with confidence weighting (Eq 2.1-2.2), forwards
feedback to every member, and reports conservative collective health
(Eq 2.4: never healthier than its weakest critical Cell).
"""

from dataclasses import dataclass
from typing import Any

from incortex.cells.base_cell import BaseCell
from incortex.cells.cell_math import clip01, confidence_weights, status_band


@dataclass(frozen=True)
class TissueOutput:
    """Immutable result of one Tissue-level process() call."""

    tissue_name: str
    content: Any
    confidence: float
    cell_outputs: tuple  # the member CellOutputs behind this result


class BaseTissue:
    def __init__(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("tissue name must be a non-empty string")
        self.name = name
        self._cells = []
        self._critical = set()

    @property
    def cells(self):
        return tuple(self._cells)

    def add_cell(self, cell, critical=False):
        """Register a member Cell. Critical cells cap the tissue's health (Eq 2.4)."""
        if not isinstance(cell, BaseCell):
            raise ValueError(f"{self.name}: only BaseCell instances can join a tissue")
        if any(member.name == cell.name for member in self._cells):
            raise ValueError(f"{self.name}: a cell named '{cell.name}' already exists")
        self._cells.append(cell)
        if critical:
            self._critical.add(cell.name)

    def get_cell(self, name):
        for cell in self._cells:
            if cell.name == name:
                return cell
        raise ValueError(f"{self.name}: no cell named '{name}'")

    def process(self, message):
        """Broadcast to every Cell that accepts the message, then combine.

        Routing-by-acceptance is the Phase 2 stand-in for the learned
        gate of Eq 2.3. Subclasses override this with specialized flows.
        """
        if not self._cells:
            raise ValueError(f"{self.name}: tissue has no cells")
        accepting = [cell for cell in self._cells if cell.accepts(message)]
        if not accepting:
            raise ValueError(f"{self.name}: no cell accepts this message")
        outputs = [cell.process(message) for cell in accepting]
        return self.combine(outputs)

    def combine(self, outputs):
        """Default combination — contents keyed by cell, confidence per Eq 2.1 + 2.4."""
        content = {output.cell_name: output.content for output in outputs}
        return TissueOutput(
            tissue_name=self.name,
            content=content,
            confidence=self.combined_confidence(outputs),
            cell_outputs=tuple(outputs),
        )

    def combined_confidence(self, outputs):
        """Eq 2.4 — confidence-weighted mean of member confidences."""
        weights = confidence_weights([output.confidence for output in outputs])  # Eq 2.1
        return clip01(
            sum(weight * output.confidence for weight, output in zip(weights, outputs))
        )

    def learn(self, feedback):
        """Forward feedback to every member Cell (Design_Doc §10.1 responsibility 5)."""
        for cell in self._cells:
            cell.learn(feedback)

    def health_check(self):
        """Eq 2.4 — tissue health = min(mean of all cells, weakest critical cell)."""
        reports = [cell.health_check() for cell in self._cells]
        if reports:
            mean_health = sum(report["health"] for report in reports) / len(reports)
            critical = [r["health"] for r in reports if r["name"] in self._critical]
            health = min([mean_health] + critical)
        else:
            health = 0.0  # an empty tissue cannot do its job
        return {
            "name": self.name,
            "status": status_band(health),
            "health": health,
            "cells": reports,
        }
