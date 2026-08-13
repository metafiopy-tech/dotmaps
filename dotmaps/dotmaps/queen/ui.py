"""UI — Q10: the operator console (`dotmaps ui`).

One command serves the console on localhost with the stdlib's own
http.server — zero third-party dependencies. A single self-contained HTML
page (queen/static/console.html, night-hive design adapted from
docs/queen.html) reads LIVE repo state through four tiny JSON endpoints:

    GET  /api/surface   surface state + open ESCALATE questions
    GET  /api/trips     the hash-chained trip log, integrity-checked, as a feed
    GET  /api/manifest  library coverage/frontier per preset + skill cards
                        (Wilson interval + decay/stability clocks)
    GET  /api/flights   runs/queen-live/* summaries

Read-only except one write path that already existed (Q1's surface.resolve):

    POST /api/resolve   {"id": ..., "choice": n} -> round-trips into trips.jsonl

The console must never itself cause a trip just by being viewed: GET
handlers read via bank/route.route_map() and trips.read_all() directly,
never dispatch()/sleep() (which emit CERTIFIED/SHELVED/SLEEP trips as a
side effect of running).
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from ..bank.route import route_map
from . import dispatch as dispatch_mod
from . import surface as surface_mod
from . import trips as trips_mod

REPO_ROOT = trips_mod.REPO_ROOT
STATIC_PAGE = Path(__file__).parent / "static" / "console.html"
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
            }
            if path in routes:
                try:
                    self._send_json(routes[path]())
                except Exception as e:
                    self._send_json({"error": str(e)}, status=500)
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
