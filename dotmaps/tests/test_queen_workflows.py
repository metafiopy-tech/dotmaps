"""Tab 4: named workflows — a map + its coverage state, seed and chat-born."""
import json
import shutil
from pathlib import Path

import pytest
import yaml

from dotmaps.queen import trips as trips_mod
from dotmaps.queen import workflows as workflows_mod

REPO = Path(__file__).resolve().parents[2]


def test_seed_workflows_present():
    names = {wf["name"] for wf in workflows_mod.SEED_WORKFLOWS}
    assert names == {"check-demo-workspace", "migrate-the-menu-data"}


@pytest.mark.parametrize("phrase,expected", [
    ("Can you check the demo workspace for me?", "check-demo-workspace"),
    ("please migrate the menu data today", "migrate-the-menu-data"),
    ("what's the weather", None),
])
def test_match_trigger(phrase, expected, tmp_path):
    wf = workflows_mod.match_trigger(phrase, maps_dir=tmp_path)
    assert (wf["name"] if wf else None) == expected


def test_coverage_pilot_fully_covered(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    wf = workflows_mod.find("check-demo-workspace", maps_dir=tmp_path)
    cov = workflows_mod.coverage(wf, skills, maps_dir=tmp_path)
    assert cov == {"covered": 4, "total": 4}


def test_coverage_migration_not_covered(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    wf = workflows_mod.find("migrate-the-menu-data", maps_dir=tmp_path)
    cov = workflows_mod.coverage(wf, skills, maps_dir=tmp_path)
    assert cov["total"] == 5
    assert cov["covered"] < cov["total"]


def test_chat_born_workflow_discovered_from_map_dir(tmp_path):
    maps_dir = tmp_path / "maps"
    map_dir = maps_dir / "map-chat-hello"
    map_dir.mkdir(parents=True)
    (map_dir / "chat_trigger.json").write_text(json.dumps({
        "trigger": "how many items", "statement": "source_items.json has 5 items",
        "answer": "There are 5 items.",
    }))
    all_wf = workflows_mod.all_workflows(maps_dir)
    chat_wf = [w for w in all_wf if w["kind"] == "chat"]
    assert len(chat_wf) == 1
    assert chat_wf[0]["name"] == "map-chat-hello"
    assert chat_wf[0]["trigger_phrases"] == ["how many items"]
    wf = workflows_mod.match_trigger("how many items are there", maps_dir=maps_dir)
    assert wf is not None and wf["name"] == "map-chat-hello"


def test_payload_never_emits_a_trip(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    trips_path = tmp_path / "trips.jsonl"
    before = len(trips_mod.read_all(trips_path))
    rows = workflows_mod.payload(skills, maps_dir=tmp_path, trips_path=trips_path)
    after = len(trips_mod.read_all(trips_path))
    assert after == before
    assert {r["name"] for r in rows} >= {"check-demo-workspace", "migrate-the-menu-data"}
    for r in rows:
        assert "description" in r and "covered" in r and "total" in r
