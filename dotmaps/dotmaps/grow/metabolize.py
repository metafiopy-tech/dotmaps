"""METABOLIZE — grow grown_map.yaml from the banked-primitives library.

Dots = dot-eligible banked rules (final step read-only, non-wall predicate).
Verifier per dot = its compiled check script. Dependencies v0 heuristic,
logged in the map itself for the post-hoc readout:

  - a PURE-READ rule (no mutation steps) is an invariant of the seed
    environment -> level-0 dot, no dependencies
  - a MUTATION rule (any write step) -> level-1 dot, depending on every
    level-0 dot that reads a file the mutation rule also touches (observed
    ordering: you learned the invariant before you learned the mechanism
    that must preserve it)

The grown map gets NO special treatment downstream: same schema, same rule-1
validation, same integrity gate, same probe as hand-made maps.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from .banking import compile_check, dot_eligible


def _touched_paths(rule: dict[str, Any]) -> set[str]:
    return {s["args"].get("path", "") for s in rule["steps"]
            if s["tool"].startswith("filesystem")}


def _is_mutation(rule: dict[str, Any]) -> bool:
    return any(s["tool"] == "filesystem.write_file" for s in rule["steps"])


def grow_map(primitives: list[dict[str, Any]], out_dir: str | Path,
             env_name: str, fog_lines: list[str] | None = None) -> Path:
    """Write a complete, self-contained map repo grown from primitives.
    Returns the map dir. Raises if no dot-eligible primitives exist."""
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    (out / "verifiers").mkdir(parents=True)

    eligible = [r for r in primitives if dot_eligible(r)]
    if not eligible:
        raise ValueError("no dot-eligible primitives — nothing to grow")

    invariants = [r for r in eligible if not _is_mutation(r)]
    mutations = [r for r in eligible if _is_mutation(r)]
    inv_ids = {r["id"] for r in invariants}

    dots = []
    for r in invariants + mutations:
        check = compile_check(r, out / "verifiers")
        deps: list[str] = []
        if _is_mutation(r):
            mine = _touched_paths(r)
            deps = sorted(i["id"] for i in invariants
                          if _touched_paths(i) & mine and i["id"] in inv_ids)
        dots.append({
            "id": r["id"],
            "statement": r["statement"],
            "verifier": f"verifiers/{check.name}",
            "depends_on": deps,
            "grown_from": {"spiral": r.get("spiral"),
                           "confirmed_by_poke": r.get("confirmed_by_poke"),
                           "kind": "mutation" if _is_mutation(r) else "invariant"},
        })

    manifest = {
        "name": f"grown-{env_name}",
        "version": "0.0.1",
        "domain": "grown",
        "mcp_required": ["filesystem.read_file", "filesystem.write_file"],
        "budget": {"max_cycles": 30},
        "traveler": {"driver": "ollama", "model": "qwen2.5-coder:7b",
                     "temperature": 0.0},
        "dots": dots,
    }
    (out / "map.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    fog = ["# Fog — declared honestly by the grow loop", ""]
    fog += fog_lines or ["(none fogged this run)"]
    (out / "fog.md").write_text("\n".join(fog) + "\n")
    (out / "blast_radius.md").write_text(
        "# Blast radius\n\nGrown map: workspace-local file operations only; "
        "no external services granted.\n")
    return out
