#!/usr/bin/env python3
"""Reconstruct probe_stats.json from surviving per-run event logs.

Needed once: the Stage-0 pilot's first tranche died of ENOSPC after T4's runs
had executed but before write_artifact ran. The scoreboard's event logs are the
single source of truth (harness rule 2), so per-run outcomes are fully
recoverable by replay. Crashed runs (no run_ended event) are EXCLUDED as
infrastructure failures — they are not traveler samples.

Usage: python3 reconstruct_stats.py <variant_map_dir> <workspace_base> [extra_base ...]
Writes <variant_map_dir>/certification/probe_stats.json (marked reconstructed).
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "dotmaps"))
from dotmaps.certify import PASS_RATIO, wilson  # noqa: E402


def replay(log: Path):
    events = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    ended = next((e for e in events if e["event"] == "run_ended"), None)
    if ended is None:
        return None  # crashed — not a sample
    eaten = set()
    for e in events:
        if e["event"] == "dot_eaten":
            eaten.add(e["dot"])
        elif e["event"] == "dot_regressed":
            eaten.discard(e["dot"])
    return {
        "ended": ended["reason"],
        "cycles": max((e.get("cycle", 0) for e in events), default=0),
        "eaten": len(eaten),
    }


def main():
    variant_dir = Path(sys.argv[1]).resolve()
    bases = [Path(p).resolve() for p in sys.argv[2:]]
    manifest = json.loads((variant_dir / "variant.json").read_text())

    results, excluded = [], 0
    for base in bases:
        for ws in sorted(base.glob("probe-*")):
            log = ws / ".dotmaps" / "events.jsonl"
            if not log.exists():
                continue
            r = replay(log)
            if r is None:
                excluded += 1
                continue
            r["run"] = len(results) + 1
            r["total"] = manifest["dot_count"]
            r["usd_spent"] = 0.0
            results.append(r)

    runs = len(results)
    greens = sum(1 for r in results if r["ended"] == "all_green")
    lo, hi = wilson(greens, runs)
    green_cycles = sorted(r["cycles"] for r in results if r["ended"] == "all_green")
    stats = {
        "map": manifest["name"],
        "version": "0.1.0",
        "traveler": {"driver": "ollama", "model": "qwen2.5-coder:7b"},
        "reconstructed": True,
        "reconstruction_note": (
            f"artifact rebuilt by replaying per-run event logs after an ENOSPC "
            f"crash; {excluded} crashed run(s) excluded as infrastructure failures"
        ),
        "runs": runs,
        "all_green": greens,
        "required": math.ceil(PASS_RATIO * runs),
        "certified": runs > 0 and greens >= math.ceil(PASS_RATIO * runs),
        "pass_rate": round(greens / runs, 4) if runs else 0.0,
        "wilson_95": [round(lo, 4), round(hi, 4)],
        "cycles_to_green_median": (green_cycles[len(green_cycles) // 2]
                                   if green_cycles else None),
        "results": results,
    }
    out = variant_dir / "certification"
    out.mkdir(exist_ok=True)
    (out / "probe_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(f"{manifest['name']}: {greens}/{runs} all-green "
          f"(excluded {excluded} crashed), wilson {stats['wilson_95']} "
          f"-> {out / 'probe_stats.json'}")


if __name__ == "__main__":
    main()
