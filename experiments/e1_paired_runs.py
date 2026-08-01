"""E1 — the reuse delta (EQUIP spec §3; THE BALLGAME). Turnkey harness.

REQUIRES A LIVE LEARNER — run this on a machine with ollama or an API key.
This file only wires the arms; it fabricates nothing.

Design (pre-registered, verbatim from spec):
  Two related tasks sharing domain: task A = the pilot seed (already grown,
  runs/grow-001..005), task B = a fresh grow against the same workspace
  family toward the content-migration predicates (the five statements the
  novelty gate routed to FRONTIER on 2026-07-31 — E1's second map, labeled
  by the gate itself).

  ARM COLD:      fresh store, learner grows B from nothing.
  ARM EQUIPPED:  store pre-banked with every CERTIFIED skill from the
                 manifest (bank_primitive of each skill's source rule,
                 provenance preserved) — the learner starts where the
                 colony finished. Everything else identical: same seed,
                 same ClockConfig, same learner, same directive.

  Measure per arm: pokes used, fetches used, primitives banked, fog count,
  wall-clock, learner cost, and readout result (R1 gates + dot count).

  SUCCESS (pre-registered): across 5 paired runs, EQUIPPED shows >=30%
  poke-budget reduction OR a readout outcome COLD fails to reach.
  KILL: if EQUIPPED <= COLD across 5 pairs, BANK as designed is dead
  weight — publish the negative, redesign the skill unit before further
  build.

Usage:
  python experiments/e1_paired_runs.py --arm cold     --run-dir runs/e1-cold-01
  python experiments/e1_paired_runs.py --arm equipped --run-dir runs/e1-eq-01
  (repeat x5 pairs; then python experiments/e1_paired_runs.py --report runs/e1-*)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "corpus" / "pilot" / "seed-ws"
SKILLS = REPO / "skills"


def preequip(store) -> int:
    """Bank every certified skill's source rule into a fresh store.
    Heredity, mechanically: the equipped learner's board opens with the
    colony's certified knowledge already on it."""
    n = 0
    for f in sorted(SKILLS.glob("*.yaml")):
        s = yaml.safe_load(f.read_text())
        if s["certificate"]["status"] != "certified":
            continue
        rule = {"id": f"inherited-{n:03d}",
                "statement": s["statement"],
                "steps": s["method"]["steps"],
                "expect": s["check"],
                "inherited_from": s["name"],
                "inherited_wilson": s["certificate"]["wilson"]}
        store.bank_primitive(rule, journal_ref=0, spiral=0)
        n += 1
    return n


def run_arm(arm: str, run_dir: Path, learner) -> dict:
    from dotmaps.grow.runner import grow
    from dotmaps.grow.store import GrowStore
    from dotmaps.grow.clock import ClockConfig

    store = GrowStore(run_dir)
    inherited = preequip(store) if arm == "equipped" else 0

    t0 = time.time()
    summary = grow(SEED, run_dir, learner, cfg=ClockConfig())
    dt = time.time() - t0

    result = {"arm": arm, "run_dir": str(run_dir), "inherited": inherited,
              "wall_clock_s": round(dt, 1), "summary": summary}
    if hasattr(learner, "usd_estimate"):
        result["learner_usd_estimate"] = round(learner.usd_estimate, 4)
    (Path(run_dir) / "e1_arm.json").write_text(json.dumps(result, indent=2))
    return result


def report(run_dirs: list[Path]) -> None:
    rows = [json.loads((Path(d) / "e1_arm.json").read_text())
            for d in run_dirs if (Path(d) / "e1_arm.json").exists()]
    cold = [r for r in rows if r["arm"] == "cold"]
    eq = [r for r in rows if r["arm"] == "equipped"]
    print(f"pairs: cold={len(cold)} equipped={len(eq)}")
    for r in rows:
        print(f"  {r['arm']:9s} {r['run_dir']}  "
              f"inherited={r['inherited']}  t={r['wall_clock_s']}s")
    print("\nGrade against the pre-registration in this file's docstring. "
          "Compute poke reduction from each run's novelty.jsonl; "
          "publish MET or NOT MET either way.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["cold", "equipped"])
    ap.add_argument("--run-dir")
    ap.add_argument("--driver", choices=["anthropic", "ollama"],
                    default="anthropic")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--report", nargs="*")
    args = ap.parse_args()

    if args.report is not None:
        report([Path(p) for p in args.report])
    else:
        if not (args.arm and args.run_dir):
            raise SystemExit("need --arm and --run-dir (or --report)")
        # identical wiring to `dotmaps grow` (cli.py) — run-005's lineage
        from dotmaps.grow.learner import AnthropicLearner, OllamaLearner
        learner = (AnthropicLearner(model=args.model)
                   if args.driver == "anthropic"
                   else OllamaLearner(model=args.model))
        result = run_arm(args.arm, Path(args.run_dir), learner)
        if hasattr(learner, "usd_estimate"):
            result["learner_usd_estimate"] = round(learner.usd_estimate, 4)
        print(json.dumps({k: v for k, v in result.items()
                          if k != "summary"}, indent=2))
