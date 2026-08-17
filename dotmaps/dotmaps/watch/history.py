"""HISTORY — a watch dot's current state, derived from trips.jsonl (never
cached). Same discipline as `queen/surface.py`'s open-escalation scan and
`queen/dispatch.py`'s `_shelve_streak`: the trip log is the only ledger,
so "what's the state of this dot right now" is always a fresh replay, not
a read of some second store that could drift from it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..queen import trips as trips_mod

WATCH_CHECK_TYPES = {"WORK_ORDER", "CERTIFIED", "ORACLE_FAIL"}


def trip_id(slug: str, dot_id: str) -> str:
    """The correlation key threaded through every trip a dot's checks emit
    (WORK_ORDER while a candidate, CERTIFIED/ORACLE_FAIL once certified,
    ESCALATE on a failing transition) — same convention as
    `queen/dispatch.py`'s `_shelve_id`."""
    return f"watch:{slug}:{dot_id}"


def _is_watch_check(rec: dict[str, Any], slug: str, dot_id: str) -> bool:
    if rec["type"] not in WATCH_CHECK_TYPES:
        return False
    d = rec.get("data", {})
    if rec["type"] == "WORK_ORDER" and d.get("kind") != "watch_check":
        return False
    return d.get("id") == trip_id(slug, dot_id)


def dot_checks(records: list[dict], slug: str, dot_id: str) -> list[dict[str, Any]]:
    """Every check trip for this dot, oldest first, each `{"ok", "status",
    "evidence", "t", "cycle"}`."""
    out = []
    for rec in records:
        if not _is_watch_check(rec, slug, dot_id):
            continue
        d = rec["data"]
        if rec["type"] == "WORK_ORDER":
            ok = d.get("phase") == "complete"
        else:  # CERTIFIED always a pass, ORACLE_FAIL always a fail
            ok = rec["type"] == "CERTIFIED"
        out.append({"ok": ok, "status": d.get("status", "green" if ok else "red"),
                    "evidence": d.get("evidence") or d.get("reason"),
                    "t": rec["t"], "cycle": d.get("cycle")})
    return out


def consecutive_clean(checks: list[dict[str, Any]]) -> int:
    n = 0
    for c in reversed(checks):
        if not c["ok"]:
            break
        n += 1
    return n


def dot_state(records: list[dict], slug: str, dot_id: str) -> dict[str, Any]:
    """The live view one dot: unlit (never checked) or its latest verdict
    plus streak — exactly what the constellation lights on screen."""
    checks = dot_checks(records, slug, dot_id)
    if not checks:
        return {"lit": False, "status": "unlit", "streak": 0, "n": 0,
                "evidence": None, "last_checked": None}
    last = checks[-1]
    return {"lit": True, "status": last["status"], "streak": consecutive_clean(checks),
            "n": len(checks), "evidence": last["evidence"], "last_checked": last["t"]}


def target_cycle(records: list[dict], slug: str) -> int:
    """The highest cycle number any dot on this target has reached — the
    next cycle to run is one past this."""
    best = 0
    for rec in records:
        d = rec.get("data", {})
        if d.get("target") != slug:
            continue
        if rec["type"] not in WATCH_CHECK_TYPES:
            continue
        c = d.get("cycle")
        if isinstance(c, int):
            best = max(best, c)
    return best


def target_dot_ids(records: list[dict], slug: str) -> list[str]:
    """Every dot id ever checked for this target, first-seen order —
    lets the UI show the constellation even for a target the current
    process never compiled (a second `dotmaps ui` process, a CLI run
    earlier, doesn't matter: the trips are the only source of truth)."""
    seen: list[str] = []
    known: set[str] = set()
    for rec in records:
        d = rec.get("data", {})
        if d.get("target") != slug or rec["type"] not in WATCH_CHECK_TYPES:
            continue
        dot_id = d.get("dot")
        if dot_id and dot_id not in known:
            known.add(dot_id)
            seen.append(dot_id)
    return seen


def load_records(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> list[dict]:
    return trips_mod.read_all(trips_path)
