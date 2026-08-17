"""ORACLE — the mechanical check a watch dot runs (W1/W2).

Every watch dot is shaped exactly like a bank skill's rule: a
`method.steps` list of tool calls and a `check.predicate/value`. Running
one is therefore not a new mechanism — it's `grow.banking.run_steps` +
`evaluate`, the same two functions `bank/route.py` and `bank/certify.py`
already use. "This IS a real oracle; no model needed to verify" (WATCH
BRIEF W1) is true because nothing here is bespoke: an HTTP GET goes out
via the map system's own walled `fetch.get` tool, and the predicate is
one of the same fixed vocabulary (`contains`) every certified skill uses.

Three outcomes, not two — a dot can be unreachable without being wrong:
    green  — check ran, predicate holds
    red    — check ran, predicate failed (a real HTTP response, wrong shape)
    amber  — the fetch itself failed (DNS/connection/timeout) — unreachable,
             not falsified
`fetch.get`'s own error format makes the distinction free: a network-level
failure always renders as "ERROR: ..."; any completed HTTP exchange always
renders as "HTTP <code>\\n<body>", 200 or not.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from ..grow.banking import evaluate, run_steps

# fetch.get never touches the workspace path it's handed (ToolBox routes it
# straight to urllib) — one shared scratch dir is enough for every check.
DUMMY_WORKSPACE = Path(tempfile.gettempdir()) / "dotmaps-watch-scratch"
DUMMY_WORKSPACE.mkdir(parents=True, exist_ok=True)


def run_dot_check(dot: dict[str, Any]) -> dict[str, Any]:
    """Execute one dot's frozen steps for real; return the mechanical verdict.

    `dot` carries `method.steps` (a single `fetch.get`, by construction of
    the W1 compiler) and `check.predicate/value`. Never raises — a fetch
    failure is a valid (amber) outcome, not an exception.
    """
    rule = {"steps": dot["method"]["steps"]}
    obs = run_steps(rule, DUMMY_WORKSPACE)

    if obs.startswith("ERROR:"):
        return {"ok": False, "status": "amber", "evidence": obs[:300]}

    ok = evaluate(dot["check"]["predicate"], dot["check"].get("value"), obs)
    headline = obs.split("\n", 1)[0]  # "HTTP 200" / "HTTP 404" / ...
    if ok:
        evidence = f"{headline} — {dot['check']['predicate']} check holds"
    else:
        evidence = (f"{headline} — expected {dot['check']['predicate']} "
                    f"{dot['check'].get('value')!r}, did not hold")
    return {"ok": ok, "status": "green" if ok else "red", "evidence": evidence[:300]}
