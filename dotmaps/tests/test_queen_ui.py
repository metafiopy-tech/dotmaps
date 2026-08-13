"""Q10 gate: the operator console. Starts the real stdlib http.server on an
ephemeral port and fetches every endpoint for real — "verify with a headless
fetch of each endpoint + HTML", per the brief's own done-test wording."""
import json
import shutil
import threading
import urllib.request
from pathlib import Path

import pytest

from dotmaps.queen import surface as surface_mod
from dotmaps.queen import trips as trips_mod
from dotmaps.queen import ui as ui_mod

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def running_server(tmp_path):
    trips_path = tmp_path / "trips.jsonl"
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    live_root = tmp_path / "runs" / "queen-live"
    live_root.mkdir(parents=True)

    surface_mod.escalate("t-esc-1", "Grow now, or keep shelving?",
                         ["grow now", "keep shelving", "park it"], path=trips_path)

    httpd = ui_mod.serve(host="127.0.0.1", port=0, trips_path=trips_path,
                         skills_dir=skills, live_root=live_root)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.socket.getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}", trips_path
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _get_json(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        assert r.status == 200
        return json.loads(r.read())


def test_index_page_serves_html_with_no_console_errors_shape(running_server):
    base, _ = running_server
    with urllib.request.urlopen(base + "/", timeout=5) as r:
        assert r.status == 200
        assert "text/html" in r.headers.get("Content-Type", "")
        body = r.read().decode()
    assert "<title>QUEEN" in body
    assert "/api/surface" in body and "/api/trips" in body
    assert "/api/manifest" in body and "/api/flights" in body
    assert "<script>" in body  # single-file: no external JS/CSS dependency


def test_api_surface_serves_real_state(running_server):
    base, _ = running_server
    data = _get_json(base + "/api/surface")
    assert data["status"] == "decision"
    assert data["escalations"][0]["id"] == "t-esc-1"
    assert len(data["escalations"][0]["options"]) == 3


def test_api_trips_serves_hash_chained_feed(running_server):
    base, _ = running_server
    data = _get_json(base + "/api/trips")
    assert data["integrity_ok"] is True
    assert data["count"] >= 1
    assert data["trips"][0]["type"] == "ESCALATE"


def test_api_manifest_serves_real_repo_coverage(running_server):
    base, _ = running_server
    data = _get_json(base + "/api/manifest")
    assert data["coverage"] > 0
    assert isinstance(data["skills"], list) and len(data["skills"]) > 0
    assert "pilot" in data["presets"] and "migration" in data["presets"]
    assert data["presets"]["pilot"]["covered"] == 4


def test_api_flights_serves_run_summaries(running_server):
    base, _ = running_server
    data = _get_json(base + "/api/flights")
    assert data["runs"] == []  # empty live_root fixture — still a valid response


def test_resolve_round_trips_into_trips_jsonl(running_server):
    base, trips_path = running_server
    req = urllib.request.Request(
        base + "/api/resolve", method="POST",
        data=json.dumps({"id": "t-esc-1", "choice": 2}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200
        out = json.loads(r.read())
    assert out["resolved"]["data"]["choice_label"] == "keep shelving"

    recs = trips_mod.read_all(trips_path)
    resolved = [t for t in recs if t["type"] == "ESCALATE" and t["data"].get("phase") == "resolved"]
    assert len(resolved) == 1

    data = _get_json(base + "/api/surface")
    assert data["status"] == "calm"


def test_manifest_endpoint_never_emits_a_trip_just_by_being_viewed(running_server):
    base, trips_path = running_server
    before = len(trips_mod.read_all(trips_path))
    _get_json(base + "/api/manifest")
    _get_json(base + "/api/surface")
    _get_json(base + "/api/trips")
    _get_json(base + "/api/flights")
    after = len(trips_mod.read_all(trips_path))
    assert after == before
