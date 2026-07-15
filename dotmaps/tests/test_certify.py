"""Phase-3 probe harness — deterministic tests via the scripted driver.

The live weak-model probe (ollama) produces the real certification artifact;
these prove the probe mechanics: fresh workspaces, correct stats, ≥4/5 rule.
"""
import dataclasses
import json

from conftest import SMOKE_MAP

from dotmaps.certify import probe, write_artifact
from dotmaps.models import Map


def test_probe_runs_fresh_workspaces_and_certifies(tmp_path):
    m = Map.load(SMOKE_MAP)  # scripted driver: deterministic all-green
    stats = probe(m, tmp_path / "probes", runs=3)
    assert stats["runs"] == 3
    assert stats["all_green"] == 3
    assert stats["certified"] is True
    assert stats["required"] == 3  # ceil(0.8 * 3)
    # fresh instance per run: each workspace exists and completed independently
    for i in (1, 2, 3):
        ws = tmp_path / "probes" / f"probe-{i:02d}"
        assert (ws / "hello.txt").read_text() == "MAGIC-TOKEN present\n"


def test_probe_flunks_a_failing_map(tmp_path):
    m = Map.load(SMOKE_MAP)
    # sabotage the script: dot 002's action writes the wrong content
    traveler = dataclasses.replace(
        m.traveler,
        script={**m.traveler.script,
                "002": [{"tool": "filesystem.write_file", "path": "hello.txt",
                          "content": "wrong content\n"}]},
    )
    bad = dataclasses.replace(m, traveler=traveler,
                              budget=dataclasses.replace(m.budget, max_cycles=4))
    stats = probe(bad, tmp_path / "probes", runs=2)
    assert stats["all_green"] == 0
    assert stats["certified"] is False


def test_probe_artifact_written_into_map_repo(tmp_path):
    # write_artifact targets the map repo; point a copy at tmp to avoid
    # touching the real maps/ tree from a unit test
    import shutil
    map_copy = tmp_path / "map-smoke"
    shutil.copytree(SMOKE_MAP, map_copy)
    m = Map.load(map_copy)
    stats = probe(m, tmp_path / "probes", runs=2)
    out = write_artifact(m, stats)
    assert out == map_copy / "certification" / "probe_stats.json"
    assert json.loads(out.read_text())["map"] == "smoke"
