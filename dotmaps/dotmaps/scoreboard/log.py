"""Append-only JSONL event writer.

Rule 2 (the board remembers, not the agent): every meaningful transition is a
line here. state.json is always derivable by replaying this file, so a run can
be killed and resumed by a fresh agent with zero context loss.

Timestamps are provided by the caller (the orchestrator) so this module stays a
dumb, deterministic sink — easy to replay and diff.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

LOG_NAME = "events.jsonl"


class EventLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: str, ts: str, **fields: Any) -> dict[str, Any]:
        record = {"ts": ts, "event": event, **fields}
        # open per-append + flush: crash-safe, and the file is the truth
        with open(self.path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
            f.flush()
        return record

    def replay(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def exists(self) -> bool:
        return self.path.exists() and self.path.stat().st_size > 0
