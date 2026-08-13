"""DISPATCH — the queen's core move (QUEEN spec §3.1, §3.3, §4).

READ a compiled map -> ROUTE via bank/route.py (manifest coverage, exact
statement identity, no semantic vibes; unmodified — this module wraps it,
never edits it) -> STAFF a full dispatch PLAN for frontier predicates
(inherited-primitive count via the preequip pattern, a ClockConfig
budget, the learner slot marked "requires Q7 or human-run" — plan only,
never a live model call) -> ESCALATE when a predicate has been SHELVED
twice running without becoming covered.

MONEY LAW: this module performs zero model calls under any circumstance.
The live path is a separate, explicit opt-in (queen/live.py, Q7) that
`dispatch()` does not import.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from ..bank.route import route_map
from ..grow.clock import ClockConfig
from . import reconsolidate
from . import surface as surface_mod
from . import trips as trips_mod

REPO_ROOT = Path(__file__).resolve().parents[3]

PRESETS: dict[str, dict[str, Path]] = {
    # G3's grown pilot map: 4/4 dots covered by certified skills, $0, zero
    # model calls (dotmaps/tests/test_bank_route.py pins this exact result).
    "pilot": {
        "map": REPO_ROOT / "runs" / "grow-005" / "grown-map" / "map.yaml",
        "skills": REPO_ROOT / "skills",
        "workspace": REPO_ROOT / "corpus" / "pilot" / "seed-ws",
    },
    # EQUIP's E1 second map: no certified skill matches yet, all 5 dots
    # route honestly to frontier.
    "migration": {
        "map": REPO_ROOT / "maps" / "map-content-migration" / "map.yaml",
        "skills": REPO_ROOT / "skills",
        "workspace": REPO_ROOT / "corpus" / "pilot" / "seed-ws",
    },
}


def resolve_target(target: str, *, skills: Path | None = None,
                    workspace: Path | None = None) -> dict[str, Any]:
    if target in PRESETS:
        t = dict(PRESETS[target])
        t["name"] = target
    else:
        map_path = Path(target)
        if not map_path.exists():
            raise SystemExit(
                f"no such preset or map file: {target!r} "
                f"(presets: {sorted(PRESETS)})")
        t = {"name": map_path.stem, "map": map_path,
             "skills": REPO_ROOT / "skills",
             "workspace": REPO_ROOT / "corpus" / "pilot" / "seed-ws"}
    if skills is not None:
        t["skills"] = Path(skills)
    if workspace is not None:
        t["workspace"] = Path(workspace)
    return t


def _shelve_id(map_name: str, dot_id: str) -> str:
    return hashlib.sha256(f"{map_name}::{dot_id}".encode()).hexdigest()[:12]


def _count_certified(skills_dir: Path) -> int:
    n = 0
    for f in sorted(Path(skills_dir).glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        if card.get("certificate", {}).get("status") == "certified":
            n += 1
    return n


def _shelve_streak(trips_path: Path, shelve_id: str) -> int:
    """Consecutive SHELVED trips for this predicate since it was last
    CERTIFIED (covered). Resets to 0 the moment coverage lands."""
    n = 0
    for rec in trips_mod.read_all(trips_path):
        data = rec.get("data", {})
        if data.get("id") != shelve_id:
            continue
        if rec["type"] == "SHELVED":
            n += 1
        elif rec["type"] == "CERTIFIED":
            n = 0
    return n


def staff_frontier(map_name: str, frontier_entries: list[dict],
                    skills_dir: Path, cfg: ClockConfig,
                    trips_path: Path) -> list[dict[str, Any]]:
    """Produce the full dispatch PLAN for each frontier predicate: plan
    only, never a live model call (MONEY LAW). Emits one SHELVED trip per
    predicate per dispatch round; escalates once a predicate has shelved
    twice without becoming covered."""
    inherited = _count_certified(skills_dir)
    plan = []
    already_open = {e["id"] for e in surface_mod.open_escalations(trips_path)}
    for entry in frontier_entries:
        dot_id = entry["dot"]
        sid = _shelve_id(map_name, dot_id)
        trips_mod.emit("SHELVED", path=trips_path, id=sid, dot=dot_id,
                       statement=entry.get("statement"), map=map_name,
                       reason="frontier — no certified skill matched; "
                              "staffing plan filed, not grown (dry-run)")
        streak = _shelve_streak(trips_path, sid)
        item = {
            "dot": dot_id,
            "statement": entry.get("statement"),
            "verdict": "FRONTIER → grow",
            "inherited_primitives": inherited,
            "budget": {"max_pokes": cfg.max_pokes,
                       "max_spirals": cfg.max_spirals,
                       "max_fetches": cfg.max_fetches},
            "learner": "requires Q7 or human-run",
            "shelve_streak": streak,
        }
        plan.append(item)
        if streak >= 2 and sid not in already_open:
            surface_mod.escalate(
                sid,
                f"Frontier predicate on '{map_name}' has been shelved "
                f"{streak} times without growth: {entry.get('statement')!r}. "
                f"Grow it now, or keep shelving?",
                ["grow now (requires Q7 or human-run)",
                 "keep shelving",
                 "mark permanently frontier"],
                path=trips_path, dot=dot_id, map=map_name)
    return plan


def check_budget(clock, trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                  **context: Any) -> bool:
    """Wired for future LIVE runs (Q7) — plan-time dispatch never calls
    this, since it never ticks a clock (MONEY LAW: no model calls in the
    default path, so no budget is ever spent here)."""
    if not clock.poke_budget_left():
        trips_mod.emit("BUDGET_EXHAUSTED", path=trips_path,
                       pokes=clock.pokes, max_pokes=clock.cfg.max_pokes,
                       **context)
        return True
    return False


def dispatch(target: str, *, skills: Path | None = None,
             workspace: Path | None = None,
             trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
             cfg: ClockConfig | None = None) -> dict[str, Any]:
    """The dispatcher: READ -> ROUTE -> STAFF -> BUDGET -> ESCALATE."""
    t = resolve_target(target, skills=skills, workspace=workspace)
    cfg = cfg or ClockConfig()

    route_report = route_map(t["map"], t["skills"], t["workspace"])
    map_name = route_report.get("map") or t["name"]

    covered_out = []
    for c in route_report["covered"]:
        sid = _shelve_id(map_name, c["dot"])
        if c["passed"]:
            trips_mod.emit("CERTIFIED", path=trips_path, id=sid, dot=c["dot"],
                           skill=c["skill"], wilson=c["wilson"])
            # C3 — write-on-read: every certified-skill invocation via
            # route updates the card's decay block. Never touches
            # method.steps or check (law 3, self-checked inside touch()).
            skill_path = Path(t["skills"]) / f"{c['skill']}.yaml"
            if skill_path.exists():
                reconsolidate.touch(skill_path, trips_path=trips_path)
        else:
            trips_mod.emit("ORACLE_FAIL", path=trips_path, id=sid, dot=c["dot"],
                           skill=c["skill"],
                           reason="certified skill failed replay on this workspace")
        covered_out.append(c)

    plan = staff_frontier(map_name, route_report["frontier"], t["skills"],
                          cfg, trips_path)

    return {
        "target": t["name"], "map": map_name,
        "covered": covered_out, "frontier": plan,
        "model_calls": route_report["model_calls"],
        "cost_usd": route_report["cost_usd"],
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(dispatch(sys.argv[1]), indent=2))
