"""Release smoke (postcondition 7): the bundled journals replay offline, and
a deliberately broken workspace makes verifiers fail loudly. No models, no
network, no Docker."""
import json
from pathlib import Path

from dotmaps.corpus import verifier_can_fail
from dotmaps.models import Map
from dotmaps.scoreboard.replay import replay

ROOT = Path(__file__).parent.parent.parent
RUNS = ROOT / "runs"


def _capture(target):
    lines = []
    replay(target, out=lines.append)
    return "\n".join(lines)


def test_bundled_run_journal_replays():
    story = _capture(RUNS / "repro-3b-circular")
    assert "run started" in story and "cycle" in story
    assert "EATEN" in story or "attempt" in story


def test_bundled_grow_journal_replays():
    story = _capture(RUNS / "grow-001")
    assert "BANKED" in story        # the reward-hack banked rules...
    assert "spiral" in story


def test_bundled_journals_are_valid_jsonl():
    """Every bundled journal parses line-by-line — no truncation, no editing
    artifacts. (Contents are never validated beyond JSON: they are history.)"""
    journals = list(RUNS.rglob("events.jsonl")) + list(RUNS.rglob("poke_journal.jsonl"))
    assert len(journals) >= 8
    for j in journals:
        for line in j.read_text().splitlines():
            json.loads(line)


def test_broken_verifier_fails_loudly(tmp_path):
    """A deliberately broken workspace must turn every map-seq dot red —
    'a check that cannot fail is not a check', run against the shipped map."""
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "articles.json").write_text("[]")
    m = Map.load(ROOT / "maps" / "map-seq")
    for dot in m.dots:
        assert verifier_can_fail(ROOT / "maps" / "map-seq", dot.id, broken), \
            f"{dot.id} passed on a broken workspace"
