"""ROUTE — the novelty gate (EQUIP spec §2.4, gate G3).

An equipped traversal: each dot on an incoming map routes through the
manifest. COVERED (a certified skill matches by statement-identity) →
execute the skill's frozen steps and evaluate its own check — no model in
the loop; the certificate stands in for the traveler. FRONTIER (no
certified match) → listed for GROW; nothing is faked.

This is heredity running: what one agent learned in July executes for
free tonight. Cost of a covered dot: $0.00, zero tokens.

H6 (HARDENING_BRIEF): a matched, certified skill is no longer trusted
blind — its formation_context.seed_fingerprint (bank/certify.py) is
compared against the CURRENT workspace being routed. A skill carrying no
fingerprint (a card from before this gate, not yet re-certified) routes
exactly as before — additive, not a breaking change for existing cards.
A skill whose fingerprint no longer matches (the workspace content
changed since certification) routes to frontier instead, with a reason
that says why, until a fresh certify_all() re-certifies it against the
new content.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from dotmaps.grow.banking import evaluate, run_steps
from .certify import fingerprint_workspace


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _load_skills(skills_dir: Path) -> list[dict]:
    return [yaml.safe_load(f.read_text())
            for f in sorted(Path(skills_dir).glob("*.yaml"))]


def match(dot: dict, skills: list[dict]) -> dict | None:
    """Certified-only, exact statement identity. Conservative by design:
    a wrong match executed silently is worse than a frontier verdict.
    Fuzzy/semantic matching is an explicit non-goal at this gate (SRA
    lesson inverted: routing must be auditable, so it must be exact)."""
    target = _norm(dot.get("statement"))
    if not target:
        return None
    for s in skills:
        if s["certificate"]["status"] != "certified":
            continue
        if target == _norm(s.get("statement")):
            return s
    return None


def route_map(map_path: Path, skills_dir: Path, workspace: Path
              ) -> dict[str, Any]:
    m = yaml.safe_load(Path(map_path).read_text())
    skills = _load_skills(skills_dir)
    report = {"map": m.get("name"), "covered": [], "frontier": [],
              "model_calls": 0, "cost_usd": 0.0}

    ws_fingerprint: str | None = None  # computed lazily, at most once
    for dot in m.get("dots", []):
        skill = match(dot, skills)
        if skill is None:
            report["frontier"].append({"dot": dot["id"],
                                       "statement": dot.get("statement"),
                                       "verdict": "FRONTIER → grow"})
            continue

        stored_fp = (skill.get("formation_context") or {}).get("seed_fingerprint")
        if stored_fp is not None:
            if ws_fingerprint is None:
                ws_fingerprint = fingerprint_workspace(workspace)
            if stored_fp != ws_fingerprint:
                report["frontier"].append({
                    "dot": dot["id"], "statement": dot.get("statement"),
                    "verdict": "FRONTIER → grow",
                    "reason": (f"stale formation context — {skill['name']!r} was "
                               f"certified against different content; refusing "
                               f"until it is re-certified"),
                })
                continue

        obs = run_steps({"steps": skill["method"]["steps"]}, Path(workspace))
        ok = evaluate(skill["check"]["predicate"],
                      skill["check"].get("value"), obs)
        report["covered"].append({
            "dot": dot["id"], "skill": skill["name"],
            "wilson": skill["certificate"]["wilson"],
            "passed": bool(ok)})
    return report


if __name__ == "__main__":
    import sys
    r = route_map(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    print(json.dumps(r, indent=2))
