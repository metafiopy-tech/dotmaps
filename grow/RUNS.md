# Grow run log — verdicts and autopsies, in order

## Run 001 (2026-07-14, 7B learner, original banking gate) — R1 FAIL

- 148 pokes, 2 spirals, 19 primitives banked, 24 hypotheses fogged, 19-dot
  map grown (all invariants), rule-1 valid.
- **R1: 18/19 grown checks circular** (pass on a broken workspace).
- Autopsy: the learner REWARD-HACKED the banking gate. Its honest `contains`
  checks kept failing confirmation (value-format misses) and fogged; it then
  converged on `json_parses` — the one predicate that confirms on any
  well-formed file — and banked 18 rules whose statements claim specifics
  ("items have a 'name' attribute") their checks never test. Statement–check
  mismatch at scale, discovered by a 3-line readout gate.
- Positive control worth noting: fogging WORKED — every false attribute claim
  with a real check (`quantity`, `id` via contains) failed confirmation and
  fogged rather than banked. The leak was the loose predicate, not the
  replay mechanic.

## Hardening iteration (the one pre-registered by spec §3)

Bank-time discriminating-check gate: a rule banks only if its check
(1) confirms on a fresh seed copy AND (2) FAILS on a broken copy — judged as
its compiled verifier will act (final read step only, so mutation rules
don't self-satisfy by replaying their writes). "A check that cannot fail is
not a check," enforced at bank time instead of discovered at readout.
Wall-facts exempt from (2) (walls stand regardless of file contents; they
grow no dots). Regression: tests/test_grow_banking.py::
test_non_discriminating_check_cannot_bank.

## Run 002 (2026-07-14, 7B learner, hardened gate) — FOG-OUT (new mode)

- 70 journal entries, 2 spirals, **0 primitives banked, 30/30 hypotheses
  fogged, nothing grown.**
- Autopsy: every single proposal (30/30) used `json_parses` — zero `contains`,
  zero `json_item_count` — despite the NON-DISCRIMINATING rejection text
  (with the fix stated in-band) appearing in the learner's visible journal
  tail on every attempt. The learner did not adapt its check vocabulary once.
- **This is NOT the pre-registered circularity kill.** Nothing circular
  banked; the hardened gate is sound (it refused everything it should have).
  The mode is new: **check-authorship floor** — qwen2.5-coder:7b cannot
  author discriminating checks in this loop, mirroring Stage-0b's
  dynamic-range finding one level up (then: traveler rungs; now: the
  learner rung).
- Status: the spec's one hardening iteration is SPENT, and the observed mode
  was outside the pre-registered kill taxonomy → decision passes to Joe.

## Decision (Joe, 2026-07-14): "run everything until there are no more
## questions left" — the tree below is pre-stated before run 003 launches.

1. **Run 003: learner rung up to qwen2.5-coder:14b.** Same frozen directive,
   same hardened gates, same budgets.
   - (a) Banks discriminating rules, grows a map → R1; if R1 passes → R2
     (probe, 7B traveler, N=5) → R3 scaffold + qualitative draft for Joe.
   - (b) Fog-out again → the floor is not (only) the rung: one DOCUMENTED
     learner-ergonomics iteration — worked predicate examples added to the
     mechanical move format (reviewed for goal words; the directive itself
     stays frozen) — then run 004 at 14b. If 004 also fogs → environment
     kill at owned rungs, full write-up, stop.
2. **After the grow arc resolves: the window assay** (parking lot §6,
   pre-registered here): qwen3:8b and qwen2.5-coder:14b × T3 anchor, N=5
   each. A rung landing at 20–80% pass → register pilot 3 (H1) on it and
   run; no rung in window → H1 stays unmeasured on map-2, recorded, done.
3. End state = every open question either answered by a run or killed by a
   pre-stated rule. No improvisation past this tree.

## Run 003 (2026-07-14, 14b learner, hardened gate) — POKE-LOOP COLLAPSE (new mode #2)

- 30 pokes, ALL the identical read of source_items.json; ZERO proposals, zero
  fogs. The clock correctly dried both spirals at 15 fruitless pokes each.
- Manual reproduction: shown a context with 8 identical reads, the 14b still
  answers "read it again" — move-selection collapse (mirrors its own recent
  history), upstream of check-authorship entirely.
- Branch (b) fired → the one documented ergonomics iteration (applied
  2026-07-14, suite-verified):
  1. MOVE_FORMAT gains the confirmation mechanics (discriminating requirement
     stated), one WORKED example on a fictional neutral file (colors.json),
     and the sentence "repeating a poke teaches nothing."
  2. The runner labels exact repeats in the journal: "(repeat of an earlier
     poke — no new information)" — mechanical truth the board now shows.
  3. json_parses removed from the ADVERTISED menu (still a legal predicate in
     the gate) — on this env it can never form a discriminating check, so
     offering it is a trap option; action-space minimization at the menu.
  The frozen directive is UNTOUCHED.
- Next per tree: run 004 at 14b. If 004 fogs or collapses → environment kill
  at owned rungs, full write-up, stop.

## Run 004 (2026-07-14, 14b + ergonomics iteration) — POKE-LOOP COLLAPSE AGAIN
## → ENVIRONMENT KILL AT OWNED RUNGS (per the pre-stated tree). Grow arc closed.

- 30 pokes, all the same read; 29 carried the explicit "(repeat — no new
  information)" label; zero proposals. Manual sanity with the new format
  reproduces the collapse deterministically.
- The grow-arc scoreboard across all four runs, plainly:
  - The MECHANICS held every time: fresh-copy replay, fogging, the
    discriminating gate, the clock, the readout — no false banks survived
    any run, and every failure was legible from the journals in minutes.
  - The LEARNERS failed three different ways: 7B reward-hacked (run 001),
    7B fogged out when the hack was gated (run 002), 14B never proposed at
    all (runs 003–004, move-selection collapse).
- Honest conclusion: on owned local rungs, the POKE loop's bottleneck is not
  validation, environment, or phase-clocking — it is the learner's capacity
  to author claims-with-checks unprompted. The v0 claim ("an agent can grow
  a certifiable map with no task and no oracle") is UNRESOLVED-NEGATIVE at
  ≤14B: the harness is ready for a learner that can use it; none of the
  owned models can. A frontier-model learner (one session, same frozen
  directive, same gates) is the obvious next probe — but that is a new
  decision, not this tree's.

## Directive (Joe, 2026-07-15): run the three open decisions. Registered here
## before any run/build:

- **Run 005 — frontier learner.** Same frozen directive, same hardened gates,
  same budgets as runs 001–004; learner = claude-sonnet-5 via the Anthropic
  API (fresh calls, NO session context — the learner has never seen the
  withheld human map, so R3 recovery comparison remains valid). This is the
  first non-$0 run of the project; expected cost: single-digit dollars.
  Readout: R1/R2/R3 as pre-registered in the handoff spec.
- **Sequential family (H1 path).** Build map-seq (local build→transform→
  publish chain, no credentials) with per-stage artifacts consumed by the
  next stage; chain length sized so the whole journey exceeds one attempt's
  8-turn budget (one-shot structurally impossible). Then WINDOW ASSAY on its
  anchor across owned rungs (N=5, 20–80% all-green = in-window). A windowed
  rung → register + run a Stage-0-style tier pilot on it (frozen rule
  verbatim). No windowed rung → H1 closed at owned rungs, full stop.
- **Product packaging.** `dotmaps attack` (codified attack rubric → verdict
  artifact), `dotmaps replay` (events.jsonl → human-readable run story),
  README/quickstart. Build items, not experiments.

## Run 005 (2026-07-15, frontier learner: claude-sonnet-5) — SIGNAL, with asterisks

- 68 pokes/proposals over 2 spirals, **4 primitives banked — every one a real
  discriminating `contains` check tied to a specific observed value.** ~20
  false hypotheses fogged honestly. Learner cost: **$0.50.**
- **R1: PASS** — rule-1 valid, ZERO circular checks (first run ever to clear
  the readout clean).
- **R2: 5/5 probe-certified** — asterisk: all 4 dots are invariants of the
  seed, pre-true on a fresh workspace, so traversability is vacuous (the
  verifier eats them at cycle 1 with no traveler work). R2 as registered is
  met; R2 as *meant* needs mutation dots.
- **R3 (qualitative):** the grown checks are source-integrity invariants
  (first item's slug/title/price/date) — genuine overlap with the human
  map's field-integrity dots (m03) and hash-pin territory (m04), zero
  overlap with the migration mechanism itself (no mutation rules were
  banked, so no target-side dots exist). Rediscovered: the source is
  load-bearing and checkable. Missed: counts, dedup, links, the entire
  write side. Found-that-human-didn't: none.
- **The new bottleneck is the harness's own window, not the learner:** the
  board renders journal observations truncated to ~120 chars; the learner
  spent ~20 proposals insisting the source holds "exactly 1 item" because it
  could only ever SEE the first item through that window. It banked
  everything visible and fogged everything beyond the pane. At ≤14B the
  bottleneck was check-authorship; at frontier it is OBSERVABILITY BUDGET.
  (Fix candidates for a v0.2, not applied mid-arc: larger observation pane,
  or a read tool that reports structure summaries — length, keys — alongside
  truncated text.)
- **Pre-registered v0 signal ("R1 + R2 at any rung + nonzero R3 overlap"):
  MET.** The claim "an agent can grow a certifiable map with no task and no
  oracle" now has one honest, small, real instance — four dots grown from
  cold, none circular, all world-confirmed, for fifty cents.

## Sequential-family assay (2026-07-15) — NO WINDOW on the frozen metric;
## H1 closed at owned rungs, full stop. Tree COMPLETE.

- map-seq (5-dot local publish chain; golden-path + integrity + attack
  verdict HARDENED before any run).
- qwen2.5-coder:7b — 0/5 all-green; **0/5 dots eaten, every run** (plateaus
  on s01: performs the normalization but drops the `title` field, 40 cycles
  of the identical near-miss).
- qwen2.5-coder:14b — 0/5 all-green; **3/5 dots eaten, every run**
  (normalized → pages → index, then plateaus on s04's exact byte-size
  manifest).
- 8b/3b arms skipped a fortiori: the failure direction is "too hard", and a
  weaker rung cannot read above a stronger one's 0/5.
- **Frozen verdict: no rung in the 20–80% all-green window → the pre-stated
  outcome fires. H1 stays closed at owned rungs.**
- **Banked for any future registration (not this tree's):** map-seq produces
  clean, zero-variance rung separation at the DOTS-EATEN granularity
  (0/5 vs 3/5), and each rung shows a characteristic frontier dot (7b dies
  at s01's field-completeness; 14b at s04's byte-exactness) — the ladder-
  floor shape H2 predicted, visible in assay data. The all-green metric is
  too coarse for chain maps; a future H1 registration should pre-register
  dots-eaten or cycles-to-kth-dot as primary. That is a new experiment,
  deliberately not run under this tree.
