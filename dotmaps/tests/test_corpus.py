"""Corpus generator integrity tests (experiment spec §1.1: tests required).

Three required properties:
  1. every variant's DAG is valid,
  2. every non-tautology verifier actually runs and CAN FAIL on a deliberately
     broken workspace,
  3. tier labels + variant content are reproducible from the recipe alone.
Plus the operators' individual contracts.
"""
import json
from pathlib import Path

import pytest
import yaml
from conftest import MAPS

from dotmaps.corpus import RecipeError, build_variant, check_dag, verifier_can_fail

RECIPES = MAPS.parent / "corpus" / "recipes" / "map2-pilot"
PILOT_RECIPES = ["t1-sparse-blunt", "t2-blunt", "t3-base", "t4-dense"]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out_base = tmp_path_factory.mktemp("corpus")
    variants = {}
    for r in PILOT_RECIPES:
        out = build_variant(RECIPES / f"{r}.yaml", out_base / r)
        variants[r] = out
    return variants


def test_all_pilot_variants_have_valid_dags(built):
    for name, out in built.items():
        manifest = yaml.safe_load((out / "map.yaml").read_text())
        assert check_dag(manifest) == [], f"{name}: invalid DAG"


def test_variant_json_records_recipe(built):
    v = json.loads((built["t1-sparse-blunt"] / "variant.json").read_text())
    assert v["tier"] == "T1"
    assert v["base"] == "content-migration"
    assert v["seed"] == 42
    assert v["dot_count"] == 3
    assert [op["op"] for op in v["operators"]] == ["sparsify", "blunt"]


def test_sparsify_keeps_terminal_and_splices_deps(built):
    manifest = yaml.safe_load((built["t1-sparse-blunt"] / "map.yaml").read_text())
    ids = [str(d["id"]) for d in manifest["dots"]]
    assert "m04" in ids and "m05" in ids  # terminals never removed
    assert len(ids) == 3
    # deps referencing removed dots were spliced, not left dangling
    assert check_dag(manifest) == []


def test_blunted_verifier_is_weaker_but_real(built, tmp_path):
    """T2's blunted m03 passes a case the original rejects (weaker), yet still
    fails on a broken workspace (real)."""
    import shutil
    import subprocess
    import sys

    variant = built["t2-blunt"]
    # a target where one item is complete but another is missing fields:
    # original m03 fails this; blunted m03 must PASS it (strictly weaker).
    ws = tmp_path / "ws"
    (ws / ".dotmaps").mkdir(parents=True)
    cfg = {"source": "source_items.json", "target": "target_items.json",
           "slug_field": "slug", "required_fields": ["title", "price"],
           "hash_fields": ["title"], "spot_hash_sample": 1,
           "links_field": "body", "internal_link_base": None}
    (ws / ".dotmaps" / "migration.json").write_text(json.dumps(cfg))
    items_src = [{"slug": "a", "title": "A", "price": "1", "body": ""},
                 {"slug": "b", "title": "B", "price": "2", "body": ""}]
    items_tgt = [{"slug": "a", "title": "A", "price": "1", "body": ""},
                 {"slug": "b"}]  # second item incomplete
    (ws / "source_items.json").write_text(json.dumps(items_src))
    (ws / "target_items.json").write_text(json.dumps(items_tgt))

    blunted = variant / "verifiers" / "m03_blunted.py"
    original = MAPS / "map-content-migration" / "verifiers" / "m03_fields_non_empty.py"
    r_blunt = subprocess.run([sys.executable, str(blunted), "--workspace", str(ws)],
                             capture_output=True)
    r_orig = subprocess.run([sys.executable, str(original), "--workspace", str(ws)],
                            capture_output=True)
    assert r_blunt.returncode == 0, "blunted check should accept the weak case"
    assert r_orig.returncode != 0, "original check must reject the weak case"


def test_every_nontautology_verifier_can_fail(built, tmp_path):
    broken = tmp_path / "broken"
    broken.mkdir()
    for name, out in built.items():
        manifest = yaml.safe_load((out / "map.yaml").read_text())
        taut = set(json.loads((out / "variant.json").read_text())["tautologized_dots"])
        for d in manifest["dots"]:
            if str(d["id"]) in taut:
                continue
            assert verifier_can_fail(out, str(d["id"]), broken), \
                f"{name}:{d['id']} passed on a broken workspace — not a real check"


def test_tautologize_always_passes_and_is_recorded(tmp_path):
    recipe = tmp_path / "t0.yaml"
    recipe.write_text(f"""
name: m2-t0-tautology
base: {MAPS / 'map-content-migration'}
tier: T0
seed: 0
operators:
  - op: tautologize
    dots: [m01, m02, m03, m04, m05]
""")
    out = build_variant(recipe, tmp_path / "t0")
    v = json.loads((out / "variant.json").read_text())
    assert v["tautologized_dots"] == ["m01", "m02", "m03", "m04", "m05"]
    # a tautology passes even on a broken workspace — that is its pathology
    broken = tmp_path / "broken"
    broken.mkdir()
    assert not verifier_can_fail(out, "m04", broken)


def test_reproducible_from_recipe(built, tmp_path):
    """Same recipe -> identical manifest + variant.json (determinism under seed)."""
    again = build_variant(RECIPES / "t1-sparse-blunt.yaml", tmp_path / "again")
    for f in ("map.yaml", "variant.json"):
        a = (built["t1-sparse-blunt"] / f).read_text()
        b = (again / f).read_text()
        assert a == b, f"{f} not reproducible"


def test_scramble_preserves_dag(tmp_path):
    recipe = tmp_path / "scr.yaml"
    recipe.write_text(f"""
name: m2-scrambled
base: {MAPS / 'map-content-migration'}
tier: T1
seed: 13
operators:
  - op: scramble
    k: 2
""")
    out = build_variant(recipe, tmp_path / "scr")
    manifest = yaml.safe_load((out / "map.yaml").read_text())
    assert check_dag(manifest) == []
    # and the wiring actually changed vs the base
    base = yaml.safe_load((MAPS / "map-content-migration" / "map.yaml").read_text())
    assert ([d.get("depends_on") for d in manifest["dots"]]
            != [d.get("depends_on") for d in base["dots"]])


def test_unknown_operator_rejected(tmp_path):
    recipe = tmp_path / "bad.yaml"
    recipe.write_text(f"""
name: bad
base: {MAPS / 'map-content-migration'}
tier: T1
operators: [{{op: verifier_synthesis}}]
""")
    with pytest.raises(RecipeError):
        build_variant(recipe, tmp_path / "bad-out")


def test_wilson_interval():
    from dotmaps.certify import wilson
    lo, hi = wilson(5, 5)
    assert 0.55 < lo < 0.60 and hi == 1.0  # 5/5 is NOT certainty at N=5
    lo0, hi0 = wilson(0, 5)
    assert lo0 == 0.0 and 0.40 < hi0 < 0.45
    assert wilson(0, 0) == (0.0, 0.0)
    # the separation the pilot decision rule leans on, stated concretely:
    # 0/5 vs 5/5 -> disjoint intervals (clear separation)
    assert wilson(0, 5)[1] < wilson(5, 5)[0]
    # 4/5 vs 5/5 -> overlapping intervals (NOT separable at N=5)
    assert wilson(4, 5)[1] > wilson(5, 5)[0]
