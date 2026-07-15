# Stage-0 pilot — interim field notes (written DURING the runs)

Recorded before results are complete, so post-hoc rationalization can be
checked against what was believed mid-flight. The decision rule stays the
pre-registered one in `pilot_analysis.py` — nothing here amends it.

> **Post-pilot revision of finding 1:** v2 (delete-free action space) ran T4
> clean — 5/5 all-green, uniform 3 cycles, no placeholder stall. The v1 T4
> stall was therefore the move-mode delete loop (finding 3), NOT placeholder
> anchoring; the two were confounded in v1. The *design* caution below stands
> (enrichment tiers need validation before carrying the "best" label), but the
> observed mechanism was the delete loop. Final verdict in `pilot_report.md`.

## Interim finding 1 — the T4 "placeholder trap" (observed run 1, cycle-by-cycle)

T4 (densified) probe-01 went **budget_exhausted at cycle 30**. Event-log
autopsy:

- cycle 2: `t00` eaten — the traveler satisfied the new easy entry rung
  ("target exists and parses as a non-empty JSON array") by writing
  `[{"item": "example"}]`, a placeholder. `m05` (links) also ate vacuously —
  a one-junk-item target has no internal links.
- cycles 3–30: `m01` ("counts match") attempted **29 times, never eaten**.
  No regressions; the run died of budget.

The base map (T3) never exhibits this: its first dot is m01 itself, whose
evidence ("source=5 target=1") pushes the model to copy the full source in
attempt 1 — observed 2-cycle all-greens in certification.

**Methodological implication (independent of how the pilot lands):** the tier
ladder's "T4 = best by construction" is only sound for *degradation* operators
(removing/weakening a road cannot improve it). *Enrichment* is not
automatically improvement — a badly designed intermediate rung can create an
attractor state (cheap local satisfaction of an early dot) that strands a weak
traveler. Corpus design consequence: densified variants need their own
validation pass (e.g., a pre-probe showing the densified map is at least as
traversable as its base) before they may carry the "best" label in H1's
correlation. Alternative honest reading: the instrument is working — it just
measured OUR densification as a worse road than the base, and the planted
label, not the probe, is what's wrong for this variant.

**Observability gap surfaced:** the scoreboard records per-dot attempt COUNTS
but nothing about WHY attempts fail (the traveler's turns/tool outcomes are
discarded by the orchestrator). Diagnosing the 29-attempt stall required
inferring from workspace state. This is exactly experiment-spec item 5
(scoreboard completeness) — gated post-Stage-0, noted here as confirmed-needed.

## Interim finding 3 — the move-mode delete (pilot v1 invalidated; harness hardened)

Pilot v1's anchor broke: **T3 — the previously certified base map — went 0/5**,
target file never present after 30 attempts/run. Live tracing found the
mechanism, an interaction of three things, each individually reasonable:

1. **Semantic prior leakage.** After correctly writing target_items.json, the
   model treats "migration" as MOVE and tries to delete the source. No dot
   asked for this; the prior came from the word.
2. **Blocked-action displacement.** The protected-paths wall correctly blocks
   the source delete — so the model, committed to deleting *something*,
   deletes its own deliverable instead. A wall redirected the agent to a
   worse in-scope action.
3. **Turn-budget parity.** Each attempt is up to 8 tool turns in a
   write→verify→delete loop; whether the attempt ends with the target present
   depends on where the turn budget slices the loop. Same map, same model,
   same temperature: certified 5/5 one day, 0/5 the next — trajectory chaos,
   not road quality.

**Harness fix (shipped):** tool-level walls. `mcp_required` now accepts
single-tool grants (`filesystem.write_file`) alongside whole servers; map 2
v0.1.1 grants only read+write+fetch — `filesystem.delete` is ABSENT from the
action space (rule 3 at tool grain: illegal actions absent, not discouraged).
Dry-run wall parity covered; suite 53 passed. Sanity run: T3 all-green again.

**Also shipped (observability, was finding-blocking twice):** the traveler's
per-attempt tool-call journal is now recorded on `dot_attempted` events —
additive field, event vocabulary unchanged.

**Experiment consequences:** all pilot-v1 runs discarded (instrument fault,
not samples). T4's stall must be re-read after the fix: the "placeholder trap"
(finding 1) and the delete loop were confounded in v1. Pilot v2 runs on the
0.1.1 base with the same pre-registered decision rule. If the product story
needs one line: the Stage-0 ambush caught a harness defect that certification
had sampled past — 5 greens said "certified" where the 6th-through-10th
trajectories said "coin flip". That is precisely why probe N and Wilson bounds
exist, and why the instrument needs variance reporting, not just pass rate.

## Interim finding 2 — pilot ops

- T4 runs cost ~50 min each when they exhaust budget (30 cycles × ollama
  latency). "Budget exhaustion on a bad road is signal, not noise" (spec §2) —
  but it is *expensive* signal on local hardware; the full sweep's tranche
  planning must budget wall-time by tier, worst-case.
- T3's first probe crashed from an operator error on my side (workspace-base
  deleted mid-run); the tranche loop self-healed and T3 re-queues last. No
  data corruption (per-variant artifacts write atomically at variant end).
