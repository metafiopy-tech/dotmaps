#!/usr/bin/env python3
"""Stage-0 ambush-pilot analysis (experiment spec §5).

Reads each pilot variant's certification/probe_stats.json and applies the
PRE-REGISTERED decision rule, verbatim:

  "If T1 and T3/T4 are not clearly separated (Wilson intervals overlapping AND
   cycles-to-green indistinguishable), H1 is dead-on-arrival in this regime —
   STOP, do not build the sweep. If the extremes separate cleanly, the
   instrument has a pulse: proceed."

Run:  python3 pilot_analysis.py [pilot_dir]
"""
import json
import sys
from pathlib import Path

PILOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "pilot")
VARIANTS = ["m2-t1-sparse-blunt", "m2-t2-blunt", "m2-t3-base", "m2-t4-dense"]


def load(name):
    p = PILOT / name / "certification" / "probe_stats.json"
    return json.loads(p.read_text()) if p.exists() else None


def main():
    rows = []
    for name in VARIANTS:
        v = json.loads((PILOT / name / "variant.json").read_text())
        s = load(name)
        rows.append((v["tier"], name, s))

    print(f"{'tier':<5} {'variant':<22} {'green':>7} {'Wilson 95%':>16} {'med cycles':>11} {'per-run cycles'}")
    for tier, name, s in sorted(rows):
        if s is None:
            print(f"{tier:<5} {name:<22} {'PENDING':>7}")
            continue
        cyc = [r["cycles"] for r in s["results"]]
        med = s.get("cycles_to_green_median")
        print(f"{tier:<5} {name:<22} {s['all_green']}/{s['runs']:>4} "
              f"[{s['wilson_95'][0]:.2f}, {s['wilson_95'][1]:.2f}]"
              f"{str(med):>9}   {cyc}")

    t1 = next(s for t, n, s in rows if t == "T1")
    t3 = next(s for t, n, s in rows if t == "T3")
    t4 = next(s for t, n, s in rows if t == "T4")
    if not all((t1, t3, t4)):
        print("\nincomplete pilot — decision deferred until all probes land")
        return 2

    # -- the pre-registered rule, mechanically ------------------------------ #
    best_lo = max(t3["wilson_95"][0], t4["wilson_95"][0])
    rate_separated = t1["wilson_95"][1] < best_lo

    def med(s):
        m = s.get("cycles_to_green_median")
        return m if m is not None else float("inf")  # no greens = worst

    cycles_separated = med(t1) > max(med(t3), med(t4))

    print(f"\npass-rate separation:  T1 Wilson upper {t1['wilson_95'][1]:.2f} "
          f"vs best(T3,T4) lower {best_lo:.2f} -> "
          f"{'SEPARATED' if rate_separated else 'overlapping'}")
    print(f"cycles separation:     T1 median {med(t1)} vs best(T3,T4) "
          f"{max(med(t3), med(t4))} -> "
          f"{'SEPARATED' if cycles_separated else 'indistinguishable'}")

    if rate_separated or cycles_separated:
        print("\nDECISION: the extremes separate — the instrument has a pulse. "
              "PROCEED to the full sweep (its job: resolve middle tiers + ρ).")
        return 0
    print("\nDECISION: T1 vs T3/T4 not separable on either axis — pre-registered "
          "EARLY KILL. Do not build the sweep; fall back to fleet-difficulty "
          "labeling for the product, and report this plainly.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
