"""Flight-2 gap closure: harvest wired into sleep; authorized live budgets;
certification never pollutes the repo seed."""
import json, shutil
from pathlib import Path
import yaml
from dotmaps.queen import sleep as sleep_mod
from dotmaps.queen import trips as trips_mod
from dotmaps.queen.live import TINY_LIVE_BUDGET, AUTHORIZED_BUDGET
from dotmaps.bank.certify import certify_all

REPO = Path(__file__).resolve().parents[2]


def _synthetic_live_run(base: Path, canary: str) -> Path:
    """A minimal, self-contained live-run fixture (primitives/ only) with a
    statement/expect combo guaranteed novel — unlike replaying the real
    committed `runs/queen-live/migration` fixture, this never depends on
    how much of THAT run's harvest already landed in the committed skills/
    library from a prior flight (R-DEDUP would otherwise legitimately
    dedupe it to zero, which is a different claim — see
    test_run_never_touches_the_repo_seed / assure's idempotence check)."""
    run = base / "synthetic-live-run"
    (run / "primitives").mkdir(parents=True)
    rule = {
        "id": "rTEST001",
        "statement": f"TEST-FIXTURE canary primitive {canary}, unique to this test",
        "steps": [{"tool": "filesystem.read_file", "args": {"path": "migration.json"}}],
        "expect": {"predicate": "contains", "value": canary},
        "confirmed_by_poke": 1, "spiral": 1, "banked_at": "2026-01-01T00:00:00",
    }
    (run / "primitives" / "rTEST001.yaml").write_text(yaml.safe_dump(rule, sort_keys=False))
    return run


def test_authorized_budget_is_a_campaign_not_a_smoke():
    assert AUTHORIZED_BUDGET.max_pokes >= 20 * TINY_LIVE_BUDGET.max_pokes


def test_sleep_harvests_live_primitives_as_candidates(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    live = tmp_path / "runs" / "queen-live"
    live.mkdir(parents=True)
    _synthetic_live_run(live, canary="queen-harvest-test-canary-9f3c21")
    before = len(list(skills.glob("*.yaml")))
    out = sleep_mod.sleep(skills_dir=skills,
                          seed=REPO / "corpus" / "pilot" / "seed-ws",
                          trips_path=tmp_path / "trips.jsonl",
                          live_root=live)
    assert out["harvested_candidates"] >= 1
    assert len(list(skills.glob("*.yaml"))) == before + out["harvested_candidates"]
    # harvest is idempotent (R-DEDUP): second sleep harvests nothing new
    out2 = sleep_mod.sleep(skills_dir=skills,
                           seed=REPO / "corpus" / "pilot" / "seed-ws",
                           trips_path=tmp_path / "trips.jsonl",
                           live_root=live)
    assert out2["harvested_candidates"] == 0


def test_certify_never_pollutes_the_repo_seed(tmp_path):
    seed = REPO / "corpus" / "pilot" / "seed-ws"
    snapshot = sorted(p.name for p in seed.rglob("*") if p.is_file())
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    # include the write-skill from the live run if harvested cards exist
    live = REPO / "runs" / "queen-live" / "migration"
    from dotmaps.bank.extractor import bank as bank_extract
    bank_extract([live], skills)
    certify_all(skills, seed)
    after = sorted(p.name for p in seed.rglob("*") if p.is_file())
    assert after == snapshot, "certification mutated the repo seed"
