"""BANK — skill extraction from grow-run journals (EQUIP spec §2.2, gate G1).

FROZEN RUBRIC (R1 output — change requires a spec revision, not a commit):
  R-UNIT   one skill per banked primitive: the smallest replayable procedure
           satisfying exactly one trigger predicate. Composition happens at
           assembly time (§2.5), never inside a skill.
  R-CHECK  a skill carries its own check: the banked rule's `expect` block is
           the skill's self-verification. No expect, no skill.
  R-REPLAY method = the rule's `steps`, verbatim. If steps are empty or
           reference tools outside the run's tool surface, the candidate is
           rejected (not repaired — repair is unfrozen judgment).
  R-REQ    `requires` is derived mechanically from the tools in `steps`.
  R-PROV   provenance is mandatory: source run, rule id, banked_at. A skill
           with no provenance is a rumor.
  R-DEDUP  identity = (trigger, method_hash). A duplicate appends provenance
           to the existing skill instead of minting a new one — the
           anti-Voyager rule: the library measures redundancy instead of
           accumulating it.
  R-STATE  every extracted skill enters as `candidate`. Certification is a
           separate gate (G2) run by the frozen probe instrument; the
           extractor NEVER writes `certified`.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


def _slug(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].rstrip("-") or "skill"


def _method_hash(steps: list[dict], expect: dict) -> str:
    """Identity = procedure AND check. Two rules reading the same file for
    different predicates/values are different skills (bug found on first
    extraction: 23 rules wrongly merged to 2 when expect was excluded)."""
    return hashlib.sha256(
        json.dumps({"steps": steps, "expect": expect},
                   sort_keys=True).encode()
    ).hexdigest()[:12]


def _trigger(rule: dict) -> str:
    """Trigger predicate key: <subject>::<predicate>. Subject is the primary
    resource the first step touches; predicate is the expect predicate class.
    Exact-match routing (SRA lesson: retrieval, not vibes)."""
    step0 = rule["steps"][0]
    args = step0.get("args", {}) or {}
    subject = args.get("path") or args.get("url") or step0.get("tool", "?")
    val = rule["expect"].get("value")
    vh = hashlib.sha256(json.dumps(val, sort_keys=True).encode()
                        ).hexdigest()[:8] if val not in (None, True) else "any"
    return f"{subject}::{rule['expect']['predicate']}::{vh}"


def extract_run(run_dir: Path) -> list[dict[str, Any]]:
    """Mine one grow run for skill candidates. Sources, in trust order:
    primitives/*.yaml (bank-gated) first; hypotheses.jsonl `banked` events as
    fallback for runs that predate the primitives directory."""
    run_dir = Path(run_dir)
    rules: list[dict] = []

    prim_dir = run_dir / "primitives"
    if prim_dir.is_dir():
        for f in sorted(prim_dir.glob("*.yaml")):
            rules.append(yaml.safe_load(f.read_text()))
    else:
        hyp = run_dir / "hypotheses.jsonl"
        if hyp.exists():
            proposed: dict[str, dict] = {}
            banked_ids: list[str] = []
            for line in hyp.read_text().splitlines():
                if not line.strip():
                    continue
                ev = json.loads(line)
                if ev.get("event") == "proposed":
                    proposed[ev["rule"]["id"]] = ev["rule"] | {
                        "banked_at": ev.get("t")}
                elif ev.get("event") == "banked":
                    banked_ids.append(ev["rule_id"])
            rules = [proposed[i] for i in banked_ids if i in proposed]

    out: list[dict[str, Any]] = []
    for rule in rules:
        # R-CHECK + R-REPLAY gates
        if not rule.get("expect") or not rule.get("steps"):
            continue
        card = {
            "name": _slug(rule.get("statement", rule.get("id", "skill"))),
            "statement": rule.get("statement"),
            "trigger": [_trigger(rule)],
            "method": {"steps": rule["steps"],
                       "hash": _method_hash(rule["steps"], rule["expect"])},
            "check": rule["expect"],                       # R-CHECK
            "requires": {"tools": sorted({s["tool"] for s in rule["steps"]})},
            "provenance": [{
                "banked_from": run_dir.name,
                "rule_id": rule.get("id"),
                "banked_at": rule.get("banked_at"),
                "confirmed_by_poke": rule.get("confirmed_by_poke"),
            }],
            "certificate": {"status": "candidate", "theta": None,
                            "wilson": None, "n": 0, "oracle_gate": None},
            "decay": {"last_used": None, "stability": None,
                      "shelf_recheck": None},
        }
        out.append(card)
    return out


def bank(run_dirs: list[Path], skills_dir: Path) -> dict[str, Any]:
    """Extract across runs with R-DEDUP; write skills/ + manifest.json."""
    skills_dir = Path(skills_dir)
    skills_dir.mkdir(parents=True, exist_ok=True)
    by_identity: dict[tuple, dict] = {}

    for rd in run_dirs:
        for card in extract_run(Path(rd)):
            key = (card["trigger"][0], card["method"]["hash"])
            if key in by_identity:                          # R-DEDUP
                by_identity[key]["provenance"].extend(card["provenance"])
            else:
                by_identity[key] = card

    # resolve name collisions across distinct identities
    seen: dict[str, int] = {}
    for card in by_identity.values():
        n = seen.get(card["name"], 0)
        seen[card["name"]] = n + 1
        if n:
            card["name"] = f"{card['name']}-{n+1}"
        (skills_dir / f"{card['name']}.yaml").write_text(
            yaml.safe_dump(card, sort_keys=False))

    cards = list(by_identity.values())
    manifest = {
        "skills": [{"name": c["name"], "trigger": c["trigger"],
                    "certificate": c["certificate"]} for c in cards],
        # coverage lists ONLY certified skills — empty until G2 runs.
        "coverage": {},
        # every candidate trigger is frontier until its skill certifies.
        "frontier": sorted({t for c in cards for t in c["trigger"]}),
        "counts": {"skills": len(cards),
                   "provenance_entries": sum(len(c["provenance"])
                                             for c in cards),
                   "dedup_merges": sum(len(c["provenance"]) - 1
                                       for c in cards)},
    }
    (skills_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    import sys
    dirs = [Path(p) for p in sys.argv[1:-1]]
    print(json.dumps(bank(dirs, Path(sys.argv[-1]))["counts"], indent=2))
