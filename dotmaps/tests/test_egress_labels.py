"""H9 (HARDENING_BRIEF): egress + data labels in the UI. The audit's Q40/
Q51 finding — "the product should surface a per-action egress label
instead of making users infer this from the driver." Before any frontier
submission the chat should show: model will be called, sources to be
read, network destinations, stored-in-record. Per-action egress label in
the Run tab."""
import json
import shutil
import threading
import urllib.request
from pathlib import Path

import pytest

from dotmaps.queen import chat as chat_mod
from dotmaps.queen import trips as trips_mod
from dotmaps.queen import ui as ui_mod
from dotmaps.queen import workorder as wo_mod

REPO = Path(__file__).resolve().parents[2]


def test_egress_preview_carries_all_four_fields(tmp_path):
    home = tmp_path / "home.json"
    out = chat_mod.egress_preview(home_path=home)
    assert set(out) == {"model", "sources", "network_destinations", "stored_in_record"}
    assert out["model"]
    assert isinstance(out["sources"], list) and out["sources"]
    assert isinstance(out["network_destinations"], list) and out["network_destinations"]
    assert out["stored_in_record"] is True


def test_api_egress_endpoint_serves_all_four_fields(tmp_path):
    trips_path = tmp_path / "trips.jsonl"
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    live_root = tmp_path / "live"
    live_root.mkdir()

    httpd = ui_mod.serve(host="127.0.0.1", port=0, trips_path=trips_path,
                         skills_dir=skills, live_root=live_root)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.socket.getsockname()[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/egress", timeout=5) as r:
            assert r.status == 200
            data = json.loads(r.read())
        assert set(data) == {"model", "sources", "network_destinations", "stored_in_record"}
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _ok_runner(workspace, job, *, model, max_turns, timeout_s, trips_path, run_id):
    (workspace / "answer.json").write_text(json.dumps({
        "answer": "5 items.", "statement": "source_items.json holds 5 items",
        "path": "source_items.json", "predicate": "json_item_count", "value": 5}))
    return {"ok": True, "subtype": "success", "num_turns": 1, "cost_usd": 0.01}


def test_chat_work_order_start_trip_carries_egress_label(tmp_path):
    trips_path = tmp_path / "trips.jsonl"
    order = chat_mod.run_work_order("how many items?", trips_path=trips_path, _runner=_ok_runner)
    starts = [t for t in trips_mod.read_all(trips_path)
             if t["type"] == "WORK_ORDER" and t["data"].get("phase") == "start"]
    assert len(starts) == 1
    egress = starts[0]["data"]["egress"]
    assert set(egress) == {"model", "sources", "network_destinations", "stored_in_record"}
    assert egress["stored_in_record"] is True


def _migrate_identity(workspace, job, *, model, max_turns, timeout_s):
    src = json.loads((workspace / "source_items.json").read_text())
    (workspace / "target_items.json").write_text(json.dumps(src))
    return {"ok": True, "subtype": "success", "num_turns": 1, "cost_usd": 0.0}


def test_workorder_start_trip_carries_egress_label(tmp_path):
    trips_path = tmp_path / "trips.jsonl"
    wo_mod.run_work_order("migration", trips_path=trips_path, _runner=_migrate_identity)
    starts = [t for t in trips_mod.read_all(trips_path)
             if t["type"] == "WORK_ORDER" and t["data"].get("phase") == "start"]
    assert len(starts) == 1
    assert starts[0]["data"]["egress"]["stored_in_record"] is True


def test_run_state_payload_surfaces_egress_on_start_step(tmp_path):
    trips_path = tmp_path / "trips.jsonl"
    chat_mod.run_work_order("how many items?", trips_path=trips_path, _runner=_ok_runner)
    payload = ui_mod.run_state_payload(trips_path)
    start_steps = [s for s in payload["steps"] if s["phase"] == "start"]
    assert len(start_steps) == 1
    assert start_steps[0]["egress"]["stored_in_record"] is True


def test_zero_jargon_check_still_passes_with_egress_note():
    """The static page's new disclosure text must not reintroduce any of
    the banned operator-jargon words assure.py's check already enforces."""
    from dotmaps.queen import assure as assure_mod
    ok, detail = assure_mod.check_zero_jargon_across_tabs()
    assert ok, detail
