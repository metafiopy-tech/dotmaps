"""GATEKEEPER v0 — the mutualist audit (QUEEN spec §4a hole 1).

The golf-gig oracle-validity tells, inverted onto the agent. A mutualist
(the Composter/BANK, and later every other organ) is net-positive iff, on
a pre-registered cadence, it clears three tests:

  1. state-change  — "prior output produced no state change in him" was
     the golf-gig kill tell. act-rate = consumption events that measurably
     changed a decision, over total consumption.
  2. transfer      — "off-objective return is only real if it transfers
     to a domain that didn't generate it." Effects that never leave the
     mutualist's own consumption loop are narrative, not value.
  3. parasite      — "an agent optimized on tickets closed will create
     tickets." The friction class it's meant to eat must be flat or
     shrinking under its stewardship, never growing.

Fail any one -> DEMOTE to candidate, re-earn on the next cadence.

Hard gate: refuses any verdict on insufficient data (<1 audit period).
"An audit that can't fail is not an audit" — a Gatekeeper that PASSES on
an empty ledger is not auditing, it's rubber-stamping.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MIN_AUDIT_PERIODS = 1


@dataclass(frozen=True)
class LedgerPeriod:
    """One audit period's worth of Composter ledger data."""
    period: int
    invocations: int                       # times the mutualist's output was consumed
    state_changes: int                     # times consumption measurably changed a decision
    domains_fired: tuple[str, ...] = ()    # domains OUTSIDE its own consumption loop
    friction_class_count: int = 0          # count of the friction class it eats, this period
    friction_class_count_prev: int | None = None  # same class, prior period


def state_change_test(periods: list[LedgerPeriod]) -> dict[str, Any]:
    total_inv = sum(p.invocations for p in periods)
    total_chg = sum(p.state_changes for p in periods)
    act_rate = (total_chg / total_inv) if total_inv else 0.0
    return {"act_rate": round(act_rate, 3), "invocations": total_inv,
            "state_changes": total_chg, "passed": total_inv > 0 and act_rate > 0.0}


def transfer_test(periods: list[LedgerPeriod]) -> dict[str, Any]:
    domains = sorted({d for p in periods for d in p.domains_fired})
    return {"domains": domains, "passed": len(domains) >= 1}


def parasite_test(periods: list[LedgerPeriod]) -> dict[str, Any]:
    deltas = [p.friction_class_count - p.friction_class_count_prev
              for p in periods if p.friction_class_count_prev is not None]
    growing = any(d > 0 for d in deltas)
    return {"deltas": deltas, "growing": growing,
            "passed": bool(deltas) and not growing}


def audit(periods: list[LedgerPeriod]) -> dict[str, Any]:
    """Hard gate: fewer than MIN_AUDIT_PERIODS periods refuses any verdict
    outright, rather than defaulting to PASS or DEMOTE on no evidence."""
    if len(periods) < MIN_AUDIT_PERIODS:
        return {"verdict": "REFUSED",
                "reason": f"insufficient data: {len(periods)} period(s) logged, "
                          f"need >= {MIN_AUDIT_PERIODS}"}

    sc = state_change_test(periods)
    tt = transfer_test(periods)
    pt = parasite_test(periods)
    tests = (("state-change", sc), ("transfer", tt), ("parasite", pt))
    failed_on = [name for name, r in tests if not r["passed"]]
    return {"verdict": "PASS" if not failed_on else "DEMOTE",
            "failed_on": failed_on,
            "state_change": sc, "transfer": tt, "parasite": pt}
