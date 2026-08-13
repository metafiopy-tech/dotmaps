"""Q6 gate: the homeostasis tick — one SLEEP trip, idempotent on rerun."""
import shutil
import time
from pathlib import Path

import yaml

from dotmaps.queen import reconsolidate
from dotmaps.queen import sleep as sleep_mod
from dotmaps.queen import trips as trips_mod

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "corpus" / "pilot" / "seed-ws"


def _fresh_skills(tmp_path) -> Path:
    d = tmp_path / "skills"
    shutil.copytree(REPO / "skills", d)
    return d


def test_full_run_completes_with_one_sleep_trip(tmp_path):
    skills = _fresh_skills(tmp_path)
    trips_path = tmp_path / "trips.jsonl"
    summary = sleep_mod.sleep(skills_dir=skills, seed=SEED, trips_path=trips_path)
    assert "coverage" in summary and "frontier" in summary
    trips = trips_mod.read_all(trips_path)
    sleeps = [t for t in trips if t["type"] == "SLEEP"]
    assert len(sleeps) == 1


def test_idempotent_on_immediate_rerun(tmp_path):
    skills = _fresh_skills(tmp_path)
    trips_path = tmp_path / "trips.jsonl"
    now = time.time()
    s1 = sleep_mod.sleep(skills_dir=skills, seed=SEED, trips_path=trips_path, now_ts=now)
    s2 = sleep_mod.sleep(skills_dir=skills, seed=SEED, trips_path=trips_path, now_ts=now)
    assert s1["coverage"] == s2["coverage"]
    assert s1["frontier"] == s2["frontier"]
    assert s1["dedup_conflicts"] == s2["dedup_conflicts"] == []
    # nothing newly decayed in zero elapsed time -> zero shelf rechecks both ticks
    assert s1["shelf_rechecks"] == 0
    assert s2["shelf_rechecks"] == 0
    trips = trips_mod.read_all(trips_path)
    assert len([t for t in trips if t["type"] == "SLEEP"]) == 2


def test_due_shelf_recheck_executes_and_resets(tmp_path):
    skills = _fresh_skills(tmp_path)
    trips_path = tmp_path / "trips.jsonl"
    target = skills / "the-source-items-json-file-contains-items-with-a.yaml"

    now = time.time()
    reconsolidate.touch(target, trips_path=trips_path, now_ts=now)
    far_future = now + reconsolidate.SHELF_HALF_LIFE_DAYS * 86400 * 20

    summary = sleep_mod.sleep(skills_dir=skills, seed=SEED, trips_path=trips_path,
                              now_ts=far_future)
    assert summary["shelf_rechecks"] == 1
    assert "the-source-items-json-file-contains-items-with-a" in summary["shelf_recheck_skills"]

    card = yaml.safe_load(target.read_text())
    assert card["certificate"]["status"] == "certified"   # re-cert held
    assert reconsolidate.due_for_recheck(target, now_ts=far_future) is False  # reset

    # a second tick at the SAME far_future timestamp is now idempotent —
    # the reset already happened
    summary2 = sleep_mod.sleep(skills_dir=skills, seed=SEED, trips_path=trips_path,
                               now_ts=far_future)
    assert summary2["shelf_rechecks"] == 0


def test_dedup_sweep_flags_without_rewriting(tmp_path):
    skills = _fresh_skills(tmp_path)
    trips_path = tmp_path / "trips.jsonl"
    before = {f.name: f.read_text() for f in skills.glob("*.yaml")}
    sleep_mod.sleep(skills_dir=skills, seed=SEED, trips_path=trips_path)
    # no conflicts expected in the real skill set, and no file's method/
    # check content should have moved (only decay/certificate blocks may)
    for f in skills.glob("*.yaml"):
        before_card = yaml.safe_load(before[f.name])
        after_card = yaml.safe_load(f.read_text())
        assert before_card["method"] == after_card["method"]
        assert before_card["check"] == after_card["check"]


def test_sleep_module_defaults_point_at_the_real_repo_paths():
    """`dotmaps sleep` (no args, cron-ready) relies on these defaults —
    proven live against the real skills/ and corpus/pilot/seed-ws by the
    acceptance run, not by a test that would mutate tracked files."""
    assert sleep_mod.DEFAULT_SKILLS == REPO / "skills"
    assert sleep_mod.DEFAULT_SEED == REPO / "corpus" / "pilot" / "seed-ws"
