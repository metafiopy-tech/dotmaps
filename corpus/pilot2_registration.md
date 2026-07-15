# Stage-0b registration — weak-rung re-pilot (FROZEN BEFORE RUNS)

**Registered:** 2026-07-13, before any run of this pilot. User-approved.

## Regime change, and only that

Same corpus (the four map-2 variants, v0.1.1 base), same N=5, same probe
machinery, same decision rule VERBATIM as Stage-0. One change: the instrument
rung drops from qwen2.5-coder:7b to **llama3.2 (3B-class)** — chosen because
Stage-0 established the 7B saturates this task family (one-shots the whole
migration), so H1 went unmeasured rather than falsified. A weaker traveler may
sit inside the instrument's dynamic range where road quality can register.

## Pre-registered outcomes (three, not two)

1. **SEPARATION** — T1 clearly worse than T3/T4 (Wilson intervals disjoint OR
   T1 median cycles-to-green strictly greater than both). The instrument has a
   pulse at this rung → proceed per the original spec §5 (sweep planning
   resumes, with the 3B as instrument rung).
2. **SATURATION (again)** — all tiers ≥4/5 with indistinguishable cycles. The
   3B also flies over map-2 → the task family is the problem, not the rung;
   any revival needs an inherently sequential base map (map 1). KILL for the
   map-2 family.
3. **FLOOR-OUT** — T3 (the certified base, the anchor) fails to reach ≥3/5.
   The 3B is below the task's floor; probe reads nothing because the traveler
   can't traverse even a good road. KILL for this rung; the dynamic-range
   window on this family is empty (7B above, 3B below) unless a mid rung
   exists.

Decision math identical to `pilot_analysis.py` (Wilson overlap AND
cycles-to-green), with outcome 3 checked first (anchor validity precedes
separation — Stage-0's hard-won lesson).

## Ops notes (pre-declared)

- Stage-0 (7B) artifacts are archived as `probe_stats_qwen7b.json` per variant
  before any new run; this pilot's artifacts land as
  `probe_stats_llama32.json`. Nothing overwrites the early-kill evidence.
- One sanity run of T3 with the 3B precedes the full grid (anchor-first — if
  it floor-outs in run 1, the full grid may still run to N=5 on T3 only to
  confirm outcome 3 cheaply, skipping T1/T2/T4).
- Same budget inheritance (max_cycles 30), same disk guard, detached runner,
  monitor. Wall-time unknown at this rung; 3B generation is faster but may
  burn more cycles.

## Amendment (pre-grid, after the declared sanity run — before any grid run)

The sanity run floor-outed for a MECHANICAL reason, not capability: the 3B
echoed the prompt's absolute workspace root with a one-character typo and was
scope-blocked on all 30 cycles (attempt journals show every call BLOCKED on a
misspelled path). Two instrument-ergonomics fixes shipped before the grid,
both model-agnostic: (1) the per-dot prompt no longer contains any absolute
path — paths are declared relative; (2) ScopeViolation errors now state the
fix in-band. The decision rule and outcomes above are unchanged. Sanity re-run
follows; the grid launches only after it.
