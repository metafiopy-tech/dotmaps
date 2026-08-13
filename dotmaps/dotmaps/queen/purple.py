"""PURPLE — the theory-of-Fio organ (QUEEN spec §3.7).

March's design: a component that watches which of two responses Fio
actually chooses and develops a theory of his cognitive signature over
time. v0 is dumb by design, per the law (gates, not advice): an act-rate
ledger per escalation category, mechanical cutoff. "Everything escalates"
in v0 — there is no adaptive threshold yet, only the count that would
eventually justify one.

No separate write path: every ESCALATE resolution already IS the record
(id, category-bearing data, choice, seq-latency) inside the append-only
trip log (QUEEN spec §3.2 — she hears trips, never polls). Purple is a
pure read-side ledger over that log.

Threshold application hard-refuses below 20 events — the count stays
visible, but nothing acts on it yet.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import trips as trips_mod

MIN_EVENTS_FOR_THRESHOLD = 20

DEFER_MARKERS = ("keep shelving", "defer", "ignore", "not now", "later", "wait")


def _category(raised_data: dict[str, Any]) -> str:
    """category = the raiser's own 'category' field if given, else the
    predicate/dot/skill/map identity it's about, else 'general'."""
    if raised_data.get("category"):
        return raised_data["category"]
    for key in ("predicate", "dot", "skill", "map"):
        if raised_data.get(key):
            return f"{key}:{raised_data[key]}"
    return "general"


def _outcome(choice_label: str | None) -> str:
    if choice_label is None:
        return "ignored"
    low = choice_label.lower()
    return "deferred" if any(m in low for m in DEFER_MARKERS) else "acted"


def ledger(path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> list[dict[str, Any]]:
    """One row per ESCALATE lifecycle (raised [+ resolved]). latency_trips
    is measured in trip-log sequence numbers, not wall-clock — deterministic
    and testable without a clock."""
    raised: dict[str, dict] = {}
    resolved: dict[str, dict] = {}
    for rec in trips_mod.read_all(path):
        if rec["type"] != "ESCALATE":
            continue
        d = rec["data"]
        eid = d.get("id")
        if eid is None:
            continue
        if d.get("phase") == "raised":
            raised[eid] = {"t": rec["t"], "seq": rec["seq"], **d}
        elif d.get("phase") == "resolved":
            resolved[eid] = {"t": rec["t"], "seq": rec["seq"], **d}

    rows = []
    for eid, r in raised.items():
        res = resolved.get(eid)
        latency = (res["seq"] - r["seq"]) if res else None
        rows.append({
            "id": eid, "category": _category(r),
            "outcome": _outcome(res.get("choice_label") if res else None),
            "latency_trips": latency,
        })
    return rows


def act_rate_table(path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> dict[str, Any]:
    rows = ledger(path)
    by_cat: dict[str, dict[str, int]] = {}
    for r in rows:
        c = by_cat.setdefault(r["category"], {"acted": 0, "deferred": 0, "ignored": 0})
        c[r["outcome"]] += 1
    table = {}
    for cat, counts in by_cat.items():
        total = sum(counts.values())
        table[cat] = {**counts, "total": total,
                      "act_rate": round(counts["acted"] / total, 3) if total else 0.0}
    return {"n_events": len(rows), "table": table,
            "threshold_applicable": len(rows) >= MIN_EVENTS_FOR_THRESHOLD,
            "min_events_for_threshold": MIN_EVENTS_FOR_THRESHOLD}


def apply_threshold(category: str, path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> float:
    """Hard refuse below MIN_EVENTS_FOR_THRESHOLD (count visible, per the
    law: 'gates, not advice' applies to the queen's OWN self-knowledge
    too — she doesn't act on a theory of Fio she doesn't have data for)."""
    summary = act_rate_table(path)
    if not summary["threshold_applicable"]:
        raise RuntimeError(
            f"purple ledger refuses: {summary['n_events']} event(s) logged, "
            f"need >= {MIN_EVENTS_FOR_THRESHOLD} before a threshold applies")
    return summary["table"].get(category, {}).get("act_rate", 0.0)
