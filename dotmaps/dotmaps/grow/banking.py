"""Rule banking — the core mechanic of the POKE loop.

A rule is a DECLARATIVE claim about the environment:

    {"id": "r003",
     "statement": "the source export holds 5 items",
     "steps": [{"tool": "filesystem.read_file",
                "args": {"path": "source_items.json"}}],
     "expect": {"predicate": "json_item_count", "value": 5}}

Banking = replay the steps against a FRESH copy of the seed environment
(never the agent's working copy — self-referential rules must not confirm)
through the same ToolBox walls the agent pokes through, then evaluate the
predicate on the FINAL observation. Confirmed -> primitive. Not -> hypothesis
stays open.

Dot-eligibility: a rule can grow into a dot only if its FINAL step is
read-only — the dot promises a STATE, its verifier OBSERVES that state, and
achieving it is the sandbox traveler's job. Wall-facts (predicate "blocked")
bank as primitives but never become dots. The verifier script is compiled
from the spec by a deterministic template; the learner never writes code.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..models import Map
from ..runtime.traveler import ScopeViolation, ToolBox, WallViolation

READ_ONLY_TOOLS = {"filesystem.read_file", "fetch.get"}
PREDICATES = {"contains", "equals", "json_item_count", "json_parses", "blocked"}
GROW_TOOLS = ("filesystem.read_file", "filesystem.write_file", "fetch.get")


def grow_env_map(name: str = "grow-env") -> Map:
    """A synthetic map that exists only to parameterize the walls the learner
    pokes through: read, write, fetch — nothing else (no delete; the Stage-0
    lesson applies to learners too)."""
    from ..models import Budget, TravelerConfig
    return Map(name=name, version="0", domain="grow",
               mcp_required=GROW_TOOLS,
               budget=Budget.from_dict(None),
               traveler=TravelerConfig.from_dict(None),
               dots=(), root=None)


def validate_rule(rule: dict[str, Any]) -> str | None:
    """Structural check on a proposed rule. Returns a problem string or None."""
    if not isinstance(rule.get("statement"), str) or not rule["statement"].strip():
        return "rule needs a non-empty statement"
    steps = rule.get("steps")
    if not isinstance(steps, list) or not steps:
        return "rule needs a non-empty steps list"
    for s in steps:
        if not isinstance(s, dict) or "tool" not in s:
            return "each step needs a tool"
        if s["tool"] not in GROW_TOOLS:
            return f"step tool {s.get('tool')!r} is outside the grow action space"
        if not isinstance(s.get("args"), dict):
            return "each step needs an args object"
    exp = rule.get("expect")
    if not isinstance(exp, dict) or exp.get("predicate") not in PREDICATES:
        return f"expect.predicate must be one of {sorted(PREDICATES)}"
    return None


def evaluate(predicate: str, value: Any, observation: str) -> bool:
    if predicate == "blocked":
        return observation.startswith("BLOCKED")
    if predicate == "contains":
        return str(value) in observation
    if predicate == "equals":
        return observation.strip() == str(value).strip()
    if predicate == "json_parses":
        try:
            json.loads(observation)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    if predicate == "json_item_count":
        try:
            return len(json.loads(observation)) == int(value)
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
    return False


def run_steps(rule: dict[str, Any], workspace: Path) -> str:
    """Execute the rule's steps through the walls; return the final observation."""
    tools = ToolBox(grow_env_map(), workspace)
    obs = ""
    for step in rule["steps"]:
        try:
            obs = str(tools.call(step["tool"], **step["args"]))
        except (WallViolation, ScopeViolation) as e:
            obs = f"BLOCKED: {e}"
        except Exception as e:
            obs = f"ERROR: {e}"
    return obs


def break_copy(seed_dir: Path, dst: Path) -> None:
    """A deliberately broken environment: every top-level JSON emptied, every
    text file truncated. Shared by bank-time gating and the readout."""
    shutil.copytree(seed_dir, dst)
    for p in dst.iterdir():
        if p.suffix == ".json":
            p.write_text("[]")
        elif p.is_file():
            p.write_text("")


def already_fogged(rule: dict[str, Any], fogged: list[str]) -> bool:
    """E1b finding F-E1b-1: mechanical gates beat informational surfacing.
    M2 failed (5/10 runs) because fog on the board is advice the learner can
    ignore mid-burst; this gates re-proposals of fogged statements at the
    action site, exactly where already_banked went 10/10. Identity =
    normalized statement (the metric M2 was graded on)."""
    import re as _re
    norm = lambda t: _re.sub(r"\s+", " ", (t or "").strip().lower())
    target = norm(rule.get("statement"))
    return bool(target) and target in {norm(f) for f in fogged}


def already_banked(rule: dict[str, Any], existing: list[dict]) -> str | None:
    """E1 finding F-E1a: duplicates ate up to a third of a run's output.
    Identity = steps + expect (same rule as the BANK extractor). Returns the
    existing rule id if this candidate is a duplicate."""
    import hashlib as _h
    key = _h.sha256(_json_dumps(rule).encode()).hexdigest()
    for ex in existing:
        if _h.sha256(_json_dumps(ex).encode()).hexdigest() == key:
            return ex.get("id", "?")
    return None


def _json_dumps(rule: dict[str, Any]) -> str:
    import json as _j
    return _j.dumps({"steps": rule.get("steps"), "expect": rule.get("expect")},
                    sort_keys=True)


def confirm(rule: dict[str, Any], seed_dir: Path) -> tuple[bool, str]:
    """The banking gate, hardened (run-001 autopsy: the learner reward-hacked
    the original gate by converging on `json_parses`, the one predicate that
    confirms on any well-formed file — 18/19 grown checks failed the readout's
    circularity gate).

    A rule banks only if its check is DISCRIMINATING:
      1. it confirms on a fresh copy of the seed, AND
      2. it FAILS on a deliberately broken copy.
    'A check that cannot fail is not a check' — enforced at bank time, not
    discovered at readout. Wall-fact rules (predicate 'blocked') are exempt
    from (2): the wall stands regardless of file contents, and they never
    grow dots anyway."""
    exp = rule["expect"]
    with tempfile.TemporaryDirectory(prefix="grow-confirm-") as td:
        fresh = Path(td) / "env"
        shutil.copytree(seed_dir, fresh)
        obs = run_steps(rule, fresh)
        if not evaluate(exp["predicate"], exp.get("value"), obs):
            return False, obs
        if exp["predicate"] == "blocked":
            return True, obs
        # Judge the rule as its VERIFIER will act: replay only the final
        # (read) step on the broken copy. Replaying a mutation rule's writes
        # would recreate its own artifact and self-satisfy anywhere.
        broken = Path(td) / "broken"
        break_copy(seed_dir, broken)
        broken_obs = run_steps({"steps": [rule["steps"][-1]]}, broken)
        if evaluate(exp["predicate"], exp.get("value"), broken_obs):
            return False, (f"NON-DISCRIMINATING: check also passes on a broken "
                           f"environment — a check that cannot fail is not a "
                           f"check. (broken obs: {broken_obs[:120]})")
    return True, obs


def dot_eligible(rule: dict[str, Any]) -> bool:
    return (rule["steps"][-1]["tool"] in READ_ONLY_TOOLS
            and rule["expect"]["predicate"] != "blocked")


CHECK_TEMPLATE = '''#!/usr/bin/env python3
"""Grown check {rule_id} — compiled from a banked rule, template-generated.

Rule: {statement}

Read-only by construction: observes the workspace state the dot promises;
never replays mutations (achieving the state is the traveler's job).
"""
import json, sys
from pathlib import Path

ws = Path(sys.argv[sys.argv.index("--workspace") + 1])
try:
    observation = (ws / {read_path!r}).read_text()
except FileNotFoundError:
    print(json.dumps({{"dot": {rule_id!r}, "pass": False,
                      "evidence": "file {read_path} missing"}}))
    sys.exit(1)

predicate, value = {predicate!r}, {value!r}
if predicate == "contains":
    ok = str(value) in observation
elif predicate == "equals":
    ok = observation.strip() == str(value).strip()
elif predicate == "json_parses":
    try: json.loads(observation); ok = True
    except Exception: ok = False
elif predicate == "json_item_count":
    try: ok = len(json.loads(observation)) == int(value)
    except Exception: ok = False
else:
    ok = False

print(json.dumps({{"dot": {rule_id!r}, "pass": ok,
                  "evidence": f"{{predicate}}={{value!r}} on {read_path}: "
                              + ("holds" if ok else "VIOLATED")}}))
sys.exit(0 if ok else 1)
'''


def compile_check(rule: dict[str, Any], checks_dir: Path) -> Path | None:
    """Emit the standalone read-only verifier for a dot-eligible rule.
    Only filesystem reads compile in v0 (fetch-based dots are a later spiral)."""
    if not dot_eligible(rule):
        return None
    last = rule["steps"][-1]
    if last["tool"] != "filesystem.read_file":
        return None
    exp = rule["expect"]
    script = CHECK_TEMPLATE.format(
        rule_id=rule["id"], statement=rule["statement"],
        read_path=last["args"]["path"],
        predicate=exp["predicate"], value=exp.get("value"))
    path = checks_dir / f"{rule['id']}.py"
    path.write_text(script)
    return path
