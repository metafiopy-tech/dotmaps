"""Q3 backtest — "history grades her before any live run does."

Scans the ARCHIVED e1b/e1c/e1d hypothesis journals under runs/ (frozen,
read-only, never edited — frozen law #2) and:

  1. computes the persistence-budget constant: the 75th percentile of
     pokes-before-first-bank across every hypothesis family that
     ultimately banked, pooled across all three experiments (52 runs).
  2. reproduces the published verdicts retroactively, at the SAME grain
     the verdicts themselves were graded on (refog counts — a normalized
     statement fogged under more than one rule id within a run — not an
     invented proxy):
       - e1c shows refogs > 0 — e1c-verdict recorded the in-flight-race
         churn ("gate inert 0/10... in-flight race confirmed by
         elimination");
       - e1d shows refogs == 0 across all runs — e1d-verdict's own words,
         "refog=0 in ALL 16 runs; 99 in-flight blocks; churn ELIMINATED".
     Separately (governor calibration, not verdict-reproduction): the
     GOVERNED assess() (churn_test + persistence-budget counterweight)
     must produce ZERO false WALL verdicts on e1d's banked families — a
     family that in fact banked was never "a wall".

Writes runs/governor-backtest/report.json. Exit 0 iff both reproductions
hold; the number this script prints for the persistence budget is the one
hand-copied into queen/governor.py's PERSISTENCE_BUDGET_POKES, with this
file as its cited provenance (frozen law #6: backtested, not invented).

Usage: python experiments/governor_backtest.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"

import sys
sys.path.insert(0, str(REPO / "dotmaps"))
from dotmaps.queen.governor import assess, classify_category  # noqa: E402


def iter_run_dirs(prefix: str) -> list[Path]:
    out = []
    for p in sorted(RUNS.glob(f"{prefix}-*")):
        if not p.is_dir():
            continue
        if "VOID" in p.name or "verdict" in p.name:
            continue
        if (p / "hypotheses.jsonl").exists():
            out.append(p)
    return out


def hypothesis_families(run_dir: Path) -> dict[str, dict[str, Any]]:
    """id -> {statement, outcome, attempts, fail_categories, pokes_before_bank}"""
    proposed: dict[str, str] = {}
    outcome: dict[str, str] = {}
    for line in (run_dir / "hypotheses.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev["event"] == "proposed":
            proposed[ev["rule"]["id"]] = ev["rule"].get("statement")
        else:
            outcome[ev["rule_id"]] = ev["event"]

    attempts: dict[str, int] = {rid: 0 for rid in proposed}
    fail_categories: dict[str, list[str]] = {rid: [] for rid in proposed}
    pokes_before_bank: dict[str, int] = {}

    poke_path = run_dir / "poke_journal.jsonl"
    if poke_path.exists():
        for line in poke_path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            action = rec.get("action", {})
            if action.get("tool") not in ("confirm", "confirm-revised"):
                continue
            rid = (action.get("args") or {}).get("id")
            if rid not in proposed or rid in pokes_before_bank:
                continue  # unknown id, or family already resolved-banked
            attempts[rid] += 1
            obs = rec.get("observation", "")
            if obs.startswith("CONFIRMED"):
                pokes_before_bank[rid] = attempts[rid]
            else:
                cat = classify_category(obs)
                if cat:
                    fail_categories[rid].append(cat)

    return {
        rid: {"statement": statement, "outcome": outcome.get(rid, "open"),
              "attempts": attempts[rid], "fail_categories": fail_categories[rid],
              "pokes_before_bank": pokes_before_bank.get(rid)}
        for rid, statement in proposed.items()
    }


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (pct / 100)
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return s[f] + (s[c] - s[f]) * (k - f)


def compute_persistence_budget() -> dict[str, Any]:
    all_pokes: list[int] = []
    per_prefix: dict[str, list[int]] = {}
    for prefix in ("e1b", "e1c", "e1d"):
        vals = []
        for rd in iter_run_dirs(prefix):
            for f in hypothesis_families(rd).values():
                if f["outcome"] == "banked" and f["pokes_before_bank"]:
                    vals.append(f["pokes_before_bank"])
        per_prefix[prefix] = vals
        all_pokes.extend(vals)
    return {"n": len(all_pokes), "p75": percentile(all_pokes, 75),
            "per_prefix_n": {k: len(v) for k, v in per_prefix.items()},
            "raw_sample_sorted": sorted(all_pokes)}


def _normalize(text: str | None) -> str:
    import re
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def refog_count(run_dir: Path) -> dict[str, Any]:
    """A statement REFOGS when it gets fogged under more than one distinct
    rule_id within a run — the exact phenomenon e1c/e1d verdicts measured
    (e1d-verdict.json: 'refog=0 in ALL 16 runs')."""
    proposed: dict[str, str] = {}
    fogged_ids: set[str] = set()          # a rule_id can log BOTH a
                                          # fog-blocked and a fogged event
                                          # for its own single resolution
                                          # (runner.py _forage: the block
                                          # path doesn't skip the terminal
                                          # fog) — dedupe by id, since
                                          # refog means DISTINCT ids, not
                                          # one id logged twice.
    for line in (run_dir / "hypotheses.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev["event"] == "proposed":
            proposed[ev["rule"]["id"]] = ev["rule"].get("statement")
        elif ev["event"] in ("fogged", "fog-blocked"):
            fogged_ids.add(ev["rule_id"])

    by_stmt: dict[str, list[str]] = {}
    for rid in sorted(fogged_ids):
        stmt = _normalize(proposed.get(rid))
        if stmt:
            by_stmt.setdefault(stmt, []).append(rid)
    refogs = {s: ids for s, ids in by_stmt.items() if len(ids) >= 2}
    return {"run": run_dir.name, "refog_statements": len(refogs), "detail": refogs}


def reproduce_verdicts() -> dict[str, Any]:
    e1c_refogs = [refog_count(rd) for rd in iter_run_dirs("e1c")]
    e1c_total = sum(r["refog_statements"] for r in e1c_refogs)
    e1d_refogs = [refog_count(rd) for rd in iter_run_dirs("e1d")]
    e1d_total = sum(r["refog_statements"] for r in e1d_refogs)

    # governor calibration (separate from verdict-reproduction above): the
    # GOVERNED assess() — churn_test + persistence-budget counterweight —
    # must never call WALL on a family that in fact went on to bank.
    e1d_false_wall = []
    for rd in iter_run_dirs("e1d"):
        for rid, f in hypothesis_families(rd).items():
            if f["outcome"] == "banked" and len(f["fail_categories"]) >= 2:
                v = assess(f["fail_categories"], f["attempts"])
                if v["verdict"] == "WALL":
                    e1d_false_wall.append({"run": rd.name, "id": rid,
                                           "statement": f["statement"], **v})

    return {
        "e1c_refog_total": e1c_total,
        "e1c_refog_by_run": [r for r in e1c_refogs if r["refog_statements"]],
        "e1d_refog_total": e1d_total,
        "e1d_refog_by_run": [r for r in e1d_refogs if r["refog_statements"]],
        "churn_reproduced": e1c_total > 0 and e1d_total == 0,
        "e1d_false_wall_count": len(e1d_false_wall),
        "e1d_false_wall": e1d_false_wall,
    }


def run_backtest() -> dict[str, Any]:
    budget = compute_persistence_budget()
    verdicts = reproduce_verdicts()
    passed = verdicts["churn_reproduced"] and verdicts["e1d_false_wall_count"] == 0
    report = {
        "registration": __doc__.strip().splitlines()[0],
        "persistence_budget": budget,
        "verdict_reproduction": verdicts,
        "pass": passed,
    }
    out = RUNS / "governor-backtest" / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    r = run_backtest()
    print(json.dumps(r, indent=2))
    print(f"\npersistence budget (p75 pokes-before-first-bank, n={r['persistence_budget']['n']}): "
          f"{r['persistence_budget']['p75']}")
    print(f"verdict reproduction: {'PASS' if r['pass'] else 'FAIL'}")
    raise SystemExit(0 if r["pass"] else 1)
