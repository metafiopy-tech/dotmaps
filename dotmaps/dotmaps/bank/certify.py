"""CERTIFY — per-skill probe certification (EQUIP spec §2.3, gate G2).

Ordering is law (§2.3b): the ORACLE GATE runs before any certificate math.
A skill whose check cannot fail on a broken environment is not certified —
it is convicted, whatever its pass rate says. `oracle_gate()`'s body is
frozen (queen/assure.py's check_frozen_files_unchanged pins its exact
bytes) — H5's changes below live entirely in probe()/certify_all(), which
are not part of that frozen block.

Honesty label: this rung probes by DETERMINISTIC REPLAY of frozen steps.
Certification here covers the frozen-steps execution rung only. The
model-executed rung (a live traveler choosing actions) requires live probes
and its own certification pass — arbitrage rule §2.6: each rung pays its
own toll.

H5 (HARDENING_BRIEF), two audit findings fixed together (they're the same
root cause — one shared seed copy):
  (1) statistical honesty — 20 "probes" replaying byte-identical frozen
      steps against ONE shared seed copy are 20 samples of a point mass,
      not 20 independent trials; a Wilson interval there overclaims
      statistical confidence. `regime="deterministic-consistency"` says so
      plainly, and certification now requires successes == n (a single
      failure among identical deterministic replays means non-determinism,
      which disqualifies — not "70% reliable"). `wilson` is still computed
      and stored (kept for callers that already read it — dispatch.py,
      ui.py — as a derived statistic) but no longer decides `status` for
      this regime.
  (2) order-dependence — certify_all() previously copied the seed ONCE and
      reused it across every skill AND every probe, so a mutating skill
      could leave state a later skill's certification then read. Both
      certify_all() (per skill) and probe() (per probe) now copy a fresh,
      disposable seed every time — cheap at this repo's seed size, and it
      makes "reorder skill files -> identical certificates" true by
      construction rather than by luck.
"""
from __future__ import annotations

import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from dotmaps.grow.banking import break_copy, evaluate, run_steps

THETA_MIN = 0.70   # global floor; per-skill θ from the error-budget function
                   # (§2.3a) activates once frequency/cost columns have data.
PROBE_N = 20
STABILITY_N = 3

REGIME_DETERMINISTIC = "deterministic-consistency"  # H5: this rung's honest label


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    ph = successes / n
    z2 = z * z
    den = 1 + z2 / n
    ctr = ph + z2 / (2 * n)
    mar = z * math.sqrt((ph * (1 - ph) + z2 / (4 * n)) / n)
    return (max(0.0, (ctr - mar) / den), min(1.0, (ctr + mar) / den))


def _fresh_copy(seed: Path, prefix: str) -> Path:
    """A brand-new disposable copy of `seed`, every call — H5's isolation
    fix: nothing that runs against the returned path can ever influence
    anything that runs against a DIFFERENT call's copy. Placed ABOVE the
    gate function on purpose: assure.py's frozen-bytes check hashes the
    gate function's own span verbatim, so nothing new may land inside it."""
    tmp = Path(tempfile.mkdtemp(prefix=prefix))
    dst = tmp / "seed"
    shutil.copytree(Path(seed), dst)
    return dst


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
    """H5: a FRESH disposable copy per probe — not the same shared copy
    replayed n times — so a mutation in probe i can never be read back by
    probe i+1. successes/wilson are still reported (wilson kept as a
    derived statistic, see module docstring); `regime` names what this
    actually is: deterministic replay, not independent sampling."""
    rule = {"steps": skill["method"]["steps"]}
    check = skill["check"]
    successes = 0
    for _ in range(n):
        copy = _fresh_copy(seed, "certify-probe-")
        obs = run_steps(rule, copy)
        if evaluate(check["predicate"], check.get("value"), obs):
            successes += 1
    lo, hi = wilson(successes, n)
    return {"n": n, "successes": successes, "wilson": [round(lo, 3), round(hi, 3)],
            "regime": REGIME_DETERMINISTIC,
            "consistency": f"{successes}/{n} deterministic replays"}


def certify_all(skills_dir: Path, seed: Path) -> dict[str, Any]:
    """Runs each skill against its OWN fresh, disposable copy of the seed
    (H5: order-dependence fix — a mutating skill's writes can no longer
    leak into a later skill's certification, whatever file order they're
    processed in). Harvested skills may contain write steps (e.g.
    flight-2's r004 creates target_items.json), so certification must
    never mutate the repo's seed workspace, and now never mutate a shared
    copy either. The oracle-gate ordering below is unchanged."""
    skills_dir = Path(skills_dir)
    results = []
    for f in sorted(skills_dir.glob("*.yaml")):
        skill = yaml.safe_load(f.read_text())
        cert = skill["certificate"]
        skill_seed = _fresh_copy(seed, "certify-skill-")

        ok, verdict = oracle_gate(skill, skill_seed)     # GATE FIRST — always
        cert["oracle_gate"] = verdict
        if not ok:
            cert["status"] = "convicted"
        else:
            p = probe(skill, skill_seed)
            cert.update({"theta": THETA_MIN, "n": p["n"],
                         "wilson": p["wilson"], "regime": p["regime"],
                         "consistency": p["consistency"],
                         "probe_mode": "deterministic-replay"})
            # H5: for a deterministic-replay regime, the honest promotion
            # rule is "every replay held" — a Wilson-lower-bound-vs-THETA_MIN
            # comparison implies statistical sampling this regime doesn't
            # have. A single failure among identical deterministic replays
            # means non-determinism/flakiness, which disqualifies outright.
            cert["status"] = "certified" if p["successes"] == p["n"] else "candidate"
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
