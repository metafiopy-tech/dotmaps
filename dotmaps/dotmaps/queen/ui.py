"""UI — Q10: THE HIVE (`dotmaps ui`), rebuilt keeper's edition.

One command serves a single self-contained page on localhost with the
stdlib's own http.server — zero third-party dependencies. The original
console (queen/static/index.html, formerly console.html) spoke in
operator jargon (predicate, manifest, Wilson, frontier, trips) and the
keeper couldn't read it. Two endpoint layers now share the same state:

  THE OLD LAYER (kept — queen/assure.py's Claim 10 depends on these
  exact routes; never renamed):
    GET  /api/surface   surface state + open ESCALATE questions
    GET  /api/trips     the hash-chained trip log, integrity-checked
    GET  /api/manifest  library coverage/frontier per preset + skill cards
                        (Wilson interval + decay/stability clocks)
    GET  /api/flights   runs/queen-live/* summaries

  THE HIVE LAYER (new — zero jargon, plain sentences, raw data behind a
  receipt tap; the same live state, translated for a keeper, not an
  operator):
    GET  /api/status    the hive door: calm, or open questions in plain
                        words + the free-jobs counter
    GET  /api/skills    one entry per skill card — the honeycomb
    GET  /api/skill/<name>  one card's full detail (the receipt)
    GET  /api/diary     the last ~20 events, translated to sentences (watch
                        check repeats collapsed to changes-only — silence
                        is health)

  THE WATCH LAYER (WATCH_BRIEF W1/W2/W3 — "point me at something"):
    POST /api/watch/start   {"url": ...} -> compiles a health map (real
                        crawl, no model), returns the unlit constellation
    POST /api/watch/<slug>/run   starts one paced check cycle in the
                        background (~2 dots/sec) so the state below can
                        be polled while it lights
    GET  /api/watch/<slug>/state    every dot's live status/streak,
                        derived fresh from trips.jsonl (never cached)
    POST /api/watch/<slug>/rewatch  {"minutes": n|null} toggle re-checking
                        on a timer
    Watch cards a dot earns after CERT_N clean checks in a row live under
    skills/watch/ (bank/certify.py never sees them — see watch/certify.py)
    and show up in the same /api/skills honeycomb as every other card.

Read-only except two write paths (Q1's surface.resolve, and starting/
running a watch — a keeper pointing at something is itself an action):

    POST /api/resolve   {"id": ..., "choice": n} -> round-trips into trips.jsonl

The page must never itself cause a trip just by being viewed: GET
handlers read via bank/route.route_map() and trips.read_all() directly,
never dispatch()/sleep() (which emit CERTIFIED/SHELVED/SLEEP trips as a
side effect of running).
"""
from __future__ import annotations

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import yaml

from ..bank.route import route_map
from ..watch import compiler as watch_compiler
from ..watch import history as watch_history
from ..watch import runner as watch_runner
from . import chat as chat_mod
from . import dispatch as dispatch_mod
from . import init as init_mod
from . import paper as paper_mod
from . import purple as purple_mod
from . import reconsolidate
from . import surface as surface_mod
from . import trips as trips_mod
from . import workflows as workflows_mod

REPO_ROOT = trips_mod.REPO_ROOT
STATIC_PAGE = Path(__file__).parent / "static" / "index.html"
DEFAULT_SKILLS = REPO_ROOT / "skills"
DEFAULT_LIVE_ROOT = REPO_ROOT / "runs" / "queen-live"
DEFAULT_CHAT_PATH = chat_mod.DEFAULT_CHAT_PATH
DEFAULT_MAPS_DIR = workflows_mod.DEFAULT_MAPS_DIR
DEFAULT_HOME_PATH = init_mod.DEFAULT_HOME_STATE_PATH
DEFAULT_SEED = chat_mod.DEFAULT_SEED
WATCH_PRESETS = ["https://bensluzasgolf.com"]

# In-process only, by design: a compiled health map and its running/rewatch
# state are re-derivable (recompile the crawl, replay trips.jsonl) — never
# the source of truth, just a cache so /run and /state don't have to
# recompile a live crawl on every poll. Losing this on restart loses
# nothing durable.
_watches: dict[str, dict[str, Any]] = {}
_watch_status: dict[str, dict[str, Any]] = {}
_watch_stop_events: dict[str, threading.Event] = {}
_watch_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# state readers — pure, read-only, no trips emitted                          #
# --------------------------------------------------------------------------- #

def surface_state(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> dict[str, Any]:
    return surface_mod.card(trips_path)


def trips_state(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                 limit: int = 300) -> dict[str, Any]:
    ok, reason = trips_mod.verify_integrity(trips_path)
    recs = trips_mod.read_all(trips_path)
    return {"integrity_ok": ok, "integrity_reason": reason,
            "count": len(recs), "trips": recs[-limit:]}


def manifest_state(skills_dir: Path = DEFAULT_SKILLS) -> dict[str, Any]:
    skills_dir = Path(skills_dir)
    mpath = skills_dir / "manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {}

    cards = []
    for f in sorted(skills_dir.glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        cert = card.get("certificate", {}) or {}
        decay = card.get("decay", {}) or {}
        cards.append({
            "name": card.get("name"), "statement": card.get("statement"),
            "status": cert.get("status"), "wilson": cert.get("wilson"),
            # H5 (HARDENING_BRIEF): the honest label — "deterministic-
            # consistency" (repeated replays of the same frozen steps) vs
            # "sampled-reliability" (independent live samples, e.g. watch
            # cards). `consistency` is the plain-English display string for
            # the former; `wilson` is kept for back-compat but is no longer
            # what decides certification for that regime — see
            # bank/certify.py.
            "regime": cert.get("regime"), "consistency": cert.get("consistency"),
            "n": cert.get("n"), "invocations": decay.get("invocations"),
            "stability": decay.get("stability"), "last_used": decay.get("last_used"),
        })

    presets: dict[str, Any] = {}
    for name, t in dispatch_mod.PRESETS.items():
        try:
            r = route_map(t["map"], t["skills"], t["workspace"])
            presets[name] = {"covered": len(r["covered"]), "frontier": len(r["frontier"]),
                             "total": len(r["covered"]) + len(r["frontier"])}
        except Exception as e:                       # a map fixture may be
            presets[name] = {"error": str(e)}          # missing in a fresh checkout

    return {"coverage": len(manifest.get("coverage", {})),
            "frontier_count": len(manifest.get("frontier", [])),
            "skills": cards, "presets": presets}


def flights_state(live_root: Path = DEFAULT_LIVE_ROOT) -> dict[str, Any]:
    live_root = Path(live_root)
    runs = []
    if live_root.is_dir():
        for d in sorted(live_root.iterdir()):
            if not d.is_dir():
                continue
            prim_dir = d / "primitives"
            primitives = len(list(prim_dir.glob("*.yaml"))) if prim_dir.is_dir() else 0
            pj = d / "poke_journal.jsonl"
            pokes = sum(1 for _ in pj.open()) if pj.exists() else 0
            runs.append({"name": d.name, "primitives": primitives, "pokes": pokes,
                        "grown_map": (d / "grown-map").is_dir()})
    return {"runs": runs}


# --------------------------------------------------------------------------- #
# THE HIVE — keeper's edition: plain sentences over the same live state      #
# --------------------------------------------------------------------------- #

GLYPH = {
    "SLEEP": "\U0001F634", "CERTIFIED": "✨", "SHELVED": "\U0001F4E5",
    "ESCALATE": "❓", "BUDGET_EXHAUSTED": "⏳",
    "ORACLE_FAIL": "⚠️", "CONVICTED": "\U0001F6AB",
    "BLOCKED": "\U0001F6A7", "WORK_ORDER": "\U0001F6E0️",
}


def _load_card(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def _earliest_learned(card: dict) -> str | None:
    dates = [p.get("banked_at") for p in card.get("provenance", []) if p.get("banked_at")]
    return min(dates) if dates else None


def _skill_statement(skills_dir: Path, name: str | None) -> str | None:
    if not name:
        return None
    p = Path(skills_dir) / f"{name}.yaml"
    if not p.exists():
        return None
    return _load_card(p).get("statement")


def _plain_choice(text: str) -> str:
    """A button label a keeper can read: strips the parenthetical aside,
    maps the three known shapes to a plain yes/no/never."""
    cleaned = re.sub(r"\s*\([^)]*\)", "", text or "").strip()
    low = cleaned.lower()
    if "grow now" in low:
        return "Yes — learn it now"
    if any(m in low for m in purple_mod.DEFER_MARKERS):
        return "Not yet — keep waiting"
    if "mark permanently" in low or "forget" in low:
        return "No — leave it be"
    return (cleaned[:1].upper() + cleaned[1:]) if cleaned else (text or "")


def _statement_for_escalate(records: list[dict], eid: str) -> str | None:
    """The most recent SHELVED trip sharing this id carries the plain
    statement — the ESCALATE record itself only carries the jargon-laden
    question text, so we read the structured field instead of parsing it."""
    stmt = None
    for rec in records:
        if rec["type"] == "SHELVED" and rec.get("data", {}).get("id") == eid:
            s = rec["data"].get("statement")
            if s:
                stmt = s
    return stmt


def status_payload(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> dict[str, Any]:
    """The hive door + the one counter: calm, or open questions in plain
    words, plus how many jobs have run free since she learned them."""
    records = trips_mod.read_all(trips_path)
    open_esc = surface_mod.open_escalations(trips_path)
    questions = []
    for e in open_esc:
        options = e.get("options", [])
        if e.get("kind") == "watch_escalation":
            # a watch failure — the raised trip already carries the plain
            # statement + the mechanical evidence directly (no SHELVED
            # lookup needed, and this is not a "should she learn it" ask).
            stmt = e.get("statement") or "something she's watching"
            text = f"Something broke: “{stmt}”. {e.get('evidence') or ''}".strip()
            questions.append({"id": e["id"], "text": text,
                              "options": [{"choice": i, "label": opt}
                                         for i, opt in enumerate(options, 1)]})
            continue
        stmt = _statement_for_escalate(records, e["id"]) or "one of her jobs"
        questions.append({
            "id": e["id"],
            "text": f"She's not sure how to check this yet: “{stmt}”. "
                    f"Want her to learn it now?",
            "options": [{"choice": i, "label": _plain_choice(opt)}
                       for i, opt in enumerate(options, 1)],
        })
    free_jobs = sum(1 for r in records if r["type"] == "CERTIFIED")
    return {"calm": not questions, "questions": questions,
            "free_jobs_count": free_jobs}


def _plain_description(statement: str | None) -> str:
    """One sentence, in plain words — Tab 3's list view needs a sentence a
    keeper can read at a glance, not a raw statement. Deterministic (pure
    function of the statement), so it's always in sync with the card —
    never stored, never able to drift stale."""
    stmt = (statement or "something she checked").strip()
    s = stmt[0].upper() + stmt[1:] if stmt else stmt
    if not s.endswith((".", "!", "?")):
        s += "."
    return f"Confirms: {s}"


def _cost_to_learn(statement: str | None, trips_path: Path) -> float | None:
    """What it cost, the one time she learned it — read from the WORK_ORDER
    completion trip a chat-taught fact leaves behind. None (shown as
    "already known") for anything grown before this cost was tracked."""
    if not statement:
        return None
    for rec in trips_mod.read_all(trips_path):
        d = rec.get("data", {})
        if rec["type"] == "WORK_ORDER" and d.get("phase") == "complete":
            ans = (d.get("gate") or {}).get("answer") or {}
            if ans.get("statement") == statement:
                cost = (d.get("claude") or {}).get("cost_usd")
                return round(float(cost), 4) if cost is not None else None
    return None


def _skill_summary(card: dict, path: Path,
                   trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> dict[str, Any]:
    decay = card.get("decay", {}) or {}
    last_used = decay.get("last_used")
    fresh = reconsolidate.freshness_ratio(path) if last_used else 1.0
    pulse = False
    recheck = decay.get("shelf_recheck")
    if recheck:
        try:
            ts = time.mktime(time.strptime(recheck, "%Y-%m-%dT%H:%M:%S"))
            pulse = (time.time() - ts) < 7 * 86400
        except ValueError:
            pulse = False
    return {
        "name": card["name"],
        "statement": card.get("statement"),
        "description": _plain_description(card.get("statement")),
        "status": card.get("certificate", {}).get("status", "candidate"),
        "learned": _earliest_learned(card),
        "used_count": decay.get("invocations") or 0,
        "times_used_free": decay.get("invocations") or 0,
        "cost_to_learn": _cost_to_learn(card.get("statement"), trips_path),
        "last_checked": last_used or recheck,
        "freshness": round(fresh, 3) if fresh is not None else 1.0,
        "pulse": pulse,
    }


def _all_skill_files(skills_dir: Path) -> list[Path]:
    """Top-level cards (the bank's) plus skills/watch/ (a watch dot's,
    earned live) — kept in a subdirectory precisely so bank/certify.py's
    non-recursive `glob("*.yaml")` reverify never sees them (see
    watch/certify.py's docstring)."""
    skills_dir = Path(skills_dir)
    watch_dir = skills_dir / "watch"
    files = sorted(skills_dir.glob("*.yaml"))
    if watch_dir.is_dir():
        files += sorted(watch_dir.glob("*.yaml"))
    return files


def skills_payload(skills_dir: Path = DEFAULT_SKILLS,
                   trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> list[dict[str, Any]]:
    """The honeycomb (and Tab 3's plain-list toggle over the same rows):
    one entry per skill card, bank and watch alike."""
    return [_skill_summary(_load_card(f), f, trips_path) for f in _all_skill_files(skills_dir)]


def skill_detail_payload(skills_dir: Path, name: str,
                         trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH
                         ) -> dict[str, Any] | None:
    """One hex, tapped: the plain card plus the raw receipt (the receipt
    chain — born in run X, certified with evidence Y — lives in `raw`)."""
    skills_dir = Path(skills_dir)
    path = skills_dir / f"{name}.yaml"
    if not path.exists():
        path = skills_dir / "watch" / f"{name}.yaml"
    if not path.exists():
        return None
    card = _load_card(path)
    detail = _skill_summary(card, path, trips_path)
    detail["learned_from"] = sorted({p.get("banked_from") for p in
                                     card.get("provenance", []) if p.get("banked_from")})
    detail["raw"] = card
    return detail


def memory_stats_payload(skills_dir: Path = DEFAULT_SKILLS) -> dict[str, Any]:
    """Tab 3's section header: "She knows N things. M certified.
    Everything re-checks itself on a clock." — counted fresh, every time."""
    files = _all_skill_files(Path(skills_dir))
    total = len(files)
    certified = sum(1 for f in files
                    if _load_card(f).get("certificate", {}).get("status") == "certified")
    return {"total": total, "certified": certified,
            "text": f"She knows {total} thing{'s' if total != 1 else ''}. "
                    f"{certified} certified. Everything re-checks itself on a clock."}


# --------------------------------------------------------------------------- #
# CHAT — Tab 1, the front door (QUEEN OS PRD)                                #
# --------------------------------------------------------------------------- #

def init_payload(path: Path = DEFAULT_HOME_PATH) -> dict[str, Any]:
    st = init_mod.home_state(path)
    return {"initialized": False} if st is None else {"initialized": True, **st}


def chat_payload(chat_path: Path = DEFAULT_CHAT_PATH,
                 trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> dict[str, Any]:
    """The transcript plus any open learn-offers rendered as trailing
    message-shaped cards with answer buttons (PRD: "reuse resolve")."""
    messages = chat_mod.read_chat(chat_path)
    open_learn = [e for e in surface_mod.open_escalations(trips_path)
                 if e.get("kind") == "learn_offer"]
    offers = [{"id": e["id"], "text": e["question"],
              "options": [{"choice": i, "label": opt}
                         for i, opt in enumerate(e.get("options", []), 1)]}
             for e in open_learn]
    ok, reason = chat_mod.verify_chat_integrity(chat_path)
    return {"messages": messages, "open_learn_offers": offers,
            "chain_ok": ok, "chain_reason": reason}


# --------------------------------------------------------------------------- #
# RUN — Tab 2, the glass engine room                                         #
# --------------------------------------------------------------------------- #

_RUN_PHASE_TEXT = {
    "start": "Starting a hands-on job...",
    "complete": "Finished — checked out clean.",
}


def run_state_payload(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                      run_id: str | None = None) -> dict[str, Any]:
    """The live step feed: every WORK_ORDER trip sharing one run_id,
    translated to a plain card. Defaults to the MOST RECENT run — active if
    it hasn't reached complete/failed yet, otherwise the idle replay of the
    last tape. Read-only: never emits a trip just by being polled."""
    records = trips_mod.read_all(trips_path)
    rid = run_id
    if rid is None:
        for rec in records:
            if rec["type"] == "WORK_ORDER" and rec["data"].get("run_id"):
                rid = rec["data"]["run_id"]
    if rid is None:
        return {"active": False, "run_id": None, "steps": []}

    steps = []
    active = False
    for rec in records:
        d = rec.get("data", {})
        if rec["type"] != "WORK_ORDER" or d.get("run_id") != rid:
            continue
        phase = d.get("phase")
        if phase in ("start", "step"):
            active = True
        elif phase in ("complete", "failed"):
            active = False
        else:
            continue
        if phase == "step":
            text = d.get("text") or "Working..."
        elif phase == "failed":
            text = f"Stopped — {d.get('reason') or 'did not check out'}."
        else:
            text = _RUN_PHASE_TEXT.get(phase, phase)
        steps.append({"seq": rec["seq"], "t": rec["t"], "phase": phase, "text": text,
                     "tool": d.get("tool"), "model_call": d.get("model_call", phase == "step"),
                     "elapsed": d.get("elapsed"), "failed": phase == "failed", "receipt": rec,
                     # H9 (HARDENING_BRIEF): the per-action egress label —
                     # model / sources / network / stored-in-record — is
                     # only present on the "start" step, exactly where the
                     # real call it describes was made.
                     "egress": d.get("egress")})
    return {"active": active, "run_id": rid, "steps": steps}


# --------------------------------------------------------------------------- #
# WORKFLOWS — Tab 4                                                          #
# --------------------------------------------------------------------------- #

def run_workflow(name: str, *, skills_dir: Path = DEFAULT_SKILLS,
                 maps_dir: Path = DEFAULT_MAPS_DIR,
                 trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> dict[str, Any]:
    """The RUN button: always the free, mechanical dispatch pass (route +
    honest staffing plan for whatever's still unproven) — never a live,
    billed campaign by a single click. Live/authorized growth stays an
    explicit, separate, human-run action (queen/live.py), same MONEY LAW
    every other default path in this package already holds to."""
    wf = workflows_mod.find(name, maps_dir)
    if wf is None:
        raise KeyError(f"unknown workflow {name!r}")
    target = wf["target"] if wf["kind"] == "seed" else str(Path(maps_dir) / wf["target"])
    report = dispatch_mod.dispatch(target, trips_path=trips_path, skills=skills_dir)
    return {"workflow": name, "covered": len(report["covered"]),
            "not_yet": len(report["frontier"]), "model_calls": report["model_calls"]}


def watchers_payload(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> list[dict[str, Any]]:
    """Every point-and-watch target this process knows about, with its
    next-check time — the Workflows tab's "watchers" section."""
    records = trips_mod.read_all(trips_path)
    with _watch_lock:
        items = list(_watch_status.items())
    out = []
    for slug, st in items:
        last = None
        for rec in records:
            if rec.get("data", {}).get("target") == slug:
                last = rec["t"]
        minutes = st.get("rewatch_minutes")
        next_check = None
        if minutes and last:
            try:
                ts = time.mktime(time.strptime(last, "%Y-%m-%dT%H:%M:%S"))
                next_check = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts + minutes * 60))
            except ValueError:
                next_check = None
        out.append({"slug": slug, "rewatch_minutes": minutes,
                    "running": st.get("running", False),
                    "last_checked": last, "next_check": next_check})
    return out


def _sleep_text(data: dict) -> str:
    parts = []
    h = data.get("harvested_candidates") or 0
    if h:
        parts.append(f"learned {h} new thing{'s' if h != 1 else ''}")
    r = data.get("shelf_rechecks") or 0
    if r:
        parts.append(f"double-checked {r} old skill{'s' if r != 1 else ''}")
    d = len(data.get("dedup_conflicts") or [])
    if d:
        parts.append(f"tidied {d} duplicate{'s' if d != 1 else ''}")
    return "Slept: " + (", ".join(parts) if parts else "everything was already in order") + "."


WATCH_GLYPH = {"green": "✓", "red": "✗", "amber": "⚠"}


def _is_watch_record(t: str, data: dict) -> bool:
    """A trip belongs to the watch layer if it's a watch-tagged check
    (WORK_ORDER kind=watch_check), or a CERTIFIED/ORACLE_FAIL/ESCALATE
    trip a watch cycle raised (carries `target`/`kind` a routed-skill or
    skill-growth trip never does)."""
    if t == "WORK_ORDER":
        return data.get("kind") == "watch_check"
    if t in ("CERTIFIED", "ORACLE_FAIL"):
        return bool(data.get("target"))
    if t == "ESCALATE":
        return data.get("kind") == "watch_escalation"
    return False


def _watch_family(t: str, data: dict) -> tuple | None:
    """The (target, dot) a watch record belongs to — the unit the
    changes-only filter groups repeats by."""
    if not _is_watch_record(t, data):
        return None
    return (data.get("target"), data.get("dot"))


def _translate(rec: dict, records: list[dict], skills_dir: Path) -> dict[str, Any]:
    t, data = rec["type"], rec.get("data", {})
    watch = _is_watch_record(t, data)
    if t == "SLEEP":
        text = _sleep_text(data)
    elif t == "CERTIFIED" and watch:
        stmt = data.get("statement") or "a page"
        if str(data.get("evidence") or "").startswith("first certification"):
            text = f"Now certain: {stmt} ({data['evidence']})."
        else:
            text = f"Checked: {stmt} — still holding ✓"
    elif t == "CERTIFIED":
        stmt = _skill_statement(skills_dir, data.get("skill")) or "a job"
        text = f"Mastered: {stmt}"
    elif t == "SHELVED":
        stmt = data.get("statement") or _skill_statement(skills_dir, data.get("skill")) or "a job"
        text = f"Set aside: {stmt} (will retry)"
    elif t == "ESCALATE" and watch:
        stmt = data.get("statement") or "something on the site"
        if data.get("phase") == "raised":
            text = f"Flagged: {stmt} — {data.get('evidence') or 'it stopped checking out'}"
        else:
            text = f"You answered: {_plain_choice(data.get('choice_label') or '')}"
    elif t == "ESCALATE":
        stmt = _statement_for_escalate(records, data.get("id")) or "a job"
        if data.get("phase") == "raised":
            text = f"Asked you: is it time to learn “{stmt}”?"
        else:
            text = f"You answered: {_plain_choice(data.get('choice_label') or '')}"
    elif t == "BUDGET_EXHAUSTED":
        text = "Ran out of time before finishing a job."
    elif t == "ORACLE_FAIL" and watch:
        stmt = data.get("statement") or "a page"
        text = f"Broke: {stmt} — {data.get('reason') or data.get('evidence') or 'stopped checking out'}"
    elif t == "ORACLE_FAIL":
        stmt = _skill_statement(skills_dir, data.get("skill")) or "a trick"
        text = f"A trick didn't hold up this time: {stmt} — she'll take another look."
    elif t == "CONVICTED":
        stmt = _skill_statement(skills_dir, data.get("skill")) or "a trick"
        text = f"Retired a trick that failed its own test: {stmt}."
    elif t == "BLOCKED":
        text = "Held back from repeating herself."
    elif t == "WORK_ORDER" and watch:
        stmt = data.get("statement") or "something on the site"
        if data.get("status") == "green":
            text = f"Checked: {stmt} — responds ✓"
        else:
            text = f"Checked: {stmt} — {data.get('evidence') or 'did not respond as expected'}"
    elif t == "WORK_ORDER":
        text = f"Did a hands-on job — {data.get('status', 'finished')}."
    else:
        text = f"Something happened: {json.dumps(data)[:80]}"
    glyph = WATCH_GLYPH.get(data.get("status"), GLYPH.get(t, "•")) if watch else GLYPH.get(t, "•")
    return {"seq": rec["seq"], "t": rec["t"], "glyph": glyph,
            "text": text, "raw": rec}


def _drop_quiet_watch_repeats(records: list[dict]) -> list[dict]:
    """'Diary appends only on CHANGES (silence = health, per her law)' —
    a watch cycle emits one raw trip per dot just to keep the check
    history/streak honest, but the diary should only ever surface a
    TRANSITION: a dot's status differing from its own previous check, or
    the moment it earns its certificate."""
    last_status: dict[tuple, str] = {}
    out = []
    for rec in records:
        t, data = rec["type"], rec.get("data", {})
        key = _watch_family(t, data)
        if key is None:
            out.append(rec)
            continue
        if t == "ESCALATE":
            out.append(rec)  # a raised watch escalation is always a change;
            continue          # never updates last_status (it carries no status)
        status = data.get("status")
        milestone = str(data.get("evidence") or "").startswith("first certification")
        if milestone or key not in last_status or last_status[key] != status:
            out.append(rec)
        last_status[key] = status
    return out


def diary_payload(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                  skills_dir: Path = DEFAULT_SKILLS, limit: int = 20
                  ) -> list[dict[str, Any]]:
    """The last ~20 events, translated to sentences, newest first."""
    records = trips_mod.read_all(trips_path)
    changes = _drop_quiet_watch_repeats(records)
    recent = list(reversed(changes[-limit:]))
    return [_translate(r, records, skills_dir) for r in recent]


# --------------------------------------------------------------------------- #
# THE WATCH LAYER — point-and-watch (WATCH_BRIEF W1/W2)                      #
# --------------------------------------------------------------------------- #

def watch_state_payload(slug: str, trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH
                        ) -> dict[str, Any]:
    """Every dot's live status, derived fresh from trips.jsonl — never
    from the in-process cache, so this is correct even after a restart
    (a target this process never itself compiled still shows whatever
    the trip log remembers)."""
    hm = _watches.get(slug)
    records = trips_mod.read_all(trips_path)
    if hm is not None:
        dot_specs = hm["dots"]
        target = hm["target"]
    else:
        dot_specs = [{"id": d, "statement": None, "kind": None, "url": None}
                    for d in watch_history.target_dot_ids(records, slug)]
        target = None
    dots = []
    for d in dot_specs:
        st = watch_history.dot_state(records, slug, d["id"])
        dots.append({**st, "id": d["id"], "statement": d.get("statement"),
                    "kind": d.get("kind"), "url": d.get("url")})
    status = _watch_status.get(slug, {})
    return {"slug": slug, "target": target, "dots": dots,
            "running": status.get("running", False),
            "rewatch_minutes": status.get("rewatch_minutes")}


def start_watch(url: str) -> dict[str, Any]:
    """Compile the health map (a real crawl, no model) and cache it for
    /run and /state — the compile itself is idempotent and cheap enough
    to never need to be the thing that's persisted (see module docstring)."""
    hm = watch_compiler.compile_health_map(url)
    with _watch_lock:
        _watches[hm["slug"]] = hm
        _watch_status.setdefault(hm["slug"], {"running": False, "rewatch_minutes": None})
    return hm


def run_watch_cycle(slug: str, trips_path: Path, skills_dir: Path,
                    pace_seconds: float = 0.5, background: bool = True) -> dict[str, Any]:
    """Kick off one check cycle. Paced (~2 dots/sec) and backgrounded by
    default so a poller on /state watches the constellation light one
    dot at a time, same as a keeper would in the browser."""
    hm = _watches.get(slug)
    if hm is None:
        raise KeyError(f"unknown watch {slug!r} — POST /api/watch/start first")
    with _watch_lock:
        st = _watch_status.setdefault(slug, {"running": False, "rewatch_minutes": None})
        if st["running"]:
            return {"started": False, "reason": "already running"}
        st["running"] = True

    def _go() -> None:
        try:
            watch_runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir,
                                   pace_seconds=pace_seconds)
        finally:
            with _watch_lock:
                _watch_status[slug]["running"] = False

    if background:
        threading.Thread(target=_go, daemon=True).start()
        return {"started": True, "slug": slug}
    _go()
    return {"started": True, "slug": slug, "finished": True}


def set_rewatch(slug: str, minutes: float | None, trips_path: Path, skills_dir: Path) -> None:
    """Toggle re-checking on a timer. Stops any prior timer for this slug
    first — one active loop per target, always."""
    old = _watch_stop_events.pop(slug, None)
    if old:
        old.set()
    with _watch_lock:
        _watch_status.setdefault(slug, {"running": False})["rewatch_minutes"] = minutes
    if not minutes:
        return
    ev = threading.Event()
    _watch_stop_events[slug] = ev

    def _loop() -> None:
        while not ev.wait(minutes * 60):
            try:
                run_watch_cycle(slug, trips_path, skills_dir, background=False)
            except KeyError:
                return  # the watch was never started in this process — give up quietly

    threading.Thread(target=_loop, daemon=True).start()


# --------------------------------------------------------------------------- #
# HTTP handler — stdlib only                                                 #
# --------------------------------------------------------------------------- #

def make_handler(trips_path: Path, skills_dir: Path, live_root: Path,
                 chat_path: Path = DEFAULT_CHAT_PATH, maps_dir: Path = DEFAULT_MAPS_DIR,
                 home_path: Path = DEFAULT_HOME_PATH, seed: Path = DEFAULT_SEED):
    trips_path, skills_dir, live_root = Path(trips_path), Path(skills_dir), Path(live_root)
    chat_path, maps_dir, home_path, seed = (Path(chat_path), Path(maps_dir),
                                            Path(home_path), Path(seed))

    class Handler(BaseHTTPRequestHandler):
        server_version = "QueenConsole/1.0"

        def log_message(self, fmt: str, *args: Any) -> None:
            pass  # quiet — the trip log is the story, not the access log

        def _send_json(self, obj: Any, status: int = 200) -> None:
            body = json.dumps(obj, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (stdlib method name)
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                body = STATIC_PAGE.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            routes = {
                "/api/surface": lambda: surface_state(trips_path),
                "/api/trips": lambda: trips_state(trips_path),
                "/api/manifest": lambda: manifest_state(skills_dir),
                "/api/flights": lambda: flights_state(live_root),
                "/api/status": lambda: status_payload(trips_path),
                "/api/skills": lambda: skills_payload(skills_dir, trips_path),
                "/api/diary": lambda: diary_payload(trips_path, skills_dir),
                "/api/init": lambda: init_payload(home_path),
                "/api/chat": lambda: chat_payload(chat_path, trips_path),
                # H9 (HARDENING_BRIEF): shown before a frontier submission —
                # model/no-model, sources to be read, network destinations,
                # stored-in-record (audit Q40/Q51).
                "/api/egress": lambda: chat_mod.egress_preview(home_path=home_path),
                "/api/run/state": lambda: run_state_payload(trips_path),
                "/api/memory": lambda: memory_stats_payload(skills_dir),
                "/api/workflows": lambda: workflows_mod.payload(skills_dir, maps_dir, trips_path),
                "/api/watchers": lambda: watchers_payload(trips_path),
                "/api/paper": lambda: paper_mod.payload(paper_dir=paper_mod.DEFAULT_PAPER_DIR,
                                                        skills_dir=skills_dir,
                                                        trips_path=trips_path, chat_path=chat_path),
            }
            if path in routes:
                try:
                    self._send_json(routes[path]())
                except Exception as e:
                    self._send_json({"error": str(e)}, status=500)
                return
            if path.startswith("/api/skill/"):
                name = unquote(path[len("/api/skill/"):])
                try:
                    detail = skill_detail_payload(skills_dir, name, trips_path)
                except Exception as e:
                    self._send_json({"error": str(e)}, status=500)
                    return
                self._send_json(detail if detail is not None else {"error": "not found"},
                                status=200 if detail is not None else 404)
                return
            if path == "/api/watch/presets":
                self._send_json({"presets": WATCH_PRESETS})
                return
            m = re.match(r"^/api/watch/([^/]+)/state$", path)
            if m:
                try:
                    self._send_json(watch_state_payload(unquote(m.group(1)), trips_path))
                except Exception as e:
                    self._send_json({"error": str(e)}, status=500)
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/resolve":
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    rec = surface_mod.resolve(payload["id"], int(payload["choice"]),
                                              path=trips_path)
                except Exception as e:
                    self._send_json({"error": str(e)}, status=400)
                    return
                self._send_json({"resolved": rec})
                return
            if path == "/api/init":
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    state = init_mod.run_init(payload["home"], payload.get("linked") or [],
                                              path=home_path)
                except Exception as e:
                    self._send_json({"error": str(e)}, status=400)
                    return
                self._send_json({"initialized": True, **state})
                return
            if path == "/api/chat":
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    out = chat_mod.ask(payload["message"], trips_path=trips_path,
                                       chat_path=chat_path, skills_dir=skills_dir,
                                       maps_dir=maps_dir, seed=seed)
                except Exception as e:
                    self._send_json({"error": str(e)}, status=400)
                    return
                self._send_json(out)
                return
            if path == "/api/chat/resolve":
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    out = chat_mod.resolve_learn_offer(
                        payload["id"], int(payload["choice"]), trips_path=trips_path,
                        chat_path=chat_path, maps_dir=maps_dir, live_root=live_root)
                except Exception as e:
                    self._send_json({"error": str(e)}, status=400)
                    return
                self._send_json(out)
                return
            m = re.match(r"^/api/workflow/([^/]+)/run$", path)
            if m:
                try:
                    out = run_workflow(unquote(m.group(1)), skills_dir=skills_dir,
                                       maps_dir=maps_dir, trips_path=trips_path)
                except KeyError as e:
                    self._send_json({"error": str(e)}, status=404)
                    return
                self._send_json(out)
                return
            if path == "/api/watch/start":
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    hm = start_watch(payload["url"])
                except Exception as e:
                    self._send_json({"error": str(e)}, status=400)
                    return
                self._send_json({"slug": hm["slug"], "target": hm["target"],
                                 "dots": [{"id": d["id"], "statement": d["statement"],
                                          "kind": d["kind"], "url": d["url"]}
                                         for d in hm["dots"]]})
                return
            m = re.match(r"^/api/watch/([^/]+)/run$", path)
            if m:
                try:
                    out = run_watch_cycle(unquote(m.group(1)), trips_path, skills_dir)
                except KeyError as e:
                    self._send_json({"error": str(e)}, status=404)
                    return
                self._send_json(out)
                return
            m = re.match(r"^/api/watch/([^/]+)/rewatch$", path)
            if m:
                slug = unquote(m.group(1))
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    minutes = payload.get("minutes")
                    set_rewatch(slug, float(minutes) if minutes else None,
                               trips_path, skills_dir)
                except Exception as e:
                    self._send_json({"error": str(e)}, status=400)
                    return
                self._send_json({"slug": slug, "rewatch_minutes": minutes})
                return
            self.send_error(404)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8765,
          trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
          skills_dir: Path = DEFAULT_SKILLS,
          live_root: Path = DEFAULT_LIVE_ROOT,
          chat_path: Path = DEFAULT_CHAT_PATH,
          maps_dir: Path = DEFAULT_MAPS_DIR,
          home_path: Path = DEFAULT_HOME_PATH,
          seed: Path = DEFAULT_SEED) -> ThreadingHTTPServer:
    """Build and start the server; returns the (already-serving-capable, not
    yet serve_forever'd) httpd so callers/tests can run it in a thread."""
    handler = make_handler(trips_path, skills_dir, live_root, chat_path, maps_dir,
                           home_path, seed)
    return ThreadingHTTPServer((host, port), handler)


def main(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = serve(host=host, port=port)
    addr = httpd.socket.getsockname()
    print(f"queen console: http://{addr[0]}:{addr[1]}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
