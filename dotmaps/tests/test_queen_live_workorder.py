"""Q9 gate: authorized live dispatch = work order (DO) THEN targeted growth
(VERIFY) on the SAME completed workspace. No live model call here — `grow`
is patched out (same convention as the rest of this module's tests: the
live path itself is proven by committed run artifacts, not re-mocked into
the deterministic suite)."""
import json
from pathlib import Path
from unittest.mock import patch

from dotmaps.queen import live as live_mod
from dotmaps.queen import trips as trips_mod


def _failing_work_order(target, *, trips_path):
    trips_mod.emit("WORK_ORDER", path=trips_path, phase="start", target=target)
    trips_mod.emit("WORK_ORDER", path=trips_path, phase="failed", target=target,
                   reason="WORK_ORDER_FAILED — mechanical completion gate did "
                          "not pass; never proceeding to growth")
    return {"target": target, "workspace": "/tmp/does-not-matter",
            "gate": {"passed": False, "dots": []}, "claude": {"ok": True}, "ok": False}


def _passing_work_order_factory(tmp_path):
    def _wo(target, *, trips_path):
        ws = tmp_path / "completed-ws"
        ws.mkdir()
        (ws / "target_items.json").write_text(json.dumps([{"slug": "a"}]))
        (ws / ".dotmaps").mkdir()
        trips_mod.emit("WORK_ORDER", path=trips_path, phase="start", target=target)
        trips_mod.emit("WORK_ORDER", path=trips_path, phase="complete", target=target,
                       gate={"passed": True})
        return {"target": target, "workspace": str(ws),
                "gate": {"passed": True, "dots": []}, "claude": {"ok": True}, "ok": True}
    return _wo


def test_gate_failure_stops_before_growth_and_never_calls_grow(tmp_path):
    p = tmp_path / "trips.jsonl"
    with patch("dotmaps.queen.live.grow") as fake_grow:
        out = live_mod.live_dispatch("migration", trips_path=p, authorized=True,
                                     _work_order=_failing_work_order)
    assert out["live"] is False
    assert out["work_order"]["ok"] is False
    assert "WORK_ORDER_FAILED" in out["note"]
    fake_grow.assert_not_called()

    phases = [t["data"]["phase"] for t in trips_mod.read_all(p) if t["type"] == "WORK_ORDER"]
    assert phases == ["start", "failed"]


def test_gate_success_grows_the_same_completed_workspace(tmp_path):
    p = tmp_path / "trips.jsonl"
    captured = {}

    def fake_grow(workspace, run_dir, learner, cfg=None):
        captured["workspace"] = Path(workspace)
        return {"grown_map": None, "primitives": 0, "spirals": []}

    with patch("dotmaps.queen.live.grow", side_effect=fake_grow):
        out = live_mod.live_dispatch(
            "migration", trips_path=p, authorized=True,
            run_dir=tmp_path / "run",
            _work_order=_passing_work_order_factory(tmp_path))

    assert out["live"] is True
    assert out["work_order"]["ok"] is True
    # growth ran against the WORK ORDER's completed workspace, not a fresh copy
    assert captured["workspace"] == Path(out["work_order"]["workspace"])
    assert (captured["workspace"] / "target_items.json").exists()

    board = captured["workspace"] / ".dotmaps" / "approved_board.txt"
    assert board.exists()
    text = board.read_text()
    assert "ALREADY been migrated" in text
    assert "do-then-verify" in text.lower()
