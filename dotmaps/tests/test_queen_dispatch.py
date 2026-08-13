"""Q2 gate: the dispatcher routes manifest coverage and staffs the frontier,
dry-run native — zero model calls under any circumstance."""
import shutil
from pathlib import Path

from dotmaps.queen import dispatch as dispatch_mod
from dotmaps.queen import surface as surface_mod
from dotmaps.queen import trips as trips_mod

REPO = Path(__file__).resolve().parents[2]


def _fresh_skills(tmp_path) -> Path:
    """A disposable copy of skills/ — C3 (Q4) writes decay updates on
    every covered invocation, and tests must never mutate the committed
    skill cards (same convention as test_bank_certify.py's _fresh)."""
    d = tmp_path / "skills"
    shutil.copytree(REPO / "skills", d)
    return d


def test_pilot_routes_4_of_4_covered_at_zero_cost(tmp_path):
    p = tmp_path / "trips.jsonl"
    report = dispatch_mod.dispatch("pilot", trips_path=p, skills=_fresh_skills(tmp_path))
    assert len(report["covered"]) == 4
    assert not report["frontier"]
    assert all(d["passed"] for d in report["covered"])
    assert report["model_calls"] == 0 and report["cost_usd"] == 0.0

    trips = trips_mod.read_all(p)
    certified = [t for t in trips if t["type"] == "CERTIFIED"]
    assert len(certified) == 4


def test_migration_shows_5_frontier_with_staffing_plan(tmp_path):
    p = tmp_path / "trips.jsonl"
    report = dispatch_mod.dispatch("migration", trips_path=p)
    assert not report["covered"]
    assert len(report["frontier"]) == 5
    for item in report["frontier"]:
        assert item["verdict"] == "FRONTIER → grow"
        assert item["learner"] == "requires Q7 or human-run"
        assert "max_pokes" in item["budget"]
        assert item["inherited_primitives"] >= 0
    assert report["model_calls"] == 0 and report["cost_usd"] == 0.0


def test_unknown_target_raises_systemexit(tmp_path):
    try:
        dispatch_mod.dispatch("not-a-real-preset-or-path")
        assert False, "expected SystemExit"
    except SystemExit:
        pass


def test_end_to_end_dispatch_trips_surface_flow(tmp_path):
    """Two dispatch rounds on the same frontier predicate SHELVE it twice
    and the queen ESCALATEs with a concrete question; surface flips from
    calm to decision; resolving restores calm. No model in the loop."""
    p = tmp_path / "trips.jsonl"
    assert surface_mod.card(p)["status"] == "calm"

    dispatch_mod.dispatch("migration", trips_path=p)
    assert surface_mod.card(p)["status"] == "calm"   # only shelved once so far

    dispatch_mod.dispatch("migration", trips_path=p)
    c = surface_mod.card(p)
    assert c["status"] == "decision"
    assert len(c["escalations"]) == 5   # every migration predicate hit streak 2
    esc = c["escalations"][0]
    assert "shelved" in esc["question"].lower()
    assert len(esc["options"]) == 3

    surface_mod.resolve(esc["id"], 2, path=p)  # "keep shelving"
    remaining = surface_mod.card(p)["escalations"]
    assert esc["id"] not in {e["id"] for e in remaining}
    assert len(remaining) == 4


def test_covering_a_predicate_resets_its_shelve_streak(tmp_path):
    p = tmp_path / "trips.jsonl"
    sid = dispatch_mod._shelve_id("m", "d1")
    trips_mod.emit("SHELVED", path=p, id=sid, dot="d1")
    trips_mod.emit("SHELVED", path=p, id=sid, dot="d1")
    assert dispatch_mod._shelve_streak(p, sid) == 2
    trips_mod.emit("CERTIFIED", path=p, id=sid, dot="d1")
    assert dispatch_mod._shelve_streak(p, sid) == 0


def test_pilot_dispatch_never_mutates_the_committed_skills(tmp_path):
    """Q4 wiring lives here (dispatch -> reconsolidate.touch on every
    covered invocation) but must never touch the real repo files under
    test — every test passes its own disposable skills copy. Compares
    git status BEFORE/AFTER (not against an assumed-clean tree) since a
    real `dotmaps queen pilot` first flight legitimately leaves skills/
    with committed decay data of its own."""
    import subprocess
    def _status():
        return subprocess.run(["git", "status", "--porcelain", "skills/"],
                              cwd=REPO, capture_output=True, text=True).stdout
    before = _status()
    p = tmp_path / "trips.jsonl"
    dispatch_mod.dispatch("pilot", trips_path=p, skills=_fresh_skills(tmp_path))
    after = _status()
    assert after == before, f"pilot dispatch mutated tracked skills: {after!r} != {before!r}"


def test_pilot_dispatch_touches_decay_on_a_disposable_copy(tmp_path):
    """Deltas, not absolutes: the copied skill cards may already carry
    real accumulated decay data from a prior `dotmaps queen pilot` first
    flight against the committed repo — this asserts the invocation
    counter advances by exactly one per certified dot this round, whatever
    it started at."""
    import yaml
    p = tmp_path / "trips.jsonl"
    skills = _fresh_skills(tmp_path)
    before = {f.name: (yaml.safe_load(f.read_text()).get("decay", {}).get("invocations") or 0)
             for f in skills.glob("*.yaml")}
    dispatch_mod.dispatch("pilot", trips_path=p, skills=skills)
    after = {f.name: yaml.safe_load(f.read_text()).get("decay", {}).get("invocations")
            for f in skills.glob("*.yaml")}
    touched = [name for name in before if after[name] == before[name] + 1]
    assert len(touched) == 4


def test_check_budget_wired_but_never_called_in_dry_run(tmp_path):
    from dotmaps.grow.clock import ClockConfig, PhaseClock
    p = tmp_path / "trips.jsonl"

    # dry-run dispatch never spends this budget
    dispatch_mod.dispatch("migration", trips_path=p)
    assert not any(t["type"] == "BUDGET_EXHAUSTED" for t in trips_mod.read_all(p))

    # but it's real and fires on demand, for the live path (Q7) to call
    clock = PhaseClock(ClockConfig(max_pokes=1))
    clock.tick_poke()
    fired = dispatch_mod.check_budget(clock, trips_path=p)
    assert fired
    assert any(t["type"] == "BUDGET_EXHAUSTED" for t in trips_mod.read_all(p))
