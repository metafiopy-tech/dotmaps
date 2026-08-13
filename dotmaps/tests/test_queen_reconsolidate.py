"""Q4 gate: C3 reconsolidation — write-on-read, never touching crystallized
method.steps or check (law 3)."""
import shutil
import time
from pathlib import Path

import yaml

from dotmaps.bank.certify import certify_all
from dotmaps.queen import reconsolidate

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "corpus" / "pilot" / "seed-ws"
CERTIFIED_SKILL = "the-source-items-json-file-contains-items-with-a.yaml"


def _fresh_skill(tmp_path) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    target = d / CERTIFIED_SKILL
    shutil.copy(REPO / "skills" / CERTIFIED_SKILL, target)
    card = yaml.safe_load(target.read_text())
    card["decay"] = {"last_used": None, "stability": None, "shelf_recheck": None}
    target.write_text(yaml.safe_dump(card, sort_keys=False))
    return target


def _reset_all_decay(skills_dir: Path) -> None:
    """Test isolation: a real `dotmaps queen pilot` first flight against
    the committed repo legitimately leaves OTHER skills' decay non-null.
    sweep_shelf_rechecks() scans every certified card in the dir, so a
    test targeting ONE skill must null out the rest or it inherits
    however-decayed the ambient repo happens to be."""
    for f in skills_dir.glob("*.yaml"):
        card = yaml.safe_load(f.read_text())
        card["decay"] = {"last_used": None, "stability": None, "shelf_recheck": None}
        f.write_text(yaml.safe_dump(card, sort_keys=False))


def _fresh_skills_dir(tmp_path) -> Path:
    d = tmp_path / "skills"
    shutil.copytree(REPO / "skills", d)
    _reset_all_decay(d)
    return d


def test_two_invocations_update_the_clock(tmp_path):
    f = _fresh_skill(tmp_path)
    r1 = reconsolidate.touch(f)
    r2 = reconsolidate.touch(f)
    assert r1["invocations"] == 1 and r2["invocations"] == 2
    assert r2["stability"] > r1["stability"]
    card = yaml.safe_load(f.read_text())
    assert card["decay"]["invocations"] == 2
    assert len(card["usage"]) == 2


def test_method_and_check_bytes_hash_identical_before_and_after(tmp_path):
    f = _fresh_skill(tmp_path)
    original = yaml.safe_load(f.read_text())
    orig_method = reconsolidate._method_bytes(original)
    orig_check = reconsolidate._check_bytes(original)

    reconsolidate.touch(f)
    reconsolidate.touch(f)

    after = yaml.safe_load(f.read_text())
    assert reconsolidate._method_bytes(after) == orig_method
    assert reconsolidate._check_bytes(after) == orig_check


def test_due_for_recheck_false_when_fresh(tmp_path):
    f = _fresh_skill(tmp_path)
    reconsolidate.touch(f)
    assert reconsolidate.due_for_recheck(f) is False


def test_two_invocations_then_injected_time_advance_triggers_one_recheck_trip(tmp_path):
    skills_dir = _fresh_skills_dir(tmp_path)
    trips_path = tmp_path / "trips.jsonl"
    target = skills_dir / CERTIFIED_SKILL

    now = time.time()
    reconsolidate.touch(target, trips_path=trips_path, now_ts=now)
    r2 = reconsolidate.touch(target, trips_path=trips_path, now_ts=now)
    assert r2["invocations"] == 2

    assert reconsolidate.due_for_recheck(target, now_ts=now) is False  # fresh, not due yet

    far_future = now + reconsolidate.SHELF_HALF_LIFE_DAYS * 86400 * 20  # decades past half-life
    fired = reconsolidate.sweep_shelf_rechecks(skills_dir, trips_path=trips_path, now_ts=far_future)

    assert len(fired) == 1
    assert fired[0]["type"] == "SHELVED"
    assert fired[0]["data"]["skill"] == "the-source-items-json-file-contains-items-with-a"

    from dotmaps.queen import trips as trips_mod
    shelved = [t for t in trips_mod.read_all(trips_path) if t["type"] == "SHELVED"]
    assert len(shelved) == 1

    card = yaml.safe_load(target.read_text())
    assert card["decay"]["shelf_recheck"] is not None


def test_recert_resets_the_decay_clock(tmp_path):
    skills_dir = _fresh_skills_dir(tmp_path)
    trips_path = tmp_path / "trips.jsonl"
    target = skills_dir / CERTIFIED_SKILL

    now = time.time()
    reconsolidate.touch(target, trips_path=trips_path, now_ts=now)
    far_future = now + reconsolidate.SHELF_HALF_LIFE_DAYS * 86400 * 20
    reconsolidate.sweep_shelf_rechecks(skills_dir, trips_path=trips_path, now_ts=far_future)
    assert reconsolidate.due_for_recheck(target, now_ts=far_future) is True

    # deterministic re-cert (free, no model) — the certified status holds
    out = certify_all(skills_dir, SEED)
    assert any(r["name"] == "the-source-items-json-file-contains-items-with-a"
              and r["status"] == "certified" for r in out["results"])

    reconsolidate.reset_after_recert(target, now_ts=far_future)
    assert reconsolidate.due_for_recheck(target, now_ts=far_future) is False
    card = yaml.safe_load(target.read_text())
    assert card["decay"]["shelf_recheck"] is None
    assert card["decay"]["stability"] == reconsolidate.STABILITY_INCREMENT

    # law 3, end to end across touch -> sweep -> recert -> reset
    original = yaml.safe_load((REPO / "skills" / CERTIFIED_SKILL).read_text())
    assert reconsolidate._method_bytes(card) == reconsolidate._method_bytes(original)
    assert reconsolidate._check_bytes(card) == reconsolidate._check_bytes(original)
