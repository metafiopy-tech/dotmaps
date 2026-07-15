"""Post-hoc readout — NEVER in-loop (spec §3).

R1 (validity): rule-1 validation + integrity gate — every grown verifier must
fail on a deliberately broken workspace. Automated.
R2 (traversability): probe-certify at an owned rung. Automated (delegates to
the existing probe).
R3 (recovery): side-by-side scaffold of grown checks vs the withheld human
map's checks, for Joe's qualitative pass. The comparison target enters
context HERE for the first time, after the run.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..corpus import verifier_can_fail
from ..models import Map


from .banking import break_copy as _break_copy  # shared with bank-time gate


def r1_validity(grown_map_dir: str | Path, seed_dir: str | Path) -> dict[str, Any]:
    m = Map.load(grown_map_dir)
    problems = m.validate()
    circular: list[str] = []
    with tempfile.TemporaryDirectory(prefix="grow-broken-") as td:
        broken = Path(td) / "broken"
        _break_copy(Path(seed_dir), broken)
        for d in m.dots:
            if not verifier_can_fail(grown_map_dir, d.id, broken):
                circular.append(d.id)
    return {"rule1_problems": problems, "circular_checks": circular,
            "dots": len(m.dots),
            "passed": not problems and not circular}


def r3_scaffold(grown_map_dir: str | Path, human_map_dir: str | Path) -> str:
    """Side-by-side listing for the qualitative recovery pass."""
    grown, human = Map.load(grown_map_dir), Map.load(human_map_dir)
    lines = ["# R3 — recovery comparison (post-hoc; human map was withheld)",
             "", f"## Grown map: {grown.name} ({len(grown.dots)} dots)"]
    for d in grown.dots:
        lines.append(f"  [{d.id}] {d.statement}")
    lines += ["", f"## Withheld human map: {human.name} ({len(human.dots)} dots)"]
    for d in human.dots:
        lines.append(f"  [{d.id}] {d.statement}")
    lines += ["", "## Joe's pass (fill in)",
              "- rediscovered: ", "- missed: ",
              "- found that the human didn't: "]
    return "\n".join(lines) + "\n"


def readout(run_dir: str | Path, seed_dir: str | Path,
            human_map_dir: str | Path | None = None) -> dict[str, Any]:
    run = Path(run_dir)
    grown = run / "grown-map"
    out: dict[str, Any] = {"run_dir": str(run)}
    if not grown.exists():
        out["r1"] = {"passed": False, "reason": "no map was grown"}
        return out
    out["r1"] = r1_validity(grown, seed_dir)
    out["r2"] = ("run `dotmaps probe` on the grown map for R2 "
                 "(traversability is a live-model measurement)")
    if human_map_dir:
        scaffold = r3_scaffold(grown, human_map_dir)
        (run / "r3_comparison.md").write_text(scaffold)
        out["r3_scaffold"] = str(run / "r3_comparison.md")
    (run / "readout.json").write_text(json.dumps(out, indent=2))
    return out
