"""TRIP BUS — the queen's only sense organ (QUEEN spec §3.2).

"The executive only hears what trips, never polls." Append-only JSONL log
of typed events. Hash-chained (each record commits to the previous
record's hash) so a rewrite is mechanically detectable, never trusted on
say-so — frozen law #1: mechanical gates, never advice.

Typed vocabulary (fixed; do not add new types — reuse these across every
queen organ, distinguished by the `data` payload):
    CERTIFIED        a covered dot executed a certified skill and passed
    CONVICTED        a skill's oracle gate failed certification
    BLOCKED          a gate refused an action (in-flight dup, wall, etc.)
    BUDGET_EXHAUSTED a live dispatch loop hit its ClockConfig budget
    ORACLE_FAIL      a certified skill failed its own check on replay
    SHELVED          a predicate/skill parked this round with a re-check
                     proposed (frontier not grown, or decay past threshold)
    ESCALATE         a decision surfaced to Fio (phase=raised|resolved)
    SLEEP            one homeostasis tick completed
    WORK_ORDER       a DO-phase agentic run against a temp workspace
                     (data.phase=start|complete|failed) — Q8/Q9: the
                     mechanical-completion-gated execution phase that
                     precedes any authorized growth
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRIPS_PATH = REPO_ROOT / "runs" / "queen" / "trips.jsonl"

TYPES = {
    "CERTIFIED", "CONVICTED", "BLOCKED", "BUDGET_EXHAUSTED",
    "ORACLE_FAIL", "SHELVED", "ESCALATE", "SLEEP", "WORK_ORDER",
}

GENESIS_HASH = "0" * 64


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _line_hash(seq: int, t: str, type_: str, data: dict, prev_hash: str) -> str:
    payload = json.dumps(
        {"seq": seq, "t": t, "type": type_, "data": data, "prev_hash": prev_hash},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _tail(path: Path) -> dict | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    last = None
    for line in path.read_text().splitlines():
        if line.strip():
            last = json.loads(line)
    return last


def emit(type_: str, path: Path = DEFAULT_TRIPS_PATH, **data: Any) -> dict:
    """Append one trip. The only write path — there is no update or delete."""
    if type_ not in TYPES:
        raise ValueError(f"unknown trip type {type_!r} — not in {sorted(TYPES)}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tail = _tail(path)
    seq = (tail["seq"] + 1) if tail else 1
    prev_hash = tail["hash"] if tail else GENESIS_HASH
    t = _now()
    h = _line_hash(seq, t, type_, data, prev_hash)
    rec = {"seq": seq, "t": t, "type": type_, "data": data,
           "prev_hash": prev_hash, "hash": h}
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def read_all(path: Path = DEFAULT_TRIPS_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_integrity(path: Path = DEFAULT_TRIPS_PATH) -> tuple[bool, str | None]:
    """Walk the hash chain from genesis. Any edit to an existing line —
    content changed, a line deleted, lines reordered — breaks the chain at
    that point. Append-only, enforced structurally, not by convention."""
    prev_hash = GENESIS_HASH
    for rec in read_all(path):
        expect = _line_hash(rec.get("seq"), rec.get("t"), rec.get("type"),
                             rec.get("data"), prev_hash)
        if rec.get("prev_hash") != prev_hash:
            return False, f"chain broken at seq {rec.get('seq')}: prev_hash mismatch"
        if rec.get("hash") != expect:
            return False, f"chain broken at seq {rec.get('seq')}: hash mismatch (tampered)"
        prev_hash = rec["hash"]
    return True, None


if __name__ == "__main__":
    import sys
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TRIPS_PATH
    ok, reason = verify_integrity(p)
    recs = read_all(p)
    print(f"{len(recs)} trip(s) — integrity {'OK' if ok else 'BROKEN: ' + reason}")
