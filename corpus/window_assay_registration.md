# Window assay registration (parking lot §6, activated by Joe's 2026-07-14
# "run everything" directive) — FROZEN BEFORE RUNS

## Question

Does any owned rung land inside the map-2 instrument window (anchor pass
rate ~20–80%), making H1 falsifiable on this family at all?

## Protocol

- Rungs: qwen3:8b, qwen2.5-coder:14b (the two untested owned rungs between/
  around the known floor at llama3.2-3B and the known ceiling at
  qwen2.5-coder:7b... note 7b SATURATED at 100%, 3b floored at 0%; 8b and
  14b are expected ≥7b's reading, so the realistic hope is qwen3:8b's
  different family behaving differently. Low prior, cheap check — run it
  anyway, that is what assays are for.)
- Anchor: m2-t3-base (the certified base), N=5 fresh probe runs per rung,
  standard budgets, existing `dotmaps probe --model` machinery.
- Readout per rung: all-green count /5 + Wilson 95%.

## Pre-stated outcomes

- Some rung lands 1/5–4/5 all-green (inclusive) → IN WINDOW → register
  pilot 3 (4 tiers × N=5 at that rung, same decision rule as Stage-0,
  verbatim) and run it.
- Every rung at 0/5 or 5/5 → window empty across ALL owned rungs → H1 on
  map-2 is closed as UNMEASURABLE-WITH-OWNED-INSTRUMENTS; recorded in
  pilot_report.md; the only H1 path left is a sequential task family (map 1
  or local-deploy variant), which is out of scope for this directive unless
  Joe reopens it.
