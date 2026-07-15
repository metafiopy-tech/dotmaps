"""Probe certification — Phase 3 (spec §4.5).

"Run the WEAK traveler on a fresh instance 5 times. Certification requires
≥4/5 all-green within budget. Stall points → decompose that stretch into denser
dots and re-probe."

The probe is the empirical half of certification (the attack pass is the
adversarial half — see each map's certification/attack_report.md). Its output
is a stats artifact that SHIPS WITH THE MAP: buyers see the weak traveler's
actual success rate, not a promise.
"""

from __future__ import annotations

import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import Map
from .runtime.orchestrator import Orchestrator

PASS_RATIO = 0.8  # ≥4/5


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (closed form, no deps).

    The experiment layer's standard for pass-rate uncertainty (experiment spec
    §3 / item 3): at N=5 a raw 5/5 says '1.0' while Wilson honestly says
    '(0.57, 1.0)' — small-sample certainty theater is exactly what this kills.
    """
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def probe(
    m: Map,
    workspace_base: str | Path,
    runs: int = 5,
    seed_dir: Optional[str | Path] = None,
    verify_mode: str = "local",
    verbose: bool = False,
) -> dict[str, Any]:
    """Run the map's traveler on `runs` FRESH workspaces; collect stats.

    Each run starts from nothing (or a copy of seed_dir for maps whose
    verifiers need a compiled config) — no state crosses runs, so every run is
    an honest sample of the weak traveler's success rate.
    """
    base = Path(workspace_base).resolve()
    base.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for i in range(1, runs + 1):
        ws = base / f"probe-{i:02d}"
        if ws.exists():
            shutil.rmtree(ws)  # fresh instance, always
        if seed_dir is not None:
            shutil.copytree(seed_dir, ws)
        board = Orchestrator(m, ws, verify_mode=verify_mode, verbose=verbose).run()
        results.append({
            "run": i,
            "ended": board.ended,
            "cycles": board.cycle,
            "eaten": len(board.eaten),
            "total": len(m.dots),
            "usd_spent": round(board.usd_spent, 4),
        })

    greens = sum(1 for r in results if r["ended"] == "all_green")
    required = math.ceil(PASS_RATIO * runs)
    lo, hi = wilson(greens, runs)
    green_cycles = sorted(r["cycles"] for r in results if r["ended"] == "all_green")
    stats = {
        "map": m.name,
        "version": m.version,
        "traveler": {"driver": m.traveler.driver, "model": m.traveler.model},
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "runs": runs,
        "all_green": greens,
        "required": required,
        "certified": greens >= required,
        "pass_rate": round(greens / runs, 4) if runs else 0.0,
        "wilson_95": [round(lo, 4), round(hi, 4)],
        "cycles_to_green_median": (green_cycles[len(green_cycles) // 2]
                                   if green_cycles else None),
        "results": results,
    }
    return stats


def write_artifact(m: Map, stats: dict[str, Any]) -> Path:
    """Persist probe stats into the map repo's certification/ directory."""
    assert m.root is not None
    cert_dir = m.root / "certification"
    cert_dir.mkdir(exist_ok=True)
    out = cert_dir / "probe_stats.json"
    out.write_text(json.dumps(stats, indent=2) + "\n")
    return out
