"""Phase-1 gate: full-manifest re-verification catches a planted regression
as loudly as progress (rule 4).

A dot that was green and then silently breaks must emit `dot_regressed` and
leave the eaten set on the very next verify pass.
"""
from conftest import SMOKE_MAP

from dotmaps.models import Map
from dotmaps.scoreboard.state import Scoreboard
from dotmaps.verifier.runner import Verifier


def test_planted_regression_is_caught(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    m = Map.load(SMOKE_MAP)
    board = Scoreboard.load_or_init(ws, m)
    board.start_run(m)
    verifier = Verifier.for_map(m, mode="local")

    # make both dots true, verify, reconcile -> both eaten
    (ws / "hello.txt").write_text("MAGIC-TOKEN present\n")
    board.start_cycle()
    board.reconcile(verifier.run_full_manifest(m, ws))
    assert board.eaten == {"001", "002"}

    # PLANT the regression: strip the token (001 still true, 002 now false)
    (ws / "hello.txt").write_text("token removed\n")
    board.start_cycle()
    board.reconcile(verifier.run_full_manifest(m, ws))

    assert "002" not in board.eaten
    assert "001" in board.eaten
    # the regression is on the record
    events = [e for e in board.log.replay() if e.get("event") == "dot_regressed"]
    assert any(e["dot"] == "002" for e in events)


def test_error_exit_treated_as_fail_and_flagged(tmp_path):
    """A verifier that errors (exit 2) counts as fail and is flagged, not passed."""
    from dotmaps.models import DotResult

    r = DotResult.from_stdout("009", "", exit_code=2)
    assert r.passed is False
    assert r.errored is True
