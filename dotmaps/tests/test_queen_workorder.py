"""Q8 gate: the work-order organ — DO, mechanically separated from VERIFY.
No live model call here (same convention as test_claude_code_learner.py /
test_queen_harvest.py's live-artifact split): the wiring is proven with an
injected `_runner`; the real subscription-billed agentic call is exercised
live, once, per QUEEN_FLIGHT_LOG.md."""
import json
import shutil
from pathlib import Path

from dotmaps.queen import trips as trips_mod
from dotmaps.queen import workorder as wo_mod

REPO = Path(__file__).resolve().parents[2]


def _migrate_identity(workspace: Path, job: str, *, model, max_turns, timeout_s):
    """Deterministic, free stand-in for the live agentic call: DOES the
    migration (identity transform is a faithful migration for this
    synthetic same-shape source/target schema), so the wiring (temp
    workspace -> job -> gate -> trip) is pytest-covered without spending a
    live call."""
    src = json.loads((workspace / "source_items.json").read_text())
    (workspace / "target_items.json").write_text(json.dumps(src))
    return {"ok": True, "subtype": "success", "num_turns": 3, "cost_usd": 0.0}


def _do_nothing(workspace: Path, job: str, *, model, max_turns, timeout_s):
    """Simulates a sabotaged DO phase: no target file ever lands."""
    return {"ok": True, "subtype": "success", "num_turns": 1, "cost_usd": 0.0}


def test_compose_job_names_config_dot_statements_and_scope():
    map_dir = REPO / "maps" / "map-content-migration"
    job = wo_mod.compose_job(map_dir, REPO / "corpus" / "pilot" / "seed-ws")
    assert "migration.json" in job
    assert "Work only inside this directory" in job
    assert "internal link" in job.lower()
    assert "duplicate slug" in job.lower()


def test_work_order_produces_real_target_items_and_passes_gate(tmp_path):
    p = tmp_path / "trips.jsonl"
    result = wo_mod.run_work_order("migration", trips_path=p, _runner=_migrate_identity)
    assert result["ok"] is True
    assert result["gate"]["passed"] is True
    assert all(d["passed"] for d in result["gate"]["dots"])

    target = Path(result["workspace"]) / "target_items.json"
    assert target.exists()
    items = json.loads(target.read_text())
    assert len(items) == 5

    phases = [t["data"]["phase"] for t in trips_mod.read_all(p) if t["type"] == "WORK_ORDER"]
    assert phases == ["start", "complete"]


def test_sabotaged_workspace_fails_the_gate_and_trips_failed(tmp_path):
    p = tmp_path / "trips.jsonl"
    result = wo_mod.run_work_order("migration", trips_path=p, _runner=_do_nothing)
    assert result["ok"] is False
    assert result["gate"]["passed"] is False

    trips = trips_mod.read_all(p)
    phases = [t["data"]["phase"] for t in trips if t["type"] == "WORK_ORDER"]
    assert phases == ["start", "failed"]
    failed = trips[-1]
    assert "WORK_ORDER_FAILED" in failed["data"]["reason"]


def test_gate_reuses_the_maps_own_frozen_verifiers_unmodified(tmp_path):
    seed = REPO / "corpus" / "pilot" / "seed-ws"
    ws = tmp_path / "ws"
    shutil.copytree(seed, ws)
    map_dir = REPO / "maps" / "map-content-migration"
    gate = wo_mod.mechanical_completion_gate(map_dir, ws)
    assert gate["passed"] is False  # no target_items.json yet — incomplete workspace
    assert {d["dot"] for d in gate["dots"]} == {"m01", "m02", "m03", "m04", "m05"}


def test_run_work_order_never_touches_the_repo_seed(tmp_path):
    seed = REPO / "corpus" / "pilot" / "seed-ws"
    snapshot = sorted(p.name for p in seed.rglob("*") if p.is_file())
    p = tmp_path / "trips.jsonl"
    wo_mod.run_work_order("migration", trips_path=p, _runner=_migrate_identity)
    after = sorted(p.name for p in seed.rglob("*") if p.is_file())
    assert after == snapshot, "work order mutated the repo seed"
