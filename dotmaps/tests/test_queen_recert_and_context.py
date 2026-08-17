"""H6 (HARDENING_BRIEF): re-cert semantics + formation context. The audit's
two regression tests, verbatim: a due skill that fails its oracle on re-cert
must be convicted, never get its freshness reset, and never emit a success
trip; a certificate's context fingerprint changing must make bank/route.py
refuse the skill until it is re-certified.
"""
import shutil
import time
from pathlib import Path

import yaml

from dotmaps.bank.route import route_map
from dotmaps.queen import reconsolidate
from dotmaps.queen import sleep as sleep_mod
from dotmaps.queen import trips as trips_mod

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "corpus" / "pilot" / "seed-ws"
TARGET_SKILL = "the-source-items-json-file-contains-items-with-a"


def _fresh_skills(tmp_path) -> Path:
    d = tmp_path / "skills"
    shutil.copytree(REPO / "skills", d)
    for f in d.glob("*.yaml"):
        card = yaml.safe_load(f.read_text())
        card["decay"] = {"last_used": None, "stability": None, "shelf_recheck": None}
        f.write_text(yaml.safe_dump(card, sort_keys=False))
    return d


# --------------------------------------------------------------------------- #
# re-cert semantics: a due skill that fails re-cert is convicted, never reset #
# --------------------------------------------------------------------------- #

def test_due_skill_that_fails_recert_is_convicted_never_reset(tmp_path):
    skills = _fresh_skills(tmp_path)
    trips_path = tmp_path / "trips.jsonl"
    target = skills / f"{TARGET_SKILL}.yaml"

    now = time.time()
    reconsolidate.touch(target, trips_path=trips_path, now_ts=now)
    far_future = now + reconsolidate.SHELF_HALF_LIFE_DAYS * 86400 * 20

    # sabotage the check so certify_all's re-cert (inside sleep()) convicts
    # it on the intact seed — a real oracle failure, not a mocked one.
    card = yaml.safe_load(target.read_text())
    card["check"] = {"predicate": "contains", "value": "this-string-will-never-be-found"}
    target.write_text(yaml.safe_dump(card, sort_keys=False))

    last_used_before = yaml.safe_load(target.read_text())["decay"]["last_used"]

    summary = sleep_mod.sleep(skills_dir=skills, seed=SEED, trips_path=trips_path,
                              live_root=tmp_path / "nolive", now_ts=far_future)

    assert TARGET_SKILL in summary["convicted_on_recheck"]
    assert TARGET_SKILL not in summary["shelf_recheck_skills"]

    card_after = yaml.safe_load(target.read_text())
    assert card_after["certificate"]["status"] == "convicted"
    # freshness NOT reset — still the pre-recert last_used, still due
    assert card_after["decay"]["last_used"] == last_used_before
    assert reconsolidate.due_for_recheck(target, now_ts=far_future) is True

    records = trips_mod.read_all(trips_path)
    convicted_trips = [t for t in records if t["type"] == "CONVICTED"
                       and t["data"].get("skill") == TARGET_SKILL]
    assert len(convicted_trips) == 1
    assert "NOT reset" in convicted_trips[0]["data"]["action"]

    success_shelved = [t for t in records if t["type"] == "SHELVED"
                       and t["data"].get("skill") == TARGET_SKILL
                       and t["data"].get("action") == "re-certified this tick"]
    assert not success_shelved, "a failed re-cert must never emit a success trip"


# --------------------------------------------------------------------------- #
# formation context: a fingerprint mismatch refuses the skill until re-cert  #
# --------------------------------------------------------------------------- #

def test_route_refuses_stale_formation_context_until_recert(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)

    target = skills / f"{TARGET_SKILL}.yaml"
    card = yaml.safe_load(target.read_text())
    assert card["formation_context"]["seed_fingerprint"], "expected a real backfilled fingerprint"
    card["formation_context"]["seed_fingerprint"] = "0" * 16  # simulate stale/changed content
    target.write_text(yaml.safe_dump(card, sort_keys=False))

    map_data = {
        "name": "stale-context-probe", "version": "0.0.1", "domain": "test",
        "dots": [{"id": "d1", "statement": card["statement"]}],
    }
    map_path = tmp_path / "map.yaml"
    map_path.write_text(yaml.safe_dump(map_data))

    report = route_map(map_path, skills, SEED)
    assert not report["covered"], "a stale-context skill must never be trusted as covered"
    assert len(report["frontier"]) == 1
    assert "stale formation context" in report["frontier"][0]["reason"]


def test_route_still_covers_when_fingerprint_matches(tmp_path):
    """Sanity check: the new context gate is not a blanket refusal — a
    skill whose formation_context DOES match the current workspace still
    routes as covered, exactly as before H6."""
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    target = skills / f"{TARGET_SKILL}.yaml"
    card = yaml.safe_load(target.read_text())

    map_data = {
        "name": "matching-context-probe", "version": "0.0.1", "domain": "test",
        "dots": [{"id": "d1", "statement": card["statement"]}],
    }
    map_path = tmp_path / "map.yaml"
    map_path.write_text(yaml.safe_dump(map_data))

    report = route_map(map_path, skills, SEED)
    assert len(report["covered"]) == 1 and not report["frontier"]
    assert report["covered"][0]["passed"] is True
