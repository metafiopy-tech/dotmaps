"""`dotmaps replay` — the run's story, told from the append-only log.

The event log is the product's receipt: every attempt, every tool call the
traveler made, every dot the sovereign verifier ate, in order, unedited.
Replay renders it for humans. A run you can READ beats a run you must trust.

Accepts any of:
  - a workspace directory        (reads .dotmaps/events.jsonl)
  - a path to an events.jsonl    (bundled journals replay offline, no models)
  - a grow run directory         (reads poke_journal.jsonl — the POKE loop's
    journal has its own story shape: pokes, confirmations, banks, fog)
  - a path to a poke_journal.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path


def _resolve(target: Path) -> tuple[str, Path] | None:
    """Figure out which kind of journal we were handed."""
    if target.is_file():
        return (("grow", target) if "poke" in target.name else ("run", target))
    for kind, rel in (("run", ".dotmaps/events.jsonl"),
                      ("run", "events.jsonl"),
                      ("grow", "poke_journal.jsonl")):
        p = target / rel
        if p.exists():
            return (kind, p)
    return None


def replay(target: str | Path, out=print) -> None:
    resolved = _resolve(Path(target))
    if resolved is None:
        out(f"no event log or poke journal found under {target}")
        return
    kind, log = resolved
    events = [json.loads(l) for l in log.read_text().splitlines()]
    (_replay_run if kind == "run" else _replay_grow)(events, out)


def _replay_run(events: list[dict], out) -> None:
    eaten: list[str] = []
    usd = 0.0
    for e in events:
        kind = e.get("event")
        if kind == "run_started":
            out(f"══ run started · map {e.get('map', '?')} "
                f"v{e.get('version', '')} · {e.get('ts', '')[:19]}")
        elif kind == "cycle_started":
            out(f"\n── cycle {e.get('cycle')}")
        elif kind == "dot_attempted":
            out(f"  → attempt {e.get('attempt')} on {e.get('dot')}")
            for act in (e.get("actions") or [])[:8]:
                out(f"      {act[:110]}")
        elif kind == "dot_eaten":
            eaten.append(e.get("dot"))
            out(f"  ✔ {e.get('dot')} EATEN — {str(e.get('evidence', ''))[:90]}")
        elif kind == "budget_tick":
            usd = e.get("usd_spent", usd)
        elif kind == "run_ended":
            out(f"\n══ run ended: {e.get('reason', '?')} · "
                f"{len(eaten)} dots eaten · ${usd}")
    if not any(e.get("event") == "run_ended" for e in events):
        out(f"\n(log ends mid-run · {len(eaten)} dots eaten so far)")


def _replay_grow(events: list[dict], out) -> None:
    """The POKE loop's story: what the learner did, what the world confirmed,
    what fogged. Banks and rejections are the plot; raw pokes are texture."""
    banked = pokes = 0
    spiral = None
    for e in events:
        if e.get("spiral") != spiral:
            spiral = e.get("spiral")
            out(f"\n── spiral {spiral}" if spiral else "\n── forage")
        act = e.get("action", {})
        tool, obs = act.get("tool", "?"), e.get("observation", "")
        if tool in ("confirm", "confirm-revised"):
            rid = act.get("args", {}).get("id", "?")
            if obs.startswith("CONFIRMED"):
                banked += 1
                out(f"  ✔ [{rid}] BANKED — {obs[11:100]}")
            else:
                out(f"  ✘ [{rid}] {obs[:100]}")
        elif tool == "propose":
            out(f"  ⊘ proposal rejected — {obs[:90]}")
        else:
            pokes += 1
            marker = "↺" if obs.startswith("(repeat") else "·"
            out(f"  {marker} {tool}({str(act.get('args'))[:60]}) → {obs[:80]}")
    out(f"\n══ journal ends · {pokes} pokes · {banked} confirmations banked")
