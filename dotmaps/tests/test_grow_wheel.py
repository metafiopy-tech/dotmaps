"""Full-wheel integration: scripted learner grows a map from a cold seed,
and the grown map is judged by the EXISTING gates — rule-1 validation and the
integrity gate — with zero special treatment. This is the whole v0 claim in
miniature, minus the live model."""
import json
from pathlib import Path

from dotmaps.corpus import verifier_can_fail
from dotmaps.grow.clock import ClockConfig
from dotmaps.grow.learner import ScriptedLearner
from dotmaps.grow.runner import grow
from dotmaps.models import Map


def make_seed(tmp_path: Path) -> Path:
    seed = tmp_path / "cold-env"
    seed.mkdir()
    (seed / "export.json").write_text(json.dumps(
        [{"slug": "a", "title": "A"}, {"slug": "b", "title": "B"},
         {"slug": "c", "title": "C"}]))
    (seed / "README.txt").write_text("nightly export, 3 records")
    return seed


MOVES = [
    # poke around
    {"poke": {"tool": "filesystem.read_file", "args": {"path": "README.txt"}}},
    {"poke": {"tool": "filesystem.read_file", "args": {"path": "export.json"}}},
    # a true invariant -> banks
    {"propose": {"statement": "the export file holds 3 records",
                 "steps": [{"tool": "filesystem.read_file",
                            "args": {"path": "export.json"}}],
                 "expect": {"predicate": "json_item_count", "value": 3}}},
    # a FALSE claim -> stays hypothesis, later fogs
    {"propose": {"statement": "the README mentions weekly exports",
                 "steps": [{"tool": "filesystem.read_file",
                            "args": {"path": "README.txt"}}],
                 "expect": {"predicate": "contains", "value": "weekly"}}},
    # a mutation mechanism -> banks, becomes a level-1 dot
    {"propose": {"statement": "a copy of the export written to backup.json reads back with 3 records",
                 "steps": [{"tool": "filesystem.read_file",
                            "args": {"path": "export.json"}},
                           {"tool": "filesystem.write_file",
                            "args": {"path": "backup.json",
                                     "content": '[{"slug":"a"},{"slug":"b"},{"slug":"c"}]'}},
                           {"tool": "filesystem.read_file",
                            "args": {"path": "backup.json"}}],
                 "expect": {"predicate": "json_item_count", "value": 3}}},
    {"rest": True},
]


def test_wheel_grows_a_valid_map_that_survives_the_gates(tmp_path):
    seed = make_seed(tmp_path)
    run_dir = tmp_path / "run"
    # forage gets one shot then fogs (scripted learner rests during forage)
    cfg = ClockConfig(max_pokes=40, max_spirals=1, forage_attempts=1,
                      window_k=5, epsilon=1)
    summary = grow(seed, run_dir, ScriptedLearner(list(MOVES)), cfg=cfg,
                   say=lambda s: None)

    # the false rule fogged, honestly declared
    fog = (run_dir / "fog.md").read_text()
    assert "weekly" in fog

    # a map was grown
    assert summary["grown_map"]
    grown = Path(summary["grown_map"])

    # GATE 1 — rule-1 validation, same as any map
    m = Map.load(grown)
    assert m.validate() == []
    ids = [d.id for d in m.dots]
    assert len(ids) == 2  # invariant + mutation dots; wall/false rules absent

    # dependency heuristic: the mutation dot depends on the invariant dot
    mut = [d for d in m.dots if "backup" in d.statement][0]
    inv = [d for d in m.dots if "3 records" in d.statement and d.id != mut.id][0]
    assert inv.id in mut.depends_on

    # GATE 2 — integrity: every grown verifier must FAIL on a broken workspace
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "export.json").write_text("[]")  # wrong count, no backup
    for d in m.dots:
        assert verifier_can_fail(grown, d.id, broken), \
            f"grown check {d.id} passed on a broken workspace (circularity)"

    # journal is append-only and populated; novelty series logged
    assert (run_dir / "poke_journal.jsonl").exists()
    assert (run_dir / "novelty.jsonl").exists()
    assert len((run_dir / "primitives").read_text() if False else
               list((run_dir / "primitives").glob("*.yaml"))) == 2
