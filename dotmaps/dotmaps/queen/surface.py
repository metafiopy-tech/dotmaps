"""SURFACE — Fio's one card (QUEEN spec §3.6, §3.9).

`dotmaps surface` renders exactly one thing: "Nothing needs you." unless an
ESCALATE trip is open, in which case it renders as a DECISION — a question
plus numbered options — never a report, never advice. Silence except
trips is the design; a wall of green checkmarks is not a card, it's noise
with the volume turned down.

`dotmaps surface --resolve <id> --choice <n>` answers one and restores
calm. Resolution is itself a new trip (ESCALATE, phase=resolved) — the
log stays append-only; nothing is edited in place.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import trips as trips_mod


def _escalation_states(path: Path) -> dict[str, dict]:
    """id -> latest state, open/closed tracked in trip order (seq) so a
    re-raise after a resolution correctly reopens the card."""
    state: dict[str, dict] = {}
    for rec in trips_mod.read_all(path):
        if rec["type"] != "ESCALATE":
            continue
        d = rec["data"]
        eid = d.get("id")
        if eid is None:
            continue
        if d.get("phase") == "raised":
            state[eid] = {**d, "open": True}
        elif d.get("phase") == "resolved" and eid in state:
            state[eid] = {**state[eid], "open": False,
                          "choice": d.get("choice"),
                          "choice_label": d.get("choice_label")}
    return state


def open_escalations(path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> list[dict]:
    return [d for d in _escalation_states(path).values() if d["open"]]


def card(path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> dict[str, Any]:
    """The one card: `{"status": "calm", ...}` or `{"status": "decision", "escalations": [...]}`."""
    open_esc = open_escalations(path)
    if not open_esc:
        return {"status": "calm", "message": "Nothing needs you."}
    return {"status": "decision", "escalations": open_esc}


def render(c: dict[str, Any]) -> str:
    if c["status"] == "calm":
        return c["message"]
    lines = []
    for esc in c["escalations"]:
        lines.append(f"[{esc['id']}] {esc['question']}")
        for i, opt in enumerate(esc.get("options", []), 1):
            lines.append(f"  {i}. {opt}")
    return "\n".join(lines)


def escalate(id: str, question: str, options: list[str],
             path: Path = trips_mod.DEFAULT_TRIPS_PATH, **extra: Any) -> dict:
    """Raise a decision. `id` should be a stable/deterministic key for the
    condition (e.g. a predicate or skill identity) so repeat firings of the
    same underlying condition reopen the same card instead of spawning
    duplicates."""
    return trips_mod.emit("ESCALATE", path=path, phase="raised", id=id,
                          question=question, options=list(options), **extra)


def resolve(id: str, choice: int, path: Path = trips_mod.DEFAULT_TRIPS_PATH) -> dict:
    """Answer one open escalation by its 1-indexed option number."""
    open_by_id = {e["id"]: e for e in open_escalations(path)}
    if id not in open_by_id:
        raise ValueError(f"no open escalation with id {id!r}")
    options = open_by_id[id].get("options", [])
    if not (1 <= choice <= len(options)):
        raise ValueError(f"choice must be in 1..{len(options)} (got {choice})")
    return trips_mod.emit("ESCALATE", path=path, phase="resolved", id=id,
                          choice=choice, choice_label=options[choice - 1])
