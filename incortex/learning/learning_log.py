"""LearningLog — the durable history of learning events.

JSONL on disk (Design_Doc §15.2 MVP storage), one JSON object per line,
loaded back on startup so the history survives restarts. With no path it
is an in-memory log with the same interface.
"""

import json
import time
from pathlib import Path


class LearningLog:
    def __init__(self, path=None, clock=time.time):
        self._clock = clock
        self._entries = []
        self._path = Path(path) if path is not None else None
        if self._path is not None:
            if self._path.exists():
                for line in self._path.read_text().splitlines():
                    if line.strip():
                        self._entries.append(json.loads(line))
            else:
                self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, entry):
        """Stamp and append one learning event."""
        if not isinstance(entry, dict):
            raise ValueError("a learning log entry must be a dict")
        stamped = {**entry, "created_at": self._clock()}
        try:
            line = json.dumps(stamped)
        except TypeError as error:
            raise ValueError(f"entry must be JSON-serializable: {error}") from error
        self._entries.append(stamped)
        if self._path is not None:
            with self._path.open("a") as handle:
                handle.write(line + "\n")

    def recent(self, count=None):
        """The recorded entries, oldest first."""
        entries = tuple(self._entries)
        return entries if count is None else entries[-count:]

    def __len__(self):
        return len(self._entries)
