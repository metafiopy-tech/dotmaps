"""CERTIFY — per-skill probe certification (EQUIP spec §2.3, gate G2).

Ordering is law (§2.3b): the ORACLE GATE runs before any certificate math.
A skill whose check cannot fail on a broken environment is not certified —
it is convicted, whatever its pass rate says.

Honesty label: this rung probes by DETERMINISTIC REPLAY of frozen steps.
Certification here covers the frozen-steps execution rung only. The
model-executed rung (a live traveler choosing actions) requires live probes
and its own certification pass — arbitrage rule §2.6: each rung pays its
own toll.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any

import yaml

from dotmaps.grow.banking import break_copy, evaluate, run_steps

THETA_MIN = 0.70   # global floor; per-skill θ from the error-budget function
                   # (§2.3a) activates once frequency/cost columns have data.
PROBE_N = 20
STABILITY_N = 3


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    ph = successes / n
    z2 = z * z
    den = 1 + z2 / n
    ctr = ph + z2 / (2 * n)
    mar = z * math.sqrt((ph * (1 - ph) + z2 / (4 * n)) / n)
    return (max(0.0, (ctr - mar) / den), min(1.0, (ctr + mar) / den))


def oracle_gate(skill: dict, seed: Path) -> tuple[bool, str]:
    """§2.3b — certify the certifier. Three structural checks, in order:
    (1) TERMINATES/PASSES on the intact seed;
    (2) DISCRIMINATES — fails on a broken copy (a check that cannot fail
        is not a check; same conviction logic the bank gate uses);
    (3) STABLE — identical replays return identical verdicts."""
    rule = {"steps": skill["method"]["steps"]}
    check = skill["check"]

    obs = run_steps(rule, seed)
    if not evaluate(check["predicate"], check.get("value"), obs):
        return False, "ORACLE-FAIL: check does not pass on the intact seed"

    with tempfile.TemporaryDirectory() as td:
        broken = Path(td) / "broken"
        break_copy(seed, broken)
        broken_obs = run_steps(rule, broken)
        if evaluate(check["predicate"], check.get("value"), broken_obs):
            return False, ("NON-DISCRIMINATING: check also passes on a "
                           "broken environment")

    verdicts = set()
    for _ in range(STABILITY_N):
        o = run_steps(rule, seed)
        verdicts.add(evaluate(check["predicate"], check.get("value"), o))
    if len(verdicts) != 1:
        return False, "UNSTABLE: identical replays returned mixed verdicts"

    return True, "oracle gate passed (terminates, discriminates, stable)"


def probe(skill: dict, seed: Path, n: int = PROBE_N) -> dict[str, Any]:
    rule = {"steps": skill["method"]["steps"]}
    check = skill["check"]
    successes = 0
    for _ in range(n):
        obs = run_steps(rule, seed)
        if evaluate(check["predicate"], check.get("value"), obs):
            successes += 1
    lo, hi = wilson(successes, n)
    return {"n": n, "successes": successes, "wilson": [round(lo, 3),
                                                       round(hi, 3)]}


def certify_all(skills_dir: Path, seed: Path) -> dict[str, Any]:
    skills_dir, seed = Path(skills_dir), Path(seed)
    results = []
    for f in sorted(skills_dir.glob("*.yaml")):
        skill = yaml.safe_load(f.read_text())
        cert = skill["certificate"]

        ok, verdict = oracle_gate(skill, seed)          # GATE FIRST — always
        cert["oracle_gate"] = verdict
        if not ok:
            cert["status"] = "convicted"
        else:
            p = probe(skill, seed)
            cert.update({"theta": THETA_MIN, "n": p["n"],
                         "wilson": p["wilson"],
                         "probe_mode": "deterministic-replay"})
            cert["status"] = ("certified"
                              if p["wilson"][0] >= THETA_MIN else "candidate")
        f.write_text(yaml.safe_dump(skill, sort_keys=False))
        results.append({"name": skill["name"], "status": cert["status"],
                        "verdict": verdict,
                        "wilson": cert.get("wilson")})

    # regenerate manifest: certified skills move into coverage
    mpath = skills_dir / "manifest.json"
    manifest = json.loads(mpath.read_text())
    coverage, frontier = {}, []
    for f in sorted(skills_dir.glob("*.yaml")):
        skill = yaml.safe_load(f.read_text())
        for entry in manifest["skills"]:
            if entry["name"] == skill["name"]:
                entry["certificate"] = skill["certificate"]
        for t in skill["trigger"]:
            if skill["certificate"]["status"] == "certified":
                coverage[t] = skill["name"]
            else:
                frontier.append(t)
    manifest["coverage"] = coverage
    manifest["frontier"] = sorted(set(frontier))
    manifest["counts"]["certified"] = len(coverage)
    mpath.write_text(json.dumps(manifest, indent=2))
    return {"results": results, "coverage": len(coverage),
            "frontier": len(manifest["frontier"])}


if __name__ == "__main__":
    import sys
    out = certify_all(Path(sys.argv[1]), Path(sys.argv[2]))
    for r in out["results"]:
        print(f"{r['status'].upper():10s} {r['name']}  "
              f"wilson={r['wilson']}  {r['verdict']}")
    print(f"\ncoverage: {out['coverage']}  frontier: {out['frontier']}")
