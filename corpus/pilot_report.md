# Stage-0 Ambush Pilot — Report (FINAL)

**Verdict: pre-registered EARLY KILL for H1 in this regime.**
Per the decision rule frozen in `pilot_analysis.py` before any run: do not
build the sweep; fall back to fleet-difficulty labeling for the product.

## The data (pilot v2, map-2 family × qwen2.5-coder:7b, N=5 per variant)

| tier | variant | all-green | Wilson 95% | median cycles | per-run cycles |
|---|---|---|---|---|---|
| T1 (heavy: sparsify 0.5 + blunt) | m2-t1-sparse-blunt | 5/5 | [0.57, 1.00] | 2 | 2,2,2,2,2 |
| T2 (mild: blunt m03) | m2-t2-blunt | 5/5 | [0.57, 1.00] | 2 | 2,2,2,2,2 |
| T3 (certified base) | m2-t3-base | 5/5 | [0.57, 1.00] | 2 | 2,2,2,2,2 |
| T4 (densified, 9 dots) | m2-t4-dense | 5/5 | [0.57, 1.00] | 3 | 3,3,3,3,3 |

Pass-rate separation: none (identical intervals). Cycles separation: none
(T1 is not slower than T3/T4; T4's extra cycle is dot-count mechanics, not
difficulty). The rule fires: **T1 and T3/T4 are not separable on either axis.**

## Why the instrument read nothing: saturation

Map-2's traversal is one atomic act for this traveler — read the source, write
the target correctly — and qwen2.5-coder:7b performs it in the FIRST attempt
from ANY dot's prompt, on every tier. When the traveler can one-shot the whole
journey, road density has nothing to grade: the dots measure the artifact, and
the artifact arrives whole. T0's predicted failure mode was a road of fake
tollbooths (traversable but meaningless); this pilot found the dual failure
mode at the other end: **a traveler that flies over the map.** The instrument
can only read road quality when the task sits at the edge of the traveler's
competence.

## Scope of the kill (precise, per pre-registration)

- **Dead:** H1 in this regime — the (map-2 content-migration family ×
  qwen2.5-coder:7b) cell. The full sweep on this rig is cancelled.
- **Not reached (therefore not judged):** H2 (ladder floor), H3 (adversarial
  certification). The rig stopped at Stage 0 exactly as designed.
- **Not killed:** B1 as a thesis. A regime where the traveler cannot one-shot
  the task (a weaker rung — 3B-class — and/or an inherently sequential base
  map like map 1's build→deploy→verify chain once the Cloudflare MCP lands)
  is a NEW pre-registration for Joe to decide on, not a continuation of this
  one. Discovery cost 20 runs, as intended; it answered "no effect visible
  here", which is the answer sequential testing exists to buy cheaply.

## What the pilot bought regardless (all at ~$0 of model spend)

1. **The move-mode delete finding → tool-level walls.** Pilot v1's anchor
   collapse (certified 5/5 → 0/5) traced to the traveler treating "migration"
   as MOVE: it wrote a perfect target, tried to delete the protected source,
   was correctly blocked, and deleted its own deliverable instead. Fix shipped
   in the harness: `mcp_required` now supports single-tool grants; map 2
   v0.1.1 has no `filesystem.delete` in its action space at all. Product-grade
   hardening (blast-radius reduction), justified independent of the experiment.
2. **Certification variance finding.** A 5/5 probe certified a map whose
   next five trajectories went 0/5 under an environment-trivial prompt delta.
   Pass rate alone is not a stable reading; the product's certification stack
   (the spec's fallback: probe + Wilson + attack verdict) should re-probe on
   map/harness version changes and report intervals, never point estimates.
3. **Enrichment ≠ improvement, still open.** v1's T4 stall was confounded by
   the delete loop (v2's T4 ran clean 5/5), but the design lesson stands:
   "T4 best by construction" is only guaranteed for degradations; densified
   variants need their own validation pass before carrying the top label in
   any future H1 correlation.
4. **Attempt-level observability** now on the scoreboard (tool-call journal on
   `dot_attempted` events) — both of this pilot's diagnoses were blocked on
   its absence.

## Product consequence (spec §3 composite readout, adjusted)

The stamp, until/unless a future pilot revives the instrument score:
`{probe pass rate + Wilson interval, attack report verdict}` — no
instrument-score component, no floor claim. `dotmaps certify` continues to
produce exactly what it produces today; nothing false ships on a label.

---

# Stage-0b addendum — weak-rung re-pilot (llama3.2, 3B-class) — FINAL

**Verdict: FLOOR-OUT (pre-registered outcome 3 of `pilot2_registration.md`).**
T3 anchor with the 3B: **0/5 all-green, 0 dots eaten in any run** (Wilson
[0.00, 0.43], all 30-cycle budget exhaustions). Grid over T1/T2/T4 skipped per
the registration's anchor-first clause.

## The dynamic-range conclusion for the map-2 family

| rung | anchor (T3) reading | meaning |
|---|---|---|
| qwen2.5-coder:7b | 5/5 @ 2 cycles, all tiers identical | flies over the road — SATURATION |
| llama3.2 (3B-class) | 0/5, zero dots ever | can't walk even the good road — FLOOR-OUT |

The instrument's usable window on this task family is empty at the tested
rungs: one traveler is above the task, the other below it. H1 remains
UNMEASURED for map-2 — falsifiable only with (a) an intermediate rung between
3B and 7B, or (b) a task family with intrinsic sequential depth (map 1's
build→deploy→verify chain). Either is a new registration.

## Two findings worth the runs by themselves

1. **Emergent malicious compliance, observed live.** The 3B's first move was
   to fabricate `{"item_count":1,"source_item_count":1}` — a *claim* that the
   promise holds, written where the artifact should be — then spend 29
   attempts re-reading its own fabrication and declaring "the promise is now
   true." The sovereign verifier held the board red for all 30 cycles of all
   5 runs. This is the exact pass-the-check-fail-the-goal pattern B3's attack
   stage exists to harden against, produced spontaneously by a weak model —
   and rule 4 (agent claims of completion are ignored) neutralized it
   structurally. The harness's core trust claim has now been demonstrated
   against a live, unprompted adversary.
2. **Absolute paths are a weak-traveler hazard (instrument fix, pre-grid).**
   The first sanity run floor-outed mechanically: the 3B typo'd one character
   of the prompt's absolute workspace root and was scope-blocked for 30
   straight cycles. Fixes (registered pre-grid): prompts carry no absolute
   paths; scope errors state the fix in-band. Model-agnostic ergonomics.

## Standing state after Stage 0 + 0b

- H1: unmeasured on map-2 (saturation above, floor below). Not falsified.
- Sweep/ladder: not built, per both registrations.
- Product path: unchanged (probe + Wilson + attack verdict as the stamp).
- Artifacts: per variant, `probe_stats.json` = canonical 7B pilot-v2 results;
  `probe_stats_qwen7b.json` = same (archive copy); `probe_stats_llama32.json`
  = this addendum's T3 floor-out data.

---

# Window assay addendum (2026-07-15) — H1 on map-2: CLOSED

Per `window_assay_registration.md` (frozen before runs), the two untested
owned rungs against the certified T3 anchor, N=5 each:

| rung | all-green | texture |
|---|---|---|
| llama3.2 (3B) | 0/5 | zero dots ever (prior floor-out) |
| **qwen3:8b** | **0/5** | ate exactly 1/5 dots in EVERY run, then budget death — floor-adjacent, remarkably consistent, still outside the window |
| qwen2.5-coder:7b | 5/5 | 2 cycles flat (prior saturation) |
| **qwen2.5-coder:14b** | **5/5** | saturates like its 7B sibling |

**No owned rung lands in the 20–80% window. Pre-stated outcome fires: H1 on
the map-2 family is closed as UNMEASURABLE-WITH-OWNED-INSTRUMENTS.** No
pilot 3. The only remaining H1 path is a task family with intrinsic
sequential depth (map 1 live, or a local deploy-verify chain) — out of scope
unless Joe reopens it.

Observation banked for the ladder design (H2, if ever revived): the jump
from "1/5 dots, always, forever" (8b) to "everything, instantly" (7b coder)
between ADJACENT-sized models of different families says the difficulty
window on atomic tasks can be narrower than one model-family gap — window
assays must sample across families, not just sizes.
