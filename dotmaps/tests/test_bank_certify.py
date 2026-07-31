"""G2 gates: oracle-first ordering, conviction, coverage math."""
import json
from pathlib import Path
import yaml
from dotmaps.bank.certify import certify_all, wilson, THETA_MIN

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "corpus" / "pilot" / "seed-ws"


def _fresh(tmp_path):
    import shutil
    d = tmp_path / "skills"
    shutil.copytree(REPO / "skills", d)
    return d


def test_convicted_skills_get_no_certificate_math(tmp_path):
    out = certify_all(_fresh(tmp_path), SEED)
    convicted = [r for r in out["results"] if r["status"] == "convicted"]
    assert convicted, "expected the vacuous json_parses skill to convict"
    for r in convicted:
        assert r["wilson"] is None          # gate FIRST — no math after fail
        assert "NON-DISCRIMINATING" in r["verdict"]


def test_certified_clear_theta_floor(tmp_path):
    out = certify_all(_fresh(tmp_path), SEED)
    for r in out["results"]:
        if r["status"] == "certified":
            assert r["wilson"][0] >= THETA_MIN


def test_manifest_coverage_excludes_convicted(tmp_path):
    d = _fresh(tmp_path)
    certify_all(d, SEED)
    m = json.loads((d / "manifest.json").read_text())
    covered = set(m["coverage"].values())
    for f in d.glob("*.yaml"):
        s = yaml.safe_load(f.read_text())
        if s["certificate"]["status"] != "certified":
            assert s["name"] not in covered


def test_wilson_floor_at_20_of_20():
    lo, hi = wilson(20, 20)
    assert 0.83 < lo < 0.85 and hi > 0.999
