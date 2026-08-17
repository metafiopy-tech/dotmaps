"""WORKFLOWS — Tab 4: the named, human-level plays she owns, distinct from
atomic skills (a skill is one fact; a workflow is a job made of dots plus
its coverage state). Two sources, one list:

  SEED       hand-authored at ship (pilot, migration) — trigger phrases are
             the plain-English asks a keeper would actually type in chat.
  CHAT-BORN  discovered at runtime: every `maps/map-chat-*/chat_trigger.json`
             a confirmed "yes, learn it" (queen/chat.py) has written. No
             registry file to keep in sync — the map directories themselves
             are the source of truth, same "no parallel stores" law as
             everything else in this package.

`match_trigger()` is chat.py's ROUTE FIRST: a normalized substring match
against every known phrase, mechanical, zero model calls.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..bank.route import route_map
from . import dispatch as dispatch_mod
from . import trips as trips_mod

REPO_ROOT = trips_mod.REPO_ROOT
DEFAULT_MAPS_DIR = REPO_ROOT / "maps"

SEED_WORKFLOWS: list[dict[str, Any]] = [
    {
        "name": "check-demo-workspace",
        "title": "Check the demo workspace",
        "description": "Confirms the sample workspace's files are exactly "
                        "what she expects — every check she already knows.",
        "kind": "seed",
        "target": "pilot",
        "trigger_phrases": [
            "check the demo workspace", "check demo workspace",
            "check the pilot", "is the demo workspace ok",
            "check the sample workspace", "check the sample data",
        ],
    },
    {
        "name": "migrate-the-menu-data",
        "title": "Migrate the menu data",
        "description": "Moves the golf shop's class listings into the new "
                        "format and checks every field landed correctly.",
        "kind": "seed",
        "target": "migration",
        "trigger_phrases": [
            "migrate the menu data", "migrate the menu",
            "run the migration", "do the migration",
            "migrate the class listings",
        ],
    },
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _chat_born(maps_dir: Path) -> list[dict[str, Any]]:
    maps_dir = Path(maps_dir)
    out = []
    if not maps_dir.is_dir():
        return out
    for d in sorted(maps_dir.glob("map-chat-*")):
        sidecar = d / "chat_trigger.json"
        if not sidecar.exists():
            continue
        info = json.loads(sidecar.read_text())
        out.append({
            "name": d.name,
            "title": info.get("statement") or info.get("trigger") or d.name,
            "description": info.get("answer") or "Learned from a chat conversation.",
            "kind": "chat",
            "target": f"{d.name}/map.yaml",
            "trigger_phrases": [info.get("trigger")] if info.get("trigger") else [],
        })
    return out


def all_workflows(maps_dir: Path = DEFAULT_MAPS_DIR) -> list[dict[str, Any]]:
    return [*SEED_WORKFLOWS, *_chat_born(maps_dir)]


def find(name: str, maps_dir: Path = DEFAULT_MAPS_DIR) -> dict[str, Any] | None:
    for wf in all_workflows(maps_dir):
        if wf["name"] == name:
            return wf
    return None


def match_trigger(message: str, maps_dir: Path = DEFAULT_MAPS_DIR
                  ) -> dict[str, Any] | None:
    """Mechanical, no model: does the message contain a known trigger
    phrase? First match wins; seed workflows are checked before chat-born
    ones (a hand-authored play should never be shadowed by a coincidental
    learned phrase)."""
    norm = _norm(message)
    for wf in all_workflows(maps_dir):
        for phrase in wf["trigger_phrases"]:
            if phrase and _norm(phrase) in norm:
                return wf
    return None


def coverage(wf: dict[str, Any], skills_dir: Path,
             maps_dir: Path = DEFAULT_MAPS_DIR) -> dict[str, Any]:
    """{"covered": n, "total": m} — the coverage bar's raw numbers.
    Never emits a trip: reads route_map() directly, same discipline as
    ui.py's manifest_state()."""
    target = wf["target"]
    try:
        if wf["kind"] == "chat":
            t = dispatch_mod.resolve_target(str(Path(maps_dir) / target), skills=skills_dir)
        else:
            t = dispatch_mod.resolve_target(target, skills=skills_dir)
        r = route_map(t["map"], t["skills"], t["workspace"])
        return {"covered": len(r["covered"]), "total": len(r["covered"]) + len(r["frontier"])}
    except Exception as e:  # a map fixture may be missing in a fresh checkout
        return {"covered": 0, "total": 0, "error": str(e)}


def _last_run(wf: dict[str, Any], trips_path: Path) -> str | None:
    """Most recent trip touching this workflow's map name, if any."""
    last = None
    for rec in trips_mod.read_all(trips_path):
        data = rec.get("data", {})
        if data.get("map") == wf["name"] or data.get("target") == wf["name"]:
            last = rec["t"]
    return last


def payload(skills_dir: Path, maps_dir: Path = DEFAULT_MAPS_DIR,
            trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> list[dict[str, Any]]:
    """The Workflows tab's list: one row per play, plain sentence, coverage
    bar, last run, ready for a RUN button."""
    out = []
    for wf in all_workflows(maps_dir):
        cov = coverage(wf, skills_dir, maps_dir)
        out.append({
            "name": wf["name"], "title": wf["title"],
            "description": wf["description"], "kind": wf["kind"],
            "covered": cov["covered"], "total": cov["total"],
            "last_run": _last_run(wf, trips_path),
        })
    return out


if __name__ == "__main__":
    print(json.dumps(payload(REPO_ROOT / "skills"), indent=2))
