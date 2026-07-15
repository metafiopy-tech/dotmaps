"""Destructive-dot gates — Phase 2 (spec §4.3).

Policy, enforced by the orchestrator BEFORE Traveler.attempt on any dot flagged
`destructive: true`:

  1. dry-run          -> ALLOW (every mutation is mocked anyway; the dry run
                          should rehearse the destructive path, not skip it)
  2. confirm callback -> ask it. Interactive runs wire this to a human prompt —
                          the explicit human-confirm pause the spec requires.
  3. --allow-destructive (explicit, per-run flag) -> ALLOW. This is the "I have
                          staging / reversibility set up" assertion, made by the
                          human who launched the run, never by the agent.
  4. otherwise        -> BLOCK. The dot is skipped this run; it can never be
                          silently attempted. Blocked-and-required means the
                          run ends red — loudly, not conveniently.

The gate returns a decision; it never mutates anything itself. Termination
authority stays with the orchestrator (rule 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..models import Dot

ALLOW = "allow"
BLOCK = "block"


@dataclass
class GateConfig:
    dry_run: bool = False
    allow_destructive: bool = False
    # interactive human-confirm pause; returns True to proceed. None = no human
    # available (headless run), which is a BLOCK for destructive dots.
    confirm: Optional[Callable[[Dot], bool]] = None
    # audit trail of gate decisions this run
    decisions: list = field(default_factory=list)


def guard(dot: Dot, config: GateConfig) -> str:
    """Decide whether a dot may be attempted. Non-destructive dots always pass."""
    if not dot.destructive:
        return ALLOW
    if config.dry_run:
        decision = ALLOW  # mocked world; rehearse the path
    elif config.confirm is not None:
        decision = ALLOW if config.confirm(dot) else BLOCK
    elif config.allow_destructive:
        decision = ALLOW
    else:
        decision = BLOCK
    config.decisions.append({"dot": dot.id, "destructive": True, "decision": decision})
    return decision
