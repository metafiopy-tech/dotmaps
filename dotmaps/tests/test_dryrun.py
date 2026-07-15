"""Phase-2 gate: dry-run mode works (spec §5).

Proofs:
  1. a dry-run traversal makes ZERO real mutations — the workspace is unchanged.
  2. intended actions are journaled (the journal is the product of a dry run).
  3. the walls still hold in dry-run: an illegal tool raises exactly as live.
"""
import json

from conftest import SMOKE_MAP

import pytest

from dotmaps.models import Map
from dotmaps.runtime.orchestrator import Orchestrator
from dotmaps.runtime.traveler import ToolBox, WallViolation
from dotmaps.safety.dryrun import wrap_toolbox_for_dryrun


def test_dryrun_traversal_mutates_nothing(tmp_path):
    ws = tmp_path / "ws"
    m = Map.load(SMOKE_MAP)
    board = Orchestrator(m, ws, verbose=False, dry_run=True).run()

    # nothing was actually written by the traveler
    assert not (ws / "hello.txt").exists()
    # so no dot can be green, and the run ended on budget — honestly red
    assert board.eaten == set()
    assert board.ended == "budget_exhausted"


def test_dryrun_journals_intended_actions(tmp_path):
    ws = tmp_path / "ws"
    m = Map.load(SMOKE_MAP)
    Orchestrator(m, ws, verbose=False, dry_run=True).run()

    journal_path = ws / ".dotmaps" / "dryrun.jsonl"
    assert journal_path.exists()
    entries = [json.loads(l) for l in journal_path.read_text().splitlines()]
    mocked = [e for e in entries if e.get("mocked")]
    assert mocked, "dry run must journal the mutations it mocked"
    assert any(e["tool"] == "filesystem.write_file" and e["args"]["path"] == "hello.txt"
               for e in mocked)


def test_walls_hold_in_dryrun(tmp_path):
    m = Map.load(SMOKE_MAP)
    ws = tmp_path / "ws"
    ws.mkdir()
    tools = wrap_toolbox_for_dryrun(ToolBox(m, ws))
    with pytest.raises(WallViolation):
        tools.call("cloudflare.deploy", project="x")


def test_reads_pass_through_in_dryrun(tmp_path):
    m = Map.load(SMOKE_MAP)
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "real.txt").write_text("real content")
    tools = wrap_toolbox_for_dryrun(ToolBox(m, ws))
    # the traveler sees the real world...
    assert tools.call("filesystem.read_file", path="real.txt") == "real content"
    # ...but cannot change it
    tools.call("filesystem.write_file", path="real.txt", content="overwritten")
    assert (ws / "real.txt").read_text() == "real content"
