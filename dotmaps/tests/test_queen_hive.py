"""QUEEN OS: the five-tab backend — init, chat, run, memory, workflows,
watchers, paper. Same discipline as test_queen_ui.py: a real stdlib
server on an ephemeral port, real repo state, no mocks."""
import json
import shutil
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from dotmaps.queen import chat as chat_mod
from dotmaps.queen import trips as trips_mod
from dotmaps.queen import ui as ui_mod

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def running_server(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    seed = tmp_path / "seed"
    shutil.copytree(REPO / "corpus" / "pilot" / "seed-ws", seed)
    trips_path = tmp_path / "trips.jsonl"
    chat_path = tmp_path / "chat.jsonl"
    maps_dir = tmp_path / "maps"
    home_path = tmp_path / "home.json"
    live_root = tmp_path / "live"
    live_root.mkdir()

    httpd = ui_mod.serve(host="127.0.0.1", port=0, trips_path=trips_path, skills_dir=skills,
                         live_root=live_root, chat_path=chat_path, maps_dir=maps_dir,
                         home_path=home_path, seed=seed)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.socket.getsockname()[1]
    try:
        yield {"base": f"http://127.0.0.1:{port}", "trips_path": trips_path,
               "chat_path": chat_path, "maps_dir": maps_dir, "home_path": home_path,
               "seed": seed, "live_root": live_root, "skills_dir": skills}
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=5) as r:
        return r.status, json.loads(r.read())


def _post(base, path, payload):
    req = urllib.request.Request(base + path, method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read())


def test_init_endpoint_round_trips(running_server):
    base = running_server["base"]
    st, body = _get(base, "/api/init")
    assert st == 200 and body == {"initialized": False}

    st, body = _post(base, "/api/init", {"home": str(running_server["home_path"].parent)})
    assert st == 200 and body["initialized"] is True

    st, body = _get(base, "/api/init")
    assert body["initialized"] is True and "home" in body


def test_chat_route_first_is_free_and_zero_model_calls(running_server):
    base = running_server["base"]
    st, out = _post(base, "/api/chat", {"message": "check the demo workspace"})
    assert st == 200
    assert out["chip"]["kind"] == "free"
    assert out["chip"]["model_calls"] == 0

    st, hist = _get(base, "/api/chat")
    assert len(hist["messages"]) == 2
    assert hist["chain_ok"] is True


def test_memory_and_workflows_and_watchers_and_paper_serve(running_server):
    base = running_server["base"]
    for path in ("/api/memory", "/api/workflows", "/api/watchers", "/api/paper", "/api/run/state"):
        st, body = _get(base, path)
        assert st == 200, path

    st, mem = _get(base, "/api/memory")
    assert mem["total"] > 0 and "text" in mem

    st, wf = _get(base, "/api/workflows")
    names = {w["name"] for w in wf}
    assert {"check-demo-workspace", "migrate-the-menu-data"} <= names

    st, paper = _get(base, "/api/paper")
    assert len(paper["sections"]) >= 6
    assert paper["numbers"]["skills_total"] > 0


def test_workflow_run_button_dispatches_pilot_free(running_server):
    base = running_server["base"]
    st, out = _post(base, "/api/workflow/check-demo-workspace/run", {})
    assert st == 200
    assert out["covered"] == 4 and out["frontier_count"] == 0 and out["model_calls"] == 0


def test_workflow_run_unknown_name_404s(running_server):
    base = running_server["base"]
    try:
        _post(base, "/api/workflow/not-a-real-workflow/run", {})
        assert False, "expected 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404


def test_chat_learn_offer_appears_and_resolves_via_chat_endpoint(running_server):
    """The full loop through the HTTP surface: a new ask (fake runner
    monkeypatched onto chat.ask's default is not exercised here — instead
    we drive the lower-level primitives directly into the server's own
    trips/chat files, then prove the HTTP resolve endpoint completes the
    learn) — a real work order via HTTP would shell out to `claude`."""
    trips_path, chat_path = running_server["trips_path"], running_server["chat_path"]
    maps_dir, live_root = running_server["maps_dir"], running_server["live_root"]

    def fake_runner(workspace, job, *, model, max_turns, timeout_s, trips_path, run_id):
        (workspace / "answer.json").write_text(json.dumps({
            "answer": "Yes.", "statement": "source_items.json contains an item with slug 'putting-intensive'",
            "path": "source_items.json", "predicate": "contains",
            "value": '"slug": "putting-intensive"'}))
        return {"ok": True, "subtype": "success", "num_turns": 2, "cost_usd": 0.02}

    chat_mod.ask("is there a putting class?", trips_path=trips_path, chat_path=chat_path,
                skills_dir=running_server["skills_dir"], maps_dir=maps_dir,
                seed=running_server["seed"], _runner=fake_runner)

    base = running_server["base"]
    st, hist = _get(base, "/api/chat")
    assert len(hist["open_learn_offers"]) == 1
    offer = hist["open_learn_offers"][0]
    assert offer["options"][0]["label"] == "Yes — learn it now"

    st, out = _post(base, "/api/chat/resolve", {"id": offer["id"], "choice": 1})
    assert st == 200 and out["learned"] is True
    assert (maps_dir / out["map"] / "map.yaml").exists()

    st, hist2 = _get(base, "/api/chat")
    assert hist2["open_learn_offers"] == []


def test_hive_endpoints_never_emit_a_trip_just_by_being_viewed(running_server):
    base = running_server["base"]
    before = len(trips_mod.read_all(running_server["trips_path"]))
    for path in ("/api/init", "/api/chat", "/api/run/state", "/api/memory",
                "/api/workflows", "/api/watchers", "/api/paper"):
        _get(base, path)
    after = len(trips_mod.read_all(running_server["trips_path"]))
    assert after == before
