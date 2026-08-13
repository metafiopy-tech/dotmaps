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
    GET  /api/diary     the last ~20 events, translated to sentences

Read-only except one write path that already existed (Q1's surface.resolve):

    POST /api/resolve   {"id": ..., "choice": n} -> round-trips into trips.jsonl

The page must never itself cause a trip just by being viewed: GET
handlers read via bank/route.route_map() and trips.read_all() directly,
never dispatch()/sleep() (which emit CERTIFIED/SHELVED/SLEEP trips as a
side effect of running).
"""
from __future__ import annotations

import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import yaml

from ..bank.route import route_map
from . import dispatch as dispatch_mod
from . import purple as purple_mod
from . import reconsolidate
from . import surface as surface_mod
from . import trips as trips_mod

REPO_ROOT = trips_mod.REPO_ROOT
STATIC_PAGE = Path(__file__).parent / "static" / "index.html"
DEFAULT_SKILLS = REPO_ROOT / "skills"
DEFAULT_LIVE_ROOT = REPO_ROOT / "runs" / "queen-live"


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
        stmt = _statement_for_escalate(records, e["id"]) or "one of her jobs"
        options = e.get("options", [])
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


def _skill_summary(card: dict, path: Path) -> dict[str, Any]:
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
        "status": card.get("certificate", {}).get("status", "candidate"),
        "learned": _earliest_learned(card),
        "used_count": decay.get("invocations") or 0,
        "last_checked": last_used or recheck,
        "freshness": round(fresh, 3) if fresh is not None else 1.0,
        "pulse": pulse,
    }


def skills_payload(skills_dir: Path = DEFAULT_SKILLS) -> list[dict[str, Any]]:
    """The honeycomb: one entry per skill card."""
    return [_skill_summary(_load_card(f), f) for f in sorted(Path(skills_dir).glob("*.yaml"))]


def skill_detail_payload(skills_dir: Path, name: str) -> dict[str, Any] | None:
    """One hex, tapped: the plain card plus the raw receipt."""
    path = Path(skills_dir) / f"{name}.yaml"
    if not path.exists():
        return None
    card = _load_card(path)
    detail = _skill_summary(card, path)
    detail["learned_from"] = sorted({p.get("banked_from") for p in
                                     card.get("provenance", []) if p.get("banked_from")})
    detail["raw"] = card
    return detail


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


def _translate(rec: dict, records: list[dict], skills_dir: Path) -> dict[str, Any]:
    t, data = rec["type"], rec.get("data", {})
    if t == "SLEEP":
        text = _sleep_text(data)
    elif t == "CERTIFIED":
        stmt = _skill_statement(skills_dir, data.get("skill")) or "a job"
        text = f"Mastered: {stmt}"
    elif t == "SHELVED":
        stmt = data.get("statement") or _skill_statement(skills_dir, data.get("skill")) or "a job"
        text = f"Set aside: {stmt} (will retry)"
    elif t == "ESCALATE":
        stmt = _statement_for_escalate(records, data.get("id")) or "a job"
        if data.get("phase") == "raised":
            text = f"Asked you: is it time to learn “{stmt}”?"
        else:
            text = f"You answered: {_plain_choice(data.get('choice_label') or '')}"
    elif t == "BUDGET_EXHAUSTED":
        text = "Ran out of time before finishing a job."
    elif t == "ORACLE_FAIL":
        stmt = _skill_statement(skills_dir, data.get("skill")) or "a trick"
        text = f"A trick didn't hold up this time: {stmt} — she'll take another look."
    elif t == "CONVICTED":
        stmt = _skill_statement(skills_dir, data.get("skill")) or "a trick"
        text = f"Retired a trick that failed its own test: {stmt}."
    elif t == "BLOCKED":
        text = "Held back from repeating herself."
    elif t == "WORK_ORDER":
        text = f"Did a hands-on job — {data.get('status', 'finished')}."
    else:
        text = f"Something happened: {json.dumps(data)[:80]}"
    return {"seq": rec["seq"], "t": rec["t"], "glyph": GLYPH.get(t, "•"),
            "text": text, "raw": rec}


def diary_payload(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                  skills_dir: Path = DEFAULT_SKILLS, limit: int = 20
                  ) -> list[dict[str, Any]]:
    """The last ~20 events, translated to sentences, newest first."""
    records = trips_mod.read_all(trips_path)
    recent = list(reversed(records[-limit:]))
    return [_translate(r, records, skills_dir) for r in recent]


# --------------------------------------------------------------------------- #
# HTTP handler — stdlib only                                                 #
# --------------------------------------------------------------------------- #

def make_handler(trips_path: Path, skills_dir: Path, live_root: Path):
    trips_path, skills_dir, live_root = Path(trips_path), Path(skills_dir), Path(live_root)

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
                "/api/skills": lambda: skills_payload(skills_dir),
                "/api/diary": lambda: diary_payload(trips_path, skills_dir),
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
                    detail = skill_detail_payload(skills_dir, name)
                except Exception as e:
                    self._send_json({"error": str(e)}, status=500)
                    return
                self._send_json(detail if detail is not None else {"error": "not found"},
                                status=200 if detail is not None else 404)
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path != "/api/resolve":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                rec = surface_mod.resolve(payload["id"], int(payload["choice"]),
                                          path=trips_path)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return
            self._send_json({"resolved": rec})

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8765,
          trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
          skills_dir: Path = DEFAULT_SKILLS,
          live_root: Path = DEFAULT_LIVE_ROOT) -> ThreadingHTTPServer:
    """Build and start the server; returns the (already-serving-capable, not
    yet serve_forever'd) httpd so callers/tests can run it in a thread."""
    handler = make_handler(trips_path, skills_dir, live_root)
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
