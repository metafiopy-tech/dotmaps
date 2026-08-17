"""CHAT — Tab 1, the front door (QUEEN OS PRD).

Every message: ROUTE FIRST (does a known workflow or a chat-learned map
already cover this, certified, $0?) -> else WORK ORDER (claude -p, tools
on, scoped to the demo workspace — subscription-billed, honest cost chip)
-> plain-language reply. A completed job that produced a checkable
artifact gets offered up for learning; "yes" banks a real primitive and
compiles a real one-dot map, so the NEXT identical ask routes free once
`dotmaps sleep` has certified it. No new machinery: this module is
assembly over bank/route.py, grow/banking.py, bank/extractor.py's harvest
(via the existing runs/queen-live/* scan in queen/sleep.py), and
queen/surface.py's escalate/resolve (the learn-offer reuses it verbatim).

Chat ledger: `runs/queen/chat.jsonl`, append-only, hash-chained like
trips.jsonl (queen/trips.py) — a separate, parallel chain (chat messages
aren't trip types; the chain math is duplicated on purpose, in a dozen
lines, rather than reworked into trips.py's frozen-adjacent module).

MONEY LAW: the only model call in this module is the WORK ORDER phase,
gated behind an injectable `_runner` exactly like queen/workorder.py's
`_run_agentic` — the default in production shells to `claude` via the
subscription CLI; tests inject a fake runner and pay nothing.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import yaml

from ..grow import banking
from . import _journal as journal_mod
from . import dispatch as dispatch_mod
from . import identity as identity_mod
from . import init as init_mod
from . import runner_adapter as runner_adapter_mod
from . import surface as surface_mod
from . import trips as trips_mod
from . import workflows as workflows_mod

REPO_ROOT = trips_mod.REPO_ROOT
DEFAULT_CHAT_PATH = REPO_ROOT / "runs" / "queen" / "chat.jsonl"
DEFAULT_SEED = REPO_ROOT / "corpus" / "pilot" / "seed-ws"
DEFAULT_SKILLS = REPO_ROOT / "skills"
DEFAULT_MAPS_DIR = REPO_ROOT / "maps"
DEFAULT_LIVE_ROOT = REPO_ROOT / "runs" / "queen-live"

WORK_ORDER_MODEL = "claude-sonnet-5"
WORK_ORDER_MAX_TURNS = 20
WORK_ORDER_TIMEOUT_S = 600

CHAT_PREDICATES = banking.PREDICATES - {"blocked"}  # a Q&A answer is never a wall-fact

GENESIS_HASH = "0" * 64


# --------------------------------------------------------------------------- #
# the chat ledger — a small, parallel hash chain (see module docstring)      #
# --------------------------------------------------------------------------- #

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _chat_line_hash(seq: int, t: str, role: str, text: str, chip: dict | None,
                    meta: dict, prev_hash: str) -> str:
    payload = json.dumps({"seq": seq, "t": t, "role": role, "text": text,
                          "chip": chip, "meta": meta, "prev_hash": prev_hash},
                         sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def emit_chat(role: str, text: str, path: Path = DEFAULT_CHAT_PATH,
             chip: dict | None = None, **meta: Any) -> dict:
    """H4 (HARDENING_BRIEF): same locked-critical-section fix as
    queen/trips.py's emit() — see queen/_journal.py."""
    assert role in ("user", "queen"), f"unknown chat role {role!r}"

    def _build(tail: dict | None) -> dict:
        seq = (tail["seq"] + 1) if tail else 1
        prev_hash = tail["hash"] if tail else GENESIS_HASH
        t = _now()
        h = _chat_line_hash(seq, t, role, text, chip, meta, prev_hash)
        return {"seq": seq, "t": t, "role": role, "text": text, "chip": chip,
                "meta": meta, "prev_hash": prev_hash, "hash": h}

    return journal_mod.append_locked(Path(path), _build)


def read_chat(path: Path = DEFAULT_CHAT_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_chat_integrity(path: Path = DEFAULT_CHAT_PATH) -> tuple[bool, str | None]:
    prev_hash = GENESIS_HASH
    for rec in read_chat(path):
        expect = _chat_line_hash(rec.get("seq"), rec.get("t"), rec.get("role"),
                                 rec.get("text"), rec.get("chip"), rec.get("meta"),
                                 prev_hash)
        if rec.get("prev_hash") != prev_hash:
            return False, f"chain broken at seq {rec.get('seq')}: prev_hash mismatch"
        if rec.get("hash") != expect:
            return False, f"chain broken at seq {rec.get('seq')}: hash mismatch (tampered)"
        prev_hash = rec["hash"]
    return True, None


# --------------------------------------------------------------------------- #
# the two cost chips — the thesis made visible, on every reply               #
# --------------------------------------------------------------------------- #

def free_chip() -> dict[str, Any]:
    return {"kind": "free", "label": "$0 · certified replay", "model_calls": 0}


def model_chip(claude_result: dict[str, Any]) -> dict[str, Any]:
    turns = claude_result.get("num_turns") or 0
    cost = claude_result.get("cost_usd") or 0.0
    return {"kind": "model", "label": f"model called · {turns} turn{'s' if turns != 1 else ''}",
            "turns": turns, "cost_usd": round(float(cost), 4)}


# --------------------------------------------------------------------------- #
# ROUTE FIRST — a known workflow, covered, $0                                #
# --------------------------------------------------------------------------- #

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _plain_covered_reply(wf: dict[str, Any], report: dict[str, Any]) -> str:
    if wf["kind"] == "chat":
        return wf["description"]
    n = len(report["covered"])
    d = wf["description"]
    return f"Already checked — {d[0].lower()}{d[1:]} ({n}/{n} confirmed.)"


def route_first(message: str, *, trips_path: Path, skills_dir: Path,
                maps_dir: Path, seed: Path = DEFAULT_SEED) -> dict[str, Any] | None:
    """None means: nothing already covers this. Otherwise the full reply
    payload, $0, zero model calls — mechanically earned by re-running
    route_map(), never trusted on a stored label."""
    wf = workflows_mod.match_trigger(message, maps_dir)
    if wf is None:
        return None
    target = wf["target"] if wf["kind"] == "seed" else str(Path(maps_dir) / wf["target"])
    report = dispatch_mod.dispatch(target, trips_path=trips_path, skills=skills_dir, workspace=seed)
    if report["frontier"]:
        return None  # honestly not (yet) fully covered — fall through to a work order
    text = _plain_covered_reply(wf, report)
    return {"text": text, "chip": free_chip(), "workflow": wf["name"],
            "model_calls": report["model_calls"]}


# --------------------------------------------------------------------------- #
# WORK ORDER — a new ask, tools on, subscription-billed                      #
# --------------------------------------------------------------------------- #

JOB_TEMPLATE = """\
You are answering a question about the files in this directory (a small
sample dataset). Read whatever files you need; do not modify anything.

Question: "{message}"

When you have the answer, write a file named answer.json in THIS directory
with exactly these keys:
  "answer": a short, plain-English sentence answering the question
  "statement": a short, present-tense factual statement this proves true
      about ONE file (e.g. "source_items.json contains exactly 5 items")
  "path": the relative path of the ONE file that proves the statement
      (must already exist in this directory)
  "predicate": one of "contains", "equals", "json_item_count", "json_parses"
  "value": the value the predicate tests for (omit for json_parses)

The predicate/path/value must describe a MECHANICAL check: re-reading
"path" and testing "predicate" against "value" must reproduce your answer.
Pick the simplest fact that answers the question. Write nothing except
answer.json.
"""


def compose_job(message: str) -> str:
    return JOB_TEMPLATE.format(message=message)


# H8 (HARDENING_BRIEF): the actual subprocess construction + CLI output
# field reading (subtype/num_turns/total_cost_usd, stream-json event
# shapes) now lives in queen/runner_adapter.py's ClaudeCliAdapter — this
# module (and workorder.py) call `.run_stream()`/`.run()` and read only
# the normalized result dict; neither touches a CLI flag or field name
# directly anymore. One adapter instance, reused across calls so its
# self-test result is cached rather than re-run every job.
_adapter = runner_adapter_mod.ClaudeCliAdapter()


def _run_agentic_stream(workspace: Path, job: str, *, model: str, max_turns: int,
                        timeout_s: int, trips_path: Path, run_id: str
                        ) -> dict[str, Any]:
    """The full agentic Claude Code, tools ON, streamed so the Run tab can
    show live steps as they happen (WORK_ORDER phase="step" trips). Falls
    back to reporting the plain error if the stream can't be parsed —
    never fakes a step that didn't happen."""
    return _adapter.run_stream(workspace, job, model=model, max_turns=max_turns,
                               timeout_s=timeout_s, trips_path=trips_path, run_id=run_id)


def _chat_gate(workspace: Path, claude_result: dict[str, Any]) -> dict[str, Any]:
    """Mechanical completion gate for a chat work order — never self-report.

    H1 (HARDENING_BRIEF): the audit's P0 finding was that this gate checked
    only the SHAPE of answer.json (parses, path exists, predicate name known)
    and never actually re-ran the predicate against the real file — so a
    structurally valid but FALSE claim, or even a claude_result whose
    subtype != "success", could still reach the user as an asserted answer.
    Three checks now, in order, each one closing exactly one of those holes:
      1. the model process itself must have succeeded (subtype == "success")
      2. answer.json must exist, parse, and name a real file + known predicate
      3. the predicate/value must be MECHANICALLY EXECUTED against that file
         (banking.run_steps + banking.evaluate — the same two functions
         bank/route.py and bank/certify.py judge every other claim with) and
         actually hold — a false value now fails here, not downstream."""
    if claude_result.get("subtype") != "success":
        return {"passed": False,
                "reason": f"model process did not succeed (subtype={claude_result.get('subtype')!r})"}
    p = workspace / "answer.json"
    if not p.exists():
        return {"passed": False, "reason": "no answer.json produced"}
    try:
        answer = json.loads(p.read_text())
    except json.JSONDecodeError:
        return {"passed": False, "reason": "answer.json did not parse as JSON"}
    required = {"answer", "statement", "path", "predicate"}
    if not required.issubset(answer.keys()):
        return {"passed": False, "reason": f"answer.json missing required keys {sorted(required)}"}
    if answer["predicate"] not in CHAT_PREDICATES:
        return {"passed": False, "reason": f"unknown predicate {answer['predicate']!r}"}
    if not (workspace / answer["path"]).exists():
        return {"passed": False, "reason": f"referenced file {answer['path']!r} does not exist"}

    rule = {"steps": [{"tool": "filesystem.read_file", "args": {"path": answer["path"]}}]}
    obs = banking.run_steps(rule, workspace)
    if not banking.evaluate(answer["predicate"], answer.get("value"), obs):
        return {"passed": False,
                "reason": (f"predicate did not mechanically hold: {answer['predicate']!r} "
                           f"against {answer.get('value')!r} failed on the real file")}
    return {"passed": True, "answer": answer, "obs": obs}


_REPLY_TEMPLATE: dict[str, Callable[[dict[str, Any]], str]] = {
    "contains": lambda a: f"Confirmed — {a['path']} contains {a.get('value')!r}.",
    "equals": lambda a: f"Confirmed — {a['path']} equals {a.get('value')!r}.",
    "json_item_count": lambda a: f"Confirmed — {a['path']} contains exactly {a.get('value')} items.",
    "json_parses": lambda a: f"Confirmed — {a['path']} parses as valid JSON.",
}

_NEGATION_MARKERS = ("no ", "not ", "n't", "false", "doesn't", "does not",
                     "isn't", "cannot", "can't", "never", "wasn't", "aren't")


def _color_contradicts(predicate: str, value: Any, free_text: str) -> bool:
    """Cheap, mechanical contradiction filter — deliberately NOT an NLI
    classifier (H1: the renderer's job is to never let free text override
    the checked fact, not to understand language). json_item_count gets a
    concrete check: any digit token in the free text that disagrees with
    the confirmed count is a contradiction. Every predicate also gets a
    coarse negation-marker scan. False positives just drop harmless color;
    false negatives can never happen for the PRIMARY assertion, since the
    template sentence — never the free text — is always what's returned."""
    lowered = free_text.lower()
    if predicate == "json_item_count":
        nums = re.findall(r"\d+", free_text)
        if nums and all(str(n) != str(value) for n in nums):
            return True
    return any(m in lowered for m in _NEGATION_MARKERS)


def _render_checked_reply(answer: dict[str, Any]) -> str:
    """H1's deterministic renderer: the reply is DERIVED from the checked
    result. The leading sentence is always the frozen template above — it
    can never come from the model's free text, so it can never contradict
    the mechanically-confirmed fact. The model's own `answer["answer"]` is
    appended only as trailing color, and only if it survives the mechanical
    contradiction filter; a contradicting or nonsensical free-text claim is
    simply dropped rather than shown (never precede or contradict the
    checked fact)."""
    base = _REPLY_TEMPLATE[answer["predicate"]](answer)
    free = (answer.get("answer") or "").strip()
    if free and not _color_contradicts(answer["predicate"], answer.get("value"), free):
        return f"{base} {free}"
    return base


def _rule_from_answer(answer: dict[str, Any]) -> dict[str, Any]:
    return {"id": "r001", "statement": answer["statement"],
            "steps": [{"tool": "filesystem.read_file", "args": {"path": answer["path"]}}],
            "expect": {"predicate": answer["predicate"], "value": answer.get("value")}}


def _slug(text: str, max_len: int = 40) -> str:
    """H7 (HARDENING_BRIEF): the audit's P1 finding — a plain 40-char
    truncation of the normalized question meant two long questions sharing
    a 40-char prefix collided into the same learned-map namespace
    (map-chat-{slug}, runs/queen-live/chat-{slug}). The readable prefix
    stays (still capped at max_len, still legible in a directory listing)
    but a hash of the FULL normalized text now makes the id unique."""
    return identity_mod.stable_id(text, text, prefix_len=max_len)


def _escalate_id(message: str) -> str:
    return hashlib.sha256(f"chat-learn::{_norm(message)}".encode()).hexdigest()[:12]


def run_work_order(message: str, *, seed: Path = DEFAULT_SEED,
                   model: str = WORK_ORDER_MODEL, max_turns: int = WORK_ORDER_MAX_TURNS,
                   timeout_s: int = WORK_ORDER_TIMEOUT_S,
                   trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                   _runner: Callable[..., dict[str, Any]] = _run_agentic_stream
                   ) -> dict[str, Any]:
    """DO, mechanically gated, exactly the Q8 shape but generalized to an
    arbitrary chat question instead of one fixed migration job."""
    run_id = uuid.uuid4().hex[:12]
    workspace = Path(tempfile.mkdtemp(prefix="queen-chat-")) / "ws"
    shutil.copytree(seed, workspace)

    job = compose_job(message)
    trips_mod.emit("WORK_ORDER", path=trips_path, phase="start", run_id=run_id,
                   job="chat", message=message, workspace=str(workspace),
                   max_turns=max_turns)

    claude_result = _runner(workspace, job, model=model, max_turns=max_turns,
                            timeout_s=timeout_s, trips_path=trips_path, run_id=run_id)
    gate = _chat_gate(workspace, claude_result)

    if gate["passed"]:
        trips_mod.emit("WORK_ORDER", path=trips_path, phase="complete", run_id=run_id,
                       job="chat", message=message, workspace=str(workspace),
                       gate=gate, claude=claude_result)
    else:
        trips_mod.emit("WORK_ORDER", path=trips_path, phase="failed", run_id=run_id,
                       job="chat", message=message, workspace=str(workspace),
                       gate=gate, claude=claude_result,
                       reason="WORK_ORDER_FAILED — no checkable answer produced")

    return {"run_id": run_id, "workspace": str(workspace), "job": job,
            "claude": claude_result, "gate": gate}


# --------------------------------------------------------------------------- #
# the ask — ROUTE FIRST -> WORK ORDER -> plain reply                         #
# --------------------------------------------------------------------------- #

def ask(message: str, *, trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
        chat_path: Path = DEFAULT_CHAT_PATH, skills_dir: Path = DEFAULT_SKILLS,
        maps_dir: Path = DEFAULT_MAPS_DIR, seed: Path = DEFAULT_SEED,
        model: str = WORK_ORDER_MODEL,
        _runner: Callable[..., dict[str, Any]] = _run_agentic_stream
        ) -> dict[str, Any]:
    message = (message or "").strip()
    emit_chat("user", message, path=chat_path)
    if not message:
        rec = emit_chat("queen", "Say something and she'll get to work.", path=chat_path)
        return {"reply": rec["text"], "chip": None}

    covered = route_first(message, trips_path=trips_path, skills_dir=skills_dir,
                          maps_dir=maps_dir, seed=seed)
    if covered is not None:
        rec = emit_chat("queen", covered["text"], path=chat_path, chip=covered["chip"],
                        workflow=covered["workflow"])
        return {"reply": rec["text"], "chip": covered["chip"], "learn_offer": None}

    wf = workflows_mod.match_trigger(message, maps_dir)
    if wf is not None and wf["kind"] == "seed":
        # a known BIG play, honestly not yet fully covered — that's a
        # Workflows-tab job (real work order + growth), not a chat Q&A one.
        text = (f'That\'s a bigger job — open Workflows and run "{wf["title"]}" '
                f"from there; she'll do it for real and show her work.")
        rec = emit_chat("queen", text, path=chat_path, workflow=wf["name"])
        return {"reply": rec["text"], "chip": None, "learn_offer": None}

    order = run_work_order(message, seed=seed, model=model, trips_path=trips_path,
                           _runner=_runner)
    chip = model_chip(order["claude"])
    learn_offer = None

    if order["gate"]["passed"]:
        answer = order["gate"]["answer"]
        # H1: the reply is DERIVED from the checked result, never trusted
        # off the model's free-text field — see _render_checked_reply().
        reply_text = _render_checked_reply(answer)
        rule = _rule_from_answer(answer)
        problem = banking.validate_rule(rule)
        confirmed = False
        if problem is None:
            confirmed, _ev = banking.confirm(rule, seed)
        if confirmed:
            eid = _escalate_id(message)
            already = {e["id"] for e in surface_mod.open_escalations(trips_path)}
            if eid not in already:
                surface_mod.escalate(
                    eid, f"Want her to learn this so next time is free: {answer['statement']!r}?",
                    ["Yes — learn it now", "No — leave it be"],
                    path=trips_path, kind="learn_offer", message=message, rule=rule,
                    answer=answer["answer"])
            learn_offer = {"id": eid, "statement": answer["statement"]}
    else:
        # H1: honest failure — the model's free-text claim (if any) is never
        # surfaced when the gate didn't mechanically pass, whatever the reason
        # (structural, a false predicate/value, or subtype != success).
        reply_text = "I tried, but I couldn't find a clean, checkable answer to that."

    rec = emit_chat("queen", reply_text, path=chat_path, chip=chip,
                    run_id=order["run_id"], learn_offer=learn_offer)
    return {"reply": rec["text"], "chip": chip, "learn_offer": learn_offer,
            "run_id": order["run_id"]}


# --------------------------------------------------------------------------- #
# learning — "yes" banks a real primitive + compiles a real one-dot map      #
# --------------------------------------------------------------------------- #

CHECK_TEMPLATE_MAP_DOMAIN = "chat"


def _write_chat_map(map_dir: Path, rule: dict[str, Any], answer_text: str,
                    trigger: str) -> Path:
    map_dir = Path(map_dir)
    verifiers_dir = map_dir / "verifiers"
    verifiers_dir.mkdir(parents=True, exist_ok=True)
    banking.compile_check(rule, verifiers_dir)
    map_data = {
        "name": map_dir.name, "version": "0.0.1", "domain": CHECK_TEMPLATE_MAP_DOMAIN,
        "mcp_required": ["filesystem.read_file"],
        "budget": {"max_cycles": 5},
        "traveler": {"driver": "scripted"},
        "dots": [{"id": rule["id"], "statement": rule["statement"],
                  "verifier": f"verifiers/{rule['id']}.py"}],
    }
    (map_dir / "map.yaml").write_text(yaml.safe_dump(map_data, sort_keys=False))
    (map_dir / "fog.md").write_text("# Fog\n\nNone yet — one dot, learned from a chat ask.\n")
    (map_dir / "blast_radius.md").write_text("# Blast radius\n\nRead-only check; nothing destructive.\n")
    (map_dir / "chat_trigger.json").write_text(json.dumps(
        {"trigger": trigger, "statement": rule["statement"], "answer": answer_text},
        indent=2))
    return map_dir


def _write_primitive(run_dir: Path, rule: dict[str, Any]) -> Path:
    prim_dir = Path(run_dir) / "primitives"
    prim_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(prim_dir.glob("*.yaml"))) + 1
    rid = f"r{n:03d}"
    card = {"statement": rule["statement"], "steps": rule["steps"], "expect": rule["expect"],
            "id": rid, "confirmed_by_poke": None, "banked_at": _now()}
    path = prim_dir / f"{rid}.yaml"
    path.write_text(yaml.safe_dump(card, sort_keys=False))
    return path


def resolve_learn_offer(id: str, choice: int, *, trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                        chat_path: Path = DEFAULT_CHAT_PATH,
                        maps_dir: Path = DEFAULT_MAPS_DIR,
                        live_root: Path = DEFAULT_LIVE_ROOT) -> dict[str, Any]:
    """The learn-offer's answer button POSTs here (not the generic
    /api/resolve) — "reuse resolve" per the PRD, so the FIRST thing this
    does is exactly what surface.resolve() does; then, on yes, it does the
    one extra thing a plain escalation never does: actually bank the rule."""
    raise_rec = None
    for rec in trips_mod.read_all(trips_path):
        if (rec["type"] == "ESCALATE" and rec["data"].get("id") == id
                and rec["data"].get("phase") == "raised"):
            raise_rec = rec
    rec = surface_mod.resolve(id, choice, path=trips_path)
    chosen_yes = rec["data"]["choice_label"].startswith("Yes")

    if not chosen_yes or raise_rec is None:
        note = emit_chat("queen", "Okay — she won't try to learn that one.", path=chat_path)
        return {"resolved": rec, "learned": False, "note": note["text"]}

    data = raise_rec["data"]
    rule, message, answer_text = data["rule"], data["message"], data["answer"]
    slug = _slug(message)
    run_dir = Path(live_root) / f"chat-{slug}"
    _write_primitive(run_dir, rule)
    map_dir = Path(maps_dir) / f"map-chat-{slug}"
    _write_chat_map(map_dir, rule, answer_text, _norm(message))
    note = emit_chat("queen", "Got it — she'll know that for free after her next sleep.",
                     path=chat_path, learned_map=map_dir.name)
    return {"resolved": rec, "learned": True, "map": map_dir.name, "note": note["text"]}


if __name__ == "__main__":
    import sys
    print(json.dumps(ask(" ".join(sys.argv[1:])), indent=2, default=str))
