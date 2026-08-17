"""SLEEP — the homeostasis organ (QUEEN spec §3.8; metabolism spec C3 +
C7 + C9: "sleep = scheduled consolidation: compress episodic to semantic,
discard noise, wake with a clean working set").

One tick: manifest recompute (deterministic re-cert, $0, no model) -> dedup
sweep (audit only — crystallized cards are never rewritten, law 3) -> due
shelf re-checks executed (the recompute step above IS the re-check;
whichever cards were due get their decay clock reset once it confirms
they still hold) -> one SLEEP trip with a morning-readable summary.

`dotmaps sleep`, cron-ready — no arguments, no interaction, no model call.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..bank.certify import certify_all
from ..bank.extractor import bank as bank_extract
from . import reconsolidate
from . import trips as trips_mod

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SKILLS = REPO_ROOT / "skills"
DEFAULT_SEED = REPO_ROOT / "corpus" / "pilot" / "seed-ws"


def _dedup_conflicts(skills_dir: Path) -> list[dict[str, str]]:
    """Audit only — R-DEDUP is the extractor's law (bank/extractor.py);
    sleep never rewrites a crystallized card, it just flags if two ever
    coexist with the same (trigger, method.hash) identity."""
    seen: dict[tuple, str] = {}
    dupes = []
    for f in sorted(Path(skills_dir).glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        key = (tuple(card["trigger"]), card["method"]["hash"])
        if key in seen:
            dupes.append({"a": seen[key], "b": card["name"]})
        else:
            seen[key] = card["name"]
    return dupes


def sleep(skills_dir: Path = DEFAULT_SKILLS, seed: Path = DEFAULT_SEED,
          trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
          now_ts: float | None = None,
          live_root: Path | None = None) -> dict[str, Any]:
    skills_dir = Path(skills_dir)

    # which certified skills are due for a re-check, BEFORE the recompute
    # runs — the recompute below IS the re-check executing.
    due = []
    for f in sorted(skills_dir.glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        if (card.get("certificate", {}).get("status") == "certified"
                and reconsolidate.due_for_recheck(f, now_ts=now_ts)):
            due.append(f.stem)

    # 0. HARVEST (flight-2 gap): extract candidate skills from any live
    #    growth journals into skills/ BEFORE the recompute, so newly grown
    #    primitives get certified this tick and coverage can actually move.
    #    R-DEDUP makes this idempotent; R-STATE means everything enters as
    #    candidate and only the frozen certifier below can promote it.
    harvested = 0
    if live_root is None:
        live_root = trips_mod.REPO_ROOT / "runs" / "queen-live"
    live_root = Path(live_root)
    if live_root.is_dir():
        live_runs = [d for d in sorted(live_root.iterdir())
                     if (d / "primitives").is_dir() or (d / "hypotheses.jsonl").exists()]
        if live_runs:
            before = len(list(skills_dir.glob("*.yaml")))
            bank_extract(live_runs, skills_dir)
            harvested = len(list(skills_dir.glob("*.yaml"))) - before

    # 1. manifest recompute: deterministic, free re-cert of every skill —
    #    coverage/frontier refreshed, no model in the loop.
    certify_all(skills_dir, seed)

    # 2. due shelf re-checks executed: the recompute above already re-
    #    verified them. H6 (HARDENING_BRIEF): the audit's P1 finding —
    #    this used to reset every due card's decay clock and log
    #    action="re-certified" WITHOUT checking whether the post-recert
    #    status actually held. Freshness now resets ONLY on a passing
    #    re-cert; a due card that fails re-cert is convicted, left stale,
    #    and never gets a success trip.
    shelf_trips = []
    convicted = []
    for name in due:
        card_path = skills_dir / f"{name}.yaml"
        fresh = yaml.safe_load(card_path.read_text())
        cert = fresh.get("certificate", {})
        if cert.get("status") == "certified":
            rec = trips_mod.emit("SHELVED", path=trips_path, skill=name,
                                 reason="stability decayed below shelf threshold",
                                 action="re-certified this tick")
            reconsolidate.reset_after_recert(card_path, now_ts=now_ts)
            shelf_trips.append(rec)
        else:
            trips_mod.emit("CONVICTED", path=trips_path, skill=name,
                           reason=(f"due re-cert failed: status={cert.get('status')!r} "
                                   f"({cert.get('oracle_gate')})"),
                           action="left stale — freshness NOT reset, no success trip")
            convicted.append(name)

    # 3. dedup sweep (audit only)
    dupes = _dedup_conflicts(skills_dir)

    manifest = json.loads((skills_dir / "manifest.json").read_text())
    summary = {
        "harvested_candidates": harvested,
        "shelf_rechecks": len(shelf_trips),
        "shelf_recheck_skills": [t["data"]["skill"] for t in shelf_trips],
        "convicted_on_recheck": convicted,
        "dedup_conflicts": dupes,
        "coverage": len(manifest.get("coverage", {})),
        "frontier": len(manifest.get("frontier", [])),
    }
    trips_mod.emit("SLEEP", path=trips_path, **summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(sleep(), indent=2))
