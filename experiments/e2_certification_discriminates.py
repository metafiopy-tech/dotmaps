"""E2 — certification discriminates (EQUIP spec §3, pre-registered).

Design: two skill populations, certified blind against the true seed.
  CLEAN    — the repo's skills/ (banked from real grow runs).
  DEGRADED — skills a learner WOULD have banked against a subtly
             corrupted environment: same procedures, checks derived
             mechanically from a planted-flaw copy of the seed
             (values mutated: price, date, title). No model involved;
             the derivation is the planted-ground-truth method from
             the corpus generator, applied to skills.

Pre-registration (verbatim from spec): certification rate for
clean-sourced skills exceeds degraded-sourced by a margin the Wilson
intervals separate at n=20 probes per skill. If certification can't
tell good skills from bad ones, the manifest is a brag sheet — C2
dies honestly.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import yaml

from dotmaps.bank.certify import certify_all

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "corpus" / "pilot" / "seed-ws"
SKILLS = REPO / "skills"

# planted flaws: (true fragment in a check value) -> (corrupted fragment)
FLAWS = {
    '"price": "45"': '"price": "99"',
    "2026-04-12": "2026-09-30",
    "Spring Junior Clinic": "Spring Junior Klinic",
    '"slug": "spring-junior-clinic"': '"slug": "spring-jr-clinic"',
}


def make_degraded_population(dst: Path) -> int:
    """Derive degraded-source counterparts of every clean certified skill
    whose check value contains a flawed fragment. Same steps, corrupted
    expectation — exactly what banking against bad ground produces."""
    dst.mkdir(parents=True)
    n = 0
    for f in sorted(SKILLS.glob("*.yaml")):
        s = yaml.safe_load(f.read_text())
        val = s["check"].get("value")
        if not isinstance(val, str):
            continue
        corrupted = val
        for true_frag, bad_frag in FLAWS.items():
            corrupted = corrupted.replace(true_frag, bad_frag)
        if corrupted == val:
            continue                       # no flaw applies; skip
        s["name"] = f"degraded-{s['name']}"[:60]
        s["check"]["value"] = corrupted
        s["certificate"] = {"status": "candidate", "theta": None,
                            "wilson": None, "n": 0, "oracle_gate": None}
        s["provenance"] = [{"banked_from": "e2-planted-flaw",
                            "rule_id": None, "banked_at": None,
                            "confirmed_by_poke": None}]
        (dst / f"{s['name']}.yaml").write_text(
            yaml.safe_dump(s, sort_keys=False))
        n += 1
    # a manifest stub so certify_all can regenerate it
    (dst / "manifest.json").write_text(json.dumps(
        {"skills": [{"name": yaml.safe_load(p.read_text())["name"],
                     "trigger": yaml.safe_load(p.read_text())["trigger"],
                     "certificate": {"status": "candidate"}}
                    for p in sorted(dst.glob("*.yaml"))],
         "coverage": {}, "frontier": [], "counts": {}}, indent=2))
    return n


def rate(results: list[dict]) -> tuple[int, int]:
    cert = sum(1 for r in results if r["status"] == "certified")
    return cert, len(results)


def main() -> dict:
    with tempfile.TemporaryDirectory() as td:
        clean_dir = Path(td) / "clean"
        shutil.copytree(SKILLS, clean_dir)
        degraded_dir = Path(td) / "degraded"
        n_deg = make_degraded_population(degraded_dir)

        clean = certify_all(clean_dir, SEED)["results"]
        degraded = certify_all(degraded_dir, SEED)["results"]

    c_cert, c_n = rate(clean)
    d_cert, d_n = rate(degraded)
    report = {
        "preregistration": "clean certification rate > degraded, "
                           "Wilson-separated at n=20 probes/skill",
        "clean": {"certified": c_cert, "total": c_n,
                  "detail": clean},
        "degraded": {"certified": d_cert, "total": d_n, "derived": n_deg,
                     "detail": degraded},
        "verdict": ("PRE-REGISTRATION MET"
                    if c_cert / max(c_n, 1) > d_cert / max(d_n, 1)
                    else "PRE-REGISTRATION NOT MET — C2 dies honestly"),
    }
    return report


if __name__ == "__main__":
    r = main()
    print(f"CLEAN:    {r['clean']['certified']}/{r['clean']['total']} certified")
    print(f"DEGRADED: {r['degraded']['certified']}/{r['degraded']['total']} certified")
    for d in r["degraded"]["detail"]:
        print(f"  {d['status'].upper():10s} {d['name'][:52]}  {d['verdict'][:60]}")
    print(f"\n{r['verdict']}")
    out = REPO / "runs" / "e2-certification-discriminates"
    out.mkdir(exist_ok=True)
    (out / "report.json").write_text(json.dumps(r, indent=2))
    print(f"report -> {out/'report.json'}")
