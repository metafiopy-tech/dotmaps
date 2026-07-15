"""HTML certificate from the event log — Phase 4 (spec §4.6). MINIMAL STUB.

Renders a plain-HTML summary from the JSONL event log ONLY (no runtime imports).
Phase 4 is deliberately last; this stub exists so the schema wiring is visible,
but the pixel replay and signing are not built yet.

Wording rule (liability posture, spec §4.6): certificates state exactly what was
checked ("34/34 declared checks passed"), NEVER blanket guarantees. Scoped
claims only.
"""

from __future__ import annotations

import json
from pathlib import Path


def render_html(events_jsonl: str | Path) -> str:
    path = Path(events_jsonl)
    events = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    eaten = sorted({e["dot"] for e in events if e.get("event") == "dot_eaten"})
    regressions = sum(1 for e in events if e.get("event") == "dot_regressed")
    ended = next((e.get("reason") for e in reversed(events)
                  if e.get("event") == "run_ended"), "unknown")
    started = next((e for e in events if e.get("event") == "run_started"), {})
    rows = "".join(f"<li>{d}</li>" for d in eaten)
    return f"""<!doctype html><meta charset=utf-8>
<title>Dot Maps certificate</title>
<h1>Completion certificate</h1>
<p><b>Map:</b> {started.get('map','?')} v{started.get('version','?')}</p>
<p><b>Result:</b> {len(eaten)} declared checks passed. Regressions caught: {regressions}. Run ended: {ended}.</p>
<p><i>This certifies exactly the checks listed below were verified — nothing more.</i></p>
<ul>{rows}</ul>
"""
