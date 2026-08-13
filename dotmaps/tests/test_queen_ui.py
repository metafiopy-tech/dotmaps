"""Q10 gate: THE HIVE (rebuilt keeper's edition, over the same live state
as the original operator console). Starts the real stdlib http.server on
an ephemeral port and fetches every endpoint for real — "verify with a
headless fetch of each endpoint + HTML", per the brief's own done-test
wording. The OLD jargon endpoints (surface/trips/manifest/flights) are
still tested below unchanged — queen/assure.py's Claim 10 depends on
them — alongside the new zero-jargon layer the page itself now reads."""
import json
import shutil
import threading
import urllib.error
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
    """The keeper's edition (rebuilt): plain page, plain endpoint names.
    The OLD jargon endpoints (/api/surface, /api/trips, /api/manifest,
    /api/flights) still exist server-side for queen/assure.py's Claim 10
    below, but the rebuilt page itself never references them — it reads
    the new zero-jargon layer instead."""
    base, _ = running_server
    with urllib.request.urlopen(base + "/", timeout=5) as r:
        assert r.status == 200
        assert "text/html" in r.headers.get("Content-Type", "")
        body = r.read().decode()
    assert "<title>The Hive</title>" in body
    assert "/api/status" in body and "/api/skills" in body and "/api/diary" in body
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


# --------------------------------------------------------------------------- #
# THE HIVE — keeper's edition: the new zero-jargon layer                     #
# --------------------------------------------------------------------------- #

BANNED = ["manifest", "predicate", "wilson", "frontier", "trips"]


def test_index_html_contains_zero_banned_jargon_words():
    text = ui_mod.STATIC_PAGE.read_text(encoding="utf-8").lower()
    for word in BANNED:
        assert word not in text, f"banned jargon word {word!r} found in index.html"


def test_status_payload_calm_with_no_trips(tmp_path):
    p = tmp_path / "trips.jsonl"
    out = ui_mod.status_payload(p)
    assert out["calm"] is True
    assert out["questions"] == []
    assert out["free_jobs_count"] == 0


def test_status_payload_translates_a_raised_escalation_without_jargon(tmp_path):
    p = tmp_path / "trips.jsonl"
    sid = "abc123"
    trips_mod.emit("SHELVED", path=p, id=sid, dot="m01", statement="the target file exists")
    surface_mod.escalate(sid, "Frontier predicate on 'x' has been shelved 2 times "
                              "without growth: 'the target file exists'. Grow it now, "
                              "or keep shelving?",
                         ["grow now (requires Q7 or human-run)", "keep shelving",
                          "mark permanently frontier"],
                         path=p, dot="m01")
    out = ui_mod.status_payload(p)
    assert out["calm"] is False
    q = out["questions"][0]
    assert "the target file exists" in q["text"]
    for word in BANNED:
        assert word not in q["text"].lower()
    labels = [o["label"] for o in q["options"]]
    assert labels == ["Yes — learn it now", "Not yet — keep waiting", "No — leave it be"]


def test_status_payload_counts_certified_as_free_jobs(tmp_path):
    p = tmp_path / "trips.jsonl"
    trips_mod.emit("CERTIFIED", path=p, id="a", dot="d1", skill="s1")
    trips_mod.emit("CERTIFIED", path=p, id="b", dot="d2", skill="s2")
    trips_mod.emit("SHELVED", path=p, id="c", dot="d3")
    assert ui_mod.status_payload(p)["free_jobs_count"] == 2


def test_skills_payload_one_entry_per_skill_yaml(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    out = ui_mod.skills_payload(skills)
    assert len(out) == len(list(skills.glob("*.yaml")))
    names = {s["name"] for s in out}
    assert names == {f.stem for f in skills.glob("*.yaml")}
    for s in out:
        assert s["status"] in ("certified", "candidate", "convicted")
        assert 0.0 <= s["freshness"] <= 1.0


def test_skill_detail_payload_includes_receipt(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    any_name = next(skills.glob("*.yaml")).stem
    detail = ui_mod.skill_detail_payload(skills, any_name)
    assert detail["name"] == any_name
    assert detail["raw"]["name"] == any_name


def test_skill_detail_payload_none_for_unknown():
    assert ui_mod.skill_detail_payload(REPO / "skills", "does-not-exist") is None


def test_diary_payload_translates_known_types_without_jargon(tmp_path):
    p = tmp_path / "trips.jsonl"
    trips_mod.emit("SLEEP", path=p, harvested_candidates=2, shelf_rechecks=1,
                   dedup_conflicts=[], coverage=5, frontier=1)
    trips_mod.emit("SHELVED", path=p, id="x", dot="m01", statement="a thing to check")
    events = ui_mod.diary_payload(p, REPO / "skills")
    assert len(events) == 2
    texts = " ".join(e["text"] for e in events).lower()
    for word in BANNED:
        assert word not in texts
    assert any(e["text"].startswith("Slept:") for e in events)
    assert any("Set aside" in e["text"] for e in events)
    assert all("raw" in e for e in events)


def test_diary_payload_respects_limit_and_orders_newest_first(tmp_path):
    p = tmp_path / "trips.jsonl"
    for i in range(5):
        trips_mod.emit("SLEEP", path=p, tick=i, dedup_conflicts=[])
    events = ui_mod.diary_payload(p, REPO / "skills", limit=3)
    assert len(events) == 3
    assert [e["raw"]["data"]["tick"] for e in events] == [4, 3, 2]


def test_hive_endpoints_serve_200(running_server):
    base, _ = running_server
    for path in ("/api/status", "/api/skills", "/api/diary"):
        with urllib.request.urlopen(base + path, timeout=5) as r:
            assert r.status == 200, path
            assert r.read()

    skills = _get_json(base + "/api/skills")
    assert skills, "expected at least one skill"
    with urllib.request.urlopen(base + "/api/skill/" + skills[0]["name"], timeout=5) as r:
        assert r.status == 200
        assert json.loads(r.read())["name"] == skills[0]["name"]


def test_honeycomb_endpoint_returns_one_hex_per_skill_yaml(running_server):
    base, trips_path = running_server
    skills_dir = trips_path.parent / "skills"
    on_disk = len(list(skills_dir.glob("*.yaml")))
    data = _get_json(base + "/api/skills")
    assert len(data) == on_disk


def test_unknown_skill_returns_404(running_server):
    base, _ = running_server
    try:
        urllib.request.urlopen(base + "/api/skill/not-a-real-skill", timeout=5)
        assert False, "expected HTTPError 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404


def test_hive_resolve_round_trips(running_server):
    """The new page's answer buttons POST to the SAME /api/resolve the old
    console used — no duplicate write path."""
    base, trips_path = running_server
    status = _get_json(base + "/api/status")
    assert status["calm"] is False

    req = urllib.request.Request(
        base + "/api/resolve", method="POST",
        data=json.dumps({"id": "t-esc-1", "choice": 1}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200

    assert _get_json(base + "/api/status")["calm"] is True
    diary = _get_json(base + "/api/diary")
    assert any("Grow" not in e["text"] and "answered" in e["text"].lower()
              for e in diary), diary


def test_hive_endpoints_never_emit_a_trip_just_by_being_viewed(running_server):
    base, trips_path = running_server
    before = len(trips_mod.read_all(trips_path))
    _get_json(base + "/api/status")
    _get_json(base + "/api/skills")
    _get_json(base + "/api/diary")
    after = len(trips_mod.read_all(trips_path))
    assert after == before
