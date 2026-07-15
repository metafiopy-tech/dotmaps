"""Phase-1 gate: kill-and-resume works from the JSONL alone (rule 2).

Two proofs:
  1. state is fully derivable by replaying the event log (delete state.json,
     rebuild, assert identical) — a fresh agent with zero context recovers it.
  2. a run interrupted mid-traversal resumes from the log and completes, without
     consulting any agent memory.
"""
import json

from conftest import SMOKE_MAP

from dotmaps.models import Map
from dotmaps.runtime.orchestrator import Orchestrator
from dotmaps.scoreboard.state import Scoreboard


def test_state_is_derivable_from_log_alone(tmp_path):
    ws = tmp_path / "ws"
    m = Map.load(SMOKE_MAP)
    Orchestrator(m, ws, verbose=False).run()

    state_json = ws / ".dotmaps" / "state.json"
    assert state_json.exists()
    state_json.unlink()  # throw away the cache; only the JSONL survives

    rebuilt = Scoreboard.load_or_init(ws, m)  # pure replay
    assert rebuilt.eaten == {"001", "002"}
    assert rebuilt.ended == "all_green"
    assert state_json.exists()  # cache regenerated from the log


def test_interrupted_run_resumes_and_completes(tmp_path):
    ws = tmp_path / "ws"
    m = Map.load(SMOKE_MAP)
    Orchestrator(m, ws, verbose=False).run()

    log = ws / ".dotmaps" / "events.jsonl"
    events = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]

    # Simulate a KILL after dot 001 was eaten but before 002: keep only events
    # up to and including the first dot_eaten, drop the terminal event.
    cut = []
    for ev in events:
        cut.append(ev)
        if ev.get("event") == "dot_eaten" and ev.get("dot") == "001":
            break
    log.write_text("\n".join(json.dumps(e) for e in cut) + "\n")
    (ws / ".dotmaps" / "state.json").unlink()
    # roll the workspace back so 002 is genuinely not satisfied yet
    (ws / "hello.txt").write_text("placeholder\n")

    # a fresh orchestrator (fresh agent, zero context) resumes from the log
    board = Orchestrator(m, ws, verbose=False).run(resume=True)
    assert board.ended == "all_green"
    assert board.eaten == {"001", "002"}
