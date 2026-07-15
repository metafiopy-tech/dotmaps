"""Scoreboard = EventLog + derived state.

`state.json` is a *cache* of what you get by replaying the log; it is never the
source of truth (rule 2). `Scoreboard.load_or_init` rebuilds state purely by
replay, which is exactly what `--resume` needs.

The orchestrator talks to this class; it never writes the JSONL directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..models import (
    END_ALL_GREEN,
    EVENT_BUDGET_TICK,
    EVENT_CYCLE_STARTED,
    EVENT_DOT_ATTEMPTED,
    EVENT_DOT_EATEN,
    EVENT_DOT_REGRESSED,
    EVENT_RUN_ENDED,
    EVENT_RUN_STARTED,
    Budget,
    DotResult,
    Map,
)
from .log import EventLog

STATE_NAME = "state.json"


def _now_iso() -> str:
    # Date.now() equivalent; injected here so the rest of the code stays pure.
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Scoreboard:
    workspace: Path
    log: EventLog
    map_name: str = ""
    map_version: str = ""
    cycle: int = 0
    eaten: set[str] = field(default_factory=set)
    attempts: dict[str, int] = field(default_factory=dict)
    usd_spent: float = 0.0
    ended: Optional[str] = None
    last_evidence: dict[str, str] = field(default_factory=dict)

    # -- lifecycle ---------------------------------------------------------- #
    @classmethod
    def load_or_init(cls, workspace: str | Path, m: Optional[Map] = None) -> "Scoreboard":
        ws = Path(workspace).resolve()
        board_dir = ws / ".dotmaps"
        log = EventLog(board_dir / "events.jsonl")
        sb = cls(workspace=ws, log=log)
        if log.exists():
            sb._rebuild_from_log()  # rule 2: resume == replay
        elif m is not None:
            sb.map_name, sb.map_version = m.name, m.version
        return sb

    def _rebuild_from_log(self) -> None:
        """Pure replay. No agent context consulted — that's the rule-2 test."""
        self.cycle = 0
        self.eaten.clear()
        self.attempts.clear()
        self.usd_spent = 0.0
        self.ended = None
        for ev in self.log.replay():
            kind = ev.get("event")
            if kind == EVENT_RUN_STARTED:
                self.map_name = ev.get("map", self.map_name)
                self.map_version = ev.get("version", self.map_version)
            elif kind == EVENT_CYCLE_STARTED:
                self.cycle = ev.get("cycle", self.cycle)
            elif kind == EVENT_DOT_EATEN:
                self.eaten.add(ev["dot"])
                self.last_evidence[ev["dot"]] = ev.get("evidence", "")
            elif kind == EVENT_DOT_REGRESSED:
                self.eaten.discard(ev["dot"])
                self.last_evidence[ev["dot"]] = ev.get("evidence", "")
            elif kind == EVENT_DOT_ATTEMPTED:
                d = ev["dot"]
                self.attempts[d] = ev.get("attempt", self.attempts.get(d, 0) + 1)
            elif kind == EVENT_BUDGET_TICK:
                self.usd_spent = ev.get("usd_spent", self.usd_spent)
            elif kind == EVENT_RUN_ENDED:
                self.ended = ev.get("reason")
        self._persist_cache()

    # -- writes (orchestrator-only) ---------------------------------------- #
    def start_run(self, m: Map) -> None:
        self.map_name, self.map_version = m.name, m.version
        if not self.log.exists():
            self.log.append(EVENT_RUN_STARTED, _now_iso(), map=m.name, version=m.version)
        self._persist_cache()

    def start_cycle(self) -> int:
        self.cycle += 1
        self.log.append(EVENT_CYCLE_STARTED, _now_iso(), cycle=self.cycle)
        return self.cycle

    def reconcile(self, results: list[DotResult]) -> None:
        """Apply a FULL-manifest verifier pass. Emits eaten/regressed events.

        Rule 4: because the verifier re-runs the whole board every cycle, a dot
        that was green and silently broke shows up here as a regression — as
        loudly as a fresh pass.
        """
        for r in results:
            self.last_evidence[r.dot] = r.evidence
            was_eaten = r.dot in self.eaten
            if r.passed and not was_eaten:
                self.eaten.add(r.dot)
                self.log.append(
                    EVENT_DOT_EATEN, _now_iso(), cycle=self.cycle, dot=r.dot,
                    evidence=r.evidence, attempt=self.attempts.get(r.dot, 0),
                )
            elif not r.passed and was_eaten:
                self.eaten.discard(r.dot)
                self.log.append(
                    EVENT_DOT_REGRESSED, _now_iso(), cycle=self.cycle, dot=r.dot,
                    evidence=r.evidence,
                )
        self._persist_cache()

    def log_attempt(self, dot_id: str, actions: Optional[list] = None) -> int:
        """`actions` is the traveler's tool-call journal for this attempt —
        additive field on the frozen dot_attempted event type. Without it a
        30-attempt stall is undiagnosable from the board (learned the hard way
        in the Stage-0 pilot)."""
        self.attempts[dot_id] = self.attempts.get(dot_id, 0) + 1
        extra = {"actions": actions} if actions else {}
        self.log.append(
            EVENT_DOT_ATTEMPTED, _now_iso(), cycle=self.cycle, dot=dot_id,
            attempt=self.attempts[dot_id], **extra,
        )
        self._persist_cache()
        return self.attempts[dot_id]

    def tick_budget(self, usd_spent: float) -> None:
        self.usd_spent = usd_spent
        self.log.append(EVENT_BUDGET_TICK, _now_iso(), cycle=self.cycle, usd_spent=usd_spent)
        self._persist_cache()

    def end(self, reason: str) -> "Scoreboard":
        self.ended = reason
        self.log.append(EVENT_RUN_ENDED, _now_iso(), cycle=self.cycle, reason=reason)
        self._persist_cache()
        return self

    # -- reads -------------------------------------------------------------- #
    def all_green(self, m: Map) -> bool:
        return all(d.id in self.eaten for d in m.dots)

    def budget_remaining(self, budget: Budget) -> bool:
        if self.ended:
            return False
        if self.cycle >= budget.max_cycles:
            return False
        # a non-positive max_usd means cost is not a limiter (e.g. free scripted
        # maps); otherwise stop once the spend ceiling is reached.
        if budget.max_usd > 0 and self.usd_spent >= budget.max_usd:
            return False
        return True

    def summary(self, m: Optional[Map] = None) -> dict[str, Any]:
        total = len(m.dots) if m else len(self.eaten)
        return {
            "map": self.map_name,
            "version": self.map_version,
            "cycle": self.cycle,
            "eaten": sorted(self.eaten),
            "eaten_count": len(self.eaten),
            "total": total,
            "usd_spent": round(self.usd_spent, 4),
            "ended": self.ended,
        }

    def _persist_cache(self) -> None:
        state_path = self.log.path.parent / STATE_NAME
        with open(state_path, "w") as f:
            json.dump(
                {
                    "map": self.map_name,
                    "version": self.map_version,
                    "cycle": self.cycle,
                    "eaten": sorted(self.eaten),
                    "attempts": self.attempts,
                    "usd_spent": self.usd_spent,
                    "ended": self.ended,
                    "last_evidence": self.last_evidence,
                },
                f,
                indent=2,
            )
