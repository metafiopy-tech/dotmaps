"""Corpus generator — the Instrument Experiment (experiment spec §1.1).

Turns a certified base map into a family of variants of KNOWN quality: because
WE construct the degradations, the quality ordering is ground truth by
construction (the planted-classes move). Each variant is a full map repo the
existing harness runs unmodified — this module changes no harness semantics.

Operators (deterministic under `seed`, composable, applied in recipe order):
  sparsify(p)        remove fraction p of non-terminal dots (road density ↓)
  blunt(dot,...)     swap a verifier for a strictly weaker REAL check (recipe
                     supplies the weaker statement + verifier — human-authored;
                     verifier synthesis is explicitly not under test)
  scramble(k)        rewire k dependency edges to plausible-but-wrong orderings
                     (DAG validity preserved)
  defog()            delete the fog declaration (undeclared judgment residue)
  tautologize(dots)  replace verifiers with always-pass stubs — the known-worst
                     tier and the direct Goodhart probe
  densify(add,...)   add finer intermediate dots with real verifiers (recipe-
                     supplied, human-reviewed)

Tier is assigned by the recipe and recorded in variant.json alongside the full
operator list and seed, so the label is reproducible from the recipe alone.
"""

from __future__ import annotations

import json
import random
import shutil
import stat
from pathlib import Path
from typing import Any

import yaml

TAUTOLOGY_STUB = '''#!/usr/bin/env python3
"""TAUTOLOGIZED verifier (corpus T0 operator): always passes, checks nothing.
This is the planted Goodhart probe — a fake tollbooth. Never ship one."""
import json
print(json.dumps({{"dot": "{dot_id}", "pass": True,
                  "evidence": "tautologized check — nothing was verified"}}))
'''

# files that constitute a map repo (copied to every variant); certification/
# and examples/ are deliberately left behind — a variant earns its own.
_REPO_FILES = ("map.yaml", "Dockerfile", "fog.md", "blast_radius.md")


class RecipeError(ValueError):
    pass


def _portable(path) -> str:
    """Provenance paths are recorded relative to the CWD when possible —
    absolute machine paths in shipped artifacts are packaging poison."""
    import os
    try:
        return os.path.relpath(path)
    except ValueError:
        return str(path)


def load_recipe(recipe_path: str | Path) -> dict[str, Any]:
    recipe_path = Path(recipe_path).resolve()
    recipe = yaml.safe_load(recipe_path.read_text())
    for req in ("name", "base", "tier"):
        if req not in recipe:
            raise RecipeError(f"recipe missing required field {req!r}")
    recipe["_dir"] = recipe_path.parent
    return recipe


def build_variant(recipe_path: str | Path, out_dir: str | Path) -> Path:
    """Recipe -> full variant map repo at out_dir. Deterministic under seed."""
    recipe = load_recipe(recipe_path)
    base = (recipe["_dir"] / recipe["base"]).resolve()
    if not (base / "map.yaml").exists():
        raise RecipeError(f"base map not found at {base}")
    out = Path(out_dir).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # copy the base repo skeleton
    for f in _REPO_FILES:
        if (base / f).exists():
            shutil.copy2(base / f, out / f)
    shutil.copytree(base / "verifiers", out / "verifiers")

    manifest = yaml.safe_load((out / "map.yaml").read_text())
    manifest["name"] = recipe["name"]
    rng = random.Random(recipe.get("seed", 0))
    terminal = set(str(t) for t in recipe.get("terminal", []))
    tautologized: list[str] = []

    for op in recipe.get("operators", []):
        kind = op["op"]
        if kind == "sparsify":
            _op_sparsify(manifest, out, float(op["p"]), terminal, rng)
        elif kind == "blunt":
            _op_blunt(manifest, out, recipe["_dir"], op)
        elif kind == "scramble":
            _op_scramble(manifest, int(op["k"]), rng)
        elif kind == "defog":
            (out / "fog.md").unlink(missing_ok=True)
        elif kind == "tautologize":
            for d in op["dots"]:
                _op_tautologize(manifest, out, str(d))
                tautologized.append(str(d))
        elif kind == "densify":
            _op_densify(manifest, out, recipe["_dir"], op)
        else:
            raise RecipeError(f"unknown operator {kind!r}")

    problems = check_dag(manifest)
    if problems:
        raise RecipeError(f"variant DAG invalid after operators: {problems}")

    (out / "map.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    (out / "variant.json").write_text(json.dumps({
        "name": recipe["name"],
        "base": yaml.safe_load((base / "map.yaml").read_text())["name"],
        "base_path": _portable(base),
        "tier": recipe["tier"],
        "seed": recipe.get("seed", 0),
        "operators": recipe.get("operators", []),
        "tautologized_dots": tautologized,
        "dot_count": len(manifest["dots"]),
    }, indent=2, default=str) + "\n")
    return out


# --------------------------------------------------------------------------- #
# operators (manifest surgery)                                                 #
# --------------------------------------------------------------------------- #
def _dots(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return manifest["dots"]


def _find(manifest: dict[str, Any], dot_id: str) -> dict[str, Any]:
    for d in _dots(manifest):
        if str(d["id"]) == dot_id:
            return d
    raise RecipeError(f"no dot {dot_id!r} in manifest")


def _op_sparsify(manifest, out: Path, p: float, terminal: set[str],
                 rng: random.Random) -> None:
    """Remove round(p * len(non_terminal)) dots; splice deps transitively so
    the DAG stays valid. The terminal/outcome dots are never removed."""
    dots = _dots(manifest)
    non_terminal = [str(d["id"]) for d in dots if str(d["id"]) not in terminal]
    k = round(p * len(non_terminal))
    removed = set(rng.sample(sorted(non_terminal), k))
    dep_map = {str(d["id"]): [str(x) for x in d.get("depends_on", []) or []]
               for d in dots}

    def splice(deps: list[str]) -> list[str]:
        result: list[str] = []
        for dep in deps:
            if dep in removed:
                result.extend(splice(dep_map[dep]))  # inherit the removed dot's deps
            elif dep not in result:
                result.append(dep)
        return result

    for d in dots:
        if str(d["id"]) in removed:
            v = out / d["verifier"]
            v.unlink(missing_ok=True)
        else:
            d["depends_on"] = splice([str(x) for x in d.get("depends_on", []) or []])
    manifest["dots"] = [d for d in dots if str(d["id"]) not in removed]


def _op_blunt(manifest, out: Path, recipe_dir: Path, op: dict[str, Any]) -> None:
    """Swap statement+verifier for the recipe's strictly-weaker pair."""
    d = _find(manifest, str(op["dot"]))
    asset = (recipe_dir / op["verifier"]).resolve()
    if not asset.exists():
        raise RecipeError(f"blunt asset missing: {asset}")
    old = out / d["verifier"]
    old.unlink(missing_ok=True)
    new_rel = f"verifiers/{op['dot']}_blunted{asset.suffix}"
    shutil.copy2(asset, out / new_rel)
    _make_exec(out / new_rel)
    d["statement"] = op["statement"]
    d["verifier"] = new_rel


def _op_scramble(manifest, k: int, rng: random.Random) -> None:
    """Rewire k dependency edges to plausible-but-wrong targets, keeping the
    DAG acyclic (retry sampling until valid; deterministic under seed)."""
    dots = _dots(manifest)
    ids = [str(d["id"]) for d in dots]
    with_deps = [d for d in dots if d.get("depends_on")]
    if not with_deps:
        return
    for _ in range(k):
        for _attempt in range(50):
            d = rng.choice(with_deps)
            deps = [str(x) for x in d["depends_on"]]
            i = rng.randrange(len(deps))
            new_dep = rng.choice([x for x in ids if x != str(d["id"]) and x not in deps])
            old = deps[i]
            deps[i] = new_dep
            d["depends_on"] = deps
            if not _has_cycle(dots):
                break
            deps[i] = old  # undo and retry
            d["depends_on"] = deps
        else:
            raise RecipeError("scramble could not find an acyclic rewiring")


def _op_tautologize(manifest, out: Path, dot_id: str) -> None:
    d = _find(manifest, dot_id)
    (out / d["verifier"]).unlink(missing_ok=True)
    new_rel = f"verifiers/{dot_id}_tautology.py"
    (out / new_rel).write_text(TAUTOLOGY_STUB.format(dot_id=dot_id))
    _make_exec(out / new_rel)
    d["verifier"] = new_rel  # statement stays — a fake tollbooth looks real


def _op_densify(manifest, out: Path, recipe_dir: Path, op: dict[str, Any]) -> None:
    """Add recipe-supplied finer dots (real, human-reviewed verifiers) and
    optionally rewire existing dots to depend on them."""
    dots = _dots(manifest)
    for add in op.get("add", []):
        asset = (recipe_dir / add["verifier"]).resolve()
        if not asset.exists():
            raise RecipeError(f"densify asset missing: {asset}")
        new_rel = f"verifiers/{add['id']}_dense{asset.suffix}"
        shutil.copy2(asset, out / new_rel)
        _make_exec(out / new_rel)
        new_dot = {
            "id": str(add["id"]),
            "statement": add["statement"],
            "verifier": new_rel,
            "depends_on": [str(x) for x in add.get("depends_on", [])],
            "destructive": False,
        }
        after = add.get("after")
        if after is None:
            dots.insert(0, new_dot)
        else:
            idx = next(i for i, d in enumerate(dots) if str(d["id"]) == str(after))
            dots.insert(idx + 1, new_dot)
    for dot_id, new_deps in (op.get("rewire") or {}).items():
        _find(manifest, str(dot_id))["depends_on"] = [str(x) for x in new_deps]


def _make_exec(p: Path) -> None:
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# --------------------------------------------------------------------------- #
# integrity checks (experiment spec §1.1: tests required)                      #
# --------------------------------------------------------------------------- #
def check_dag(manifest: dict[str, Any]) -> list[str]:
    """Unknown deps, duplicate ids, cycles. Empty list = valid."""
    problems: list[str] = []
    dots = _dots(manifest)
    ids = [str(d["id"]) for d in dots]
    if len(ids) != len(set(ids)):
        problems.append("duplicate dot ids")
    idset = set(ids)
    for d in dots:
        for dep in d.get("depends_on", []) or []:
            if str(dep) not in idset:
                problems.append(f"dot {d['id']} depends_on unknown {dep}")
    if _has_cycle(dots):
        problems.append("dependency cycle")
    return problems


def _has_cycle(dots: list[dict[str, Any]]) -> bool:
    deps = {str(d["id"]): [str(x) for x in d.get("depends_on", []) or []]
            for d in dots}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in deps}

    def visit(node: str) -> bool:
        color[node] = GRAY
        for nxt in deps.get(node, []):
            if color.get(nxt) == GRAY:
                return True
            if color.get(nxt) == WHITE and visit(nxt):
                return True
        color[node] = BLACK
        return False

    return any(color[n] == WHITE and visit(n) for n in list(deps))


def verifier_can_fail(map_dir: str | Path, dot_id: str, broken_ws: str | Path) -> bool:
    """Integrity check: a non-tautology verifier must FAIL (exit != 0) on a
    deliberately broken workspace. A check that cannot fail is not a check."""
    from .models import Map
    from .verifier.runner import Verifier

    m = Map.load(map_dir)
    result = Verifier.for_map(m, mode="local").run_one(m, dot_id, Path(broken_ws).resolve())
    return not result.passed
