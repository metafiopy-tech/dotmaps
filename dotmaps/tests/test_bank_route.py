"""G3 gates: equipped traversal covers what it learned, refuses what it didn't."""
import shutil
from pathlib import Path
from dotmaps.bank.route import route_map

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "corpus" / "pilot" / "seed-ws"
SKILLS = REPO / "skills"


def test_equipped_traversal_of_learned_map_is_free():
    r = route_map(REPO / "runs/grow-005/grown-map/map.yaml", SKILLS, SEED)
    assert len(r["covered"]) == 4 and not r["frontier"]
    assert all(d["passed"] for d in r["covered"])
    assert r["model_calls"] == 0 and r["cost_usd"] == 0.0


def test_unlearned_map_routes_honestly_to_frontier():
    r = route_map(REPO / "maps/map-content-migration/map.yaml", SKILLS, SEED)
    assert not r["covered"]            # no fake coverage, ever
    assert len(r["frontier"]) == 5
    assert all("grow" in f["verdict"] for f in r["frontier"])


def test_convicted_skills_never_route(tmp_path):
    d = tmp_path / "skills"; shutil.copytree(SKILLS, d)
    import yaml
    for f in d.glob("*.yaml"):
        s = yaml.safe_load(f.read_text())
        s["certificate"]["status"] = "convicted"
        f.write_text(yaml.safe_dump(s, sort_keys=False))
    r = route_map(REPO / "runs/grow-005/grown-map/map.yaml", d, SEED)
    assert not r["covered"] and len(r["frontier"]) == 4
