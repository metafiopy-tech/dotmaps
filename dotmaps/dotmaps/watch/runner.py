"""RUNNER — one watch cycle (W2/W3).

Walks a compiled health map's dots in order, running each through the
real oracle (`watch/oracle.py`) and recording exactly one trip per dot —
WORK_ORDER while the dot is still a candidate, CERTIFIED/ORACLE_FAIL once
it's earned a card (the same vocabulary `queen/dispatch.py` uses for a
routed skill, reused on purpose: a certified watch dot IS a routed skill,
just one whose steps happen to be a live fetch). A failing dot that
wasn't already open gets a real ESCALATE with the evidence receipt
attached — no separate notification channel. Certification is checked
fresh after every clean trip: once a dot's consecutive-clean streak hits
CERT_N, `watch/certify.py` mints the card and a CERTIFIED trip marks the
moment, same call as every other pass thereafter (the type's own meaning,
"a covered dot executed a certified skill and passed", doesn't need a
special case for "first time").

`pace_seconds` is presentation only — the UI passes a nonzero value so
the constellation lights ~2 dots/sec for a keeper watching; tests and the
CLI's non-interactive paths leave it at 0 for an instant cycle.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..queen import surface as surface_mod
from ..queen import trips as trips_mod
from . import certify, history, oracle

DEFAULT_SKILLS = trips_mod.REPO_ROOT / "skills"


def run_cycle(health_map: dict[str, Any],
             trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
             skills_dir: Path = DEFAULT_SKILLS,
             pace_seconds: float = 0.0) -> dict[str, Any]:
    slug, target = health_map["slug"], health_map["target"]
    records = trips_mod.read_all(trips_path)
    cycle = history.target_cycle(records, slug) + 1
    open_ids = {e["id"] for e in surface_mod.open_escalations(trips_path)}

    results = []
    for i, dot in enumerate(health_map["dots"]):
        dot_id = dot["id"]
        id_ = history.trip_id(slug, dot_id)
        cert = certify.already_certified(skills_dir, slug, dot_id)
        outcome = oracle.run_dot_check(dot)

        common = dict(id=id_, target=slug, dot=dot_id, statement=dot["statement"],
                      url=dot["url"], evidence=outcome["evidence"], status=outcome["status"],
                      cycle=cycle)

        newly_certified = None
        if outcome["ok"]:
            if cert:
                trips_mod.emit("CERTIFIED", path=trips_path, skill=cert["name"],
                               wilson=cert["certificate"]["wilson"], **common)
            else:
                trips_mod.emit("WORK_ORDER", path=trips_path, phase="complete",
                               kind="watch_check", **common)
                streak = history.consecutive_clean(
                    history.dot_checks(trips_mod.read_all(trips_path), slug, dot_id))
                if streak >= certify.CERT_N:
                    card = certify.write_certificate(skills_dir, slug, target, dot, streak)
                    trips_mod.emit("CERTIFIED", path=trips_path, skill=card["name"],
                                   wilson=card["certificate"]["wilson"],
                                   **{**common, "evidence": (f"first certification — "
                                                             f"{streak} consecutive clean "
                                                             f"checks"), "status": "green"})
                    newly_certified = card
        else:
            if cert:
                trips_mod.emit("ORACLE_FAIL", path=trips_path, skill=cert["name"],
                               reason=outcome["evidence"], **common)
            else:
                trips_mod.emit("WORK_ORDER", path=trips_path, phase="failed",
                               kind="watch_check", **common)
            if id_ not in open_ids:
                surface_mod.escalate(
                    id_, f"{dot['statement']} just failed — {outcome['evidence']}",
                    ["Acknowledge — keep watching", "Snooze this check"],
                    path=trips_path, target=slug, dot=dot_id, statement=dot["statement"],
                    evidence=outcome["evidence"], kind="watch_escalation")
                open_ids.add(id_)

        results.append({"dot": dot_id, "statement": dot["statement"],
                        "status": outcome["status"], "evidence": outcome["evidence"],
                        "certified": bool(cert) or newly_certified is not None,
                        "newly_certified": newly_certified is not None})
        if pace_seconds and i < len(health_map["dots"]) - 1:
            time.sleep(pace_seconds)

    return {"target": target, "slug": slug, "cycle": cycle, "results": results}
