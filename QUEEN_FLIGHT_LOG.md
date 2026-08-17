---
tags: [queen, flight-log, v0]
status: acceptance test PASSED — every gate green, every gate a separate commit
date: 2026-08-12
---

# QUEEN_FLIGHT_LOG — v0's first flight

One paragraph: Queen v0 shipped in seven gates (Q1–Q7, Q4b inserted per
spec) on branch `queen-v0`, each a separate commit with its own done-test.
She is wiring, not invention — a dispatch organ over already-proven parts
(bank/route.py, bank/certify.py, grow/*). The acceptance test passes:
`dotmaps queen pilot` routes 4/4 covered at \$0 with zero model calls,
`dotmaps sleep` completes with one SLEEP trip, `dotmaps surface` says
"Nothing needs you." Q7 (optional) came back POSITIVE, not parked: the
subscription learner's smoke failure had a real root cause and a real
fix, confirmed by one live growth run.

## What was built, gate by gate

### Q1 — Trip bus + Fio surface (`49674db`)
`queen/trips.py`: append-only JSONL log (`runs/queen/trips.jsonl`),
hash-chained so a rewrite is mechanically detectable — not trusted on
say-so. Eight typed events, fixed: CERTIFIED, CONVICTED, BLOCKED,
BUDGET_EXHAUSTED, ORACLE_FAIL, SHELVED, ESCALATE, SLEEP.
`queen/surface.py` + `dotmaps surface`: one card, "Nothing needs you."
unless an ESCALATE is open, which renders as a decision (question +
numbered options). `dotmaps surface --resolve <id> --choice <n>` answers
one.
**Done-test (12 tests):** synthetic ESCALATE flips the surface; resolve
restores calm; re-raise after resolve reopens the same id; a tampered or
deleted trip-log line breaks the hash chain and `verify_integrity()`
catches it.

### Q2 — The dispatcher (`0af3051`)
`queen/dispatch.py` + `dotmaps queen <preset|map.yaml>`. Wraps
`bank/route.py` UNMODIFIED: READ a compiled map → ROUTE (covered dots
execute certified skills silently at \$0; frontier listed honestly) →
STAFF a full dispatch PLAN per frontier predicate (inherited-primitive
count, a ClockConfig budget, learner slot marked "requires Q7 or
human-run" — plan only) → BUDGET (`check_budget`, wired but never called
in dry-run) → ESCALATE once a predicate SHELVES twice without becoming
covered. Presets: `pilot` (the grown pilot map, `runs/grow-005/grown-map`)
and `migration` (`maps/map-content-migration`).
**Done-test (6 tests):** pilot routes 4/4 covered / \$0 / zero model
calls, matching G3's committed result exactly; migration shows 5 frontier
each with a complete staffing plan; end-to-end pytest proves
dispatch → trips → surface (two rounds shelve every migration predicate
twice, the queen escalates all 5, resolving one restores it to calm).

### Q3 — Abort governor, backtested (`dded766`)
`queen/governor.py` — three criteria plus a counterweight: (a)
competence-flatness (typed failure categories, mechanically derived from
grow's own observation vocabulary, + a chi-null permutation-test churn
classifier: WALL/CHURN/DIRECTIONAL/INSUFFICIENT); (b) oracle-validity
(delegates to `bank/certify.oracle_gate` verbatim); (c)
objective-provenance (v0 hard assert: every objective is inherited, never
self-generated). `experiments/governor_backtest.py` scans the archived
e1b/e1c/e1d journals (33 runs, frozen, read-only) and:
- computes `PERSISTENCE_BUDGET_POKES` = the 75th percentile of
  pokes-before-first-bank across every banked hypothesis family
  (**n=1195, p75=1** — the honest result: most hypotheses confirm on the
  first attempt; forage revision is the tail case, not the median);
- reproduces the published verdicts at the grain they were actually
  graded on — refog counts (a statement fogged under more than one
  distinct rule_id within a run): **e1c shows 20 refogs** (matches
  e1c-verdict's documented in-flight-race churn), **e1d shows 0 across
  all 16 runs** (matches e1d-verdict.json verbatim: "refog=0 in ALL 16
  runs... churn ELIMINATED").

Two real bugs the backtest itself caught before landing: non-
discriminating WALL calls on n=2 same-category failure traces (7 false
positives on e1d's own banked families — fixed by `MIN_N_FOR_VERDICT=3`,
a permutation test needs room to have power) and duplicate
fog/fog-blocked events double-counting one hypothesis id as its own
refog (fixed by deduping rule_ids before grouping by statement).
**Done-test (18 tests):** synthetic WALL/CHURN/DIRECTIONAL traces;
provenance hard-assert; oracle_valid pass-through equivalence; the
backtest reproduces both published verdicts retroactively with zero
false WALLs on the clean e1d runs, and `PERSISTENCE_BUDGET_POKES` is
asserted to match the committed report's p75 exactly.

### Q4 — C3 reconsolidation hook (`150b0cc`)
`queen/reconsolidate.py` — the metabolism spec's one component with no
vault precedent. `touch()` fires on every certified-skill invocation via
route (wired into `dispatch.py`'s covered-dot loop): advances
`last_used`, increments an invocation counter, bumps FSRS-lite
`stability`, appends a usage delta. NEVER touches `method.steps` or
`check` (law 3) — self-checked by a byte-identity assertion inside
`touch()`/`reset_after_recert()` itself, not just in a test.
`due_for_recheck()` decays stability exponentially since `last_used`;
`sweep_shelf_rechecks()` fires one SHELVED trip per decayed certified
card proposing re-certification; `reset_after_recert()` restarts the
clock once a recheck confirms the skill still holds (C6 annealing).
**Done-test (13 tests):** two invocations update the clock; an injected
20×-half-life time-advance triggers exactly one SHELVED re-check on an
otherwise-fresh card; a deterministic re-cert + reset clears the due flag;
method/check bytes are hash-identical to the original across the full
touch → sweep → recert → reset sequence.

### Q4b — Gatekeeper v0 (`da39ba3`)
`queen/gatekeeper.py` — the golf-gig oracle-validity tells, inverted onto
the agent. Three tests against a mutualist's Composter ledger data, any
one failure demotes to candidate: state-change (act-rate — did
consumption measurably change a decision?), transfer (did the effect show
up outside the mutualist's own consumption loop?), parasite (is the
friction class it eats growing under its stewardship?). Hard gate:
refuses any verdict below 1 audit period.
**Done-test (6 tests):** synthetic pass ledger clears all three; three
synthetic fail ledgers each isolate one failure mode; empty ledger
refuses outright; a single period is sufficient to clear the hard gate.

### Q5 — Purple's ledger (`02dbbbf`)
`queen/purple.py` — the theory-of-Fio organ, excavated from March's
design. No separate write path: every ESCALATE resolution already IS the
record inside `trips.jsonl` (id, category-bearing raise data, choice,
seq-latency); Purple is a pure read-side ledger, wired to
`dotmaps surface --purple`. `apply_threshold()` hard-refuses below 20
events (the count stays visible in the error).
**Done-test (6 tests):** ledger accrues per category from real
raise/resolve pairs; unresolved reads as "ignored"; a "keep shelving"-
style choice reads as "deferred"; refusal enforced at 19 events, applies
cleanly at 20.

### Q6 — Sleep (`2fae8a9`)
`queen/sleep.py` + `dotmaps sleep` (cron-ready, no args, no model call).
One tick: manifest recompute (`certify_all` rerun, deterministic, \$0) →
due shelf re-checks executed (the recompute above IS the re-check;
decayed cards get their clock reset via `reset_after_recert`, C6
annealing) → dedup sweep (audit only, never rewrites — law 3) → one SLEEP
trip with a morning-readable summary.
**Done-test (5 tests):** a full run emits exactly one SLEEP trip;
back-to-back ticks at the same injected timestamp are idempotent (zero
rechecks on the second tick); a decayed card gets exactly one recheck,
recerts clean, and resets so a repeat tick finds nothing due; the dedup
sweep never rewrites method/check on any real card.

### Q7 — Subscription learner: FIXED, not parked (`3510f9c`)
Diagnosed and fixed live, timeboxed to ~1 hour. Root cause of the
original smoke failure (`claude -p` returning `result: None`,
`subtype: error_max_turns`), confirmed by direct observation: Claude
Code's DEFAULT system prompt is the full agentic-coding persona, which
reaches for a tool on turn 1 (`stop_reason: tool_use`) even with the
common tools disallowed — burning the entire `--max-turns 1` budget
before any text turn. **Fix:** `--system-prompt` REPLACES that persona
with a bare move-generator instruction ("you have no tools, reply with
ONE JSON object"). Confirmed live, subscription-billed, every call since
the fix returns `subtype: success`, `num_turns: 1`, a real parseable
move, first attempt, every attempt.

Also confirmed and worth flagging: **`ANTHROPIC_API_KEY` is present in
this session's ambient environment.** An unfiltered `claude -p` call uses
it (real metered billing, not the subscription) — this was hit once by
accident during diagnosis (~\$0.04) before the env-stripping was
double-checked; `ClaudeCodeLearner`'s existing stripping logic was
already correct and is now covered by a mocked test that asserts the key
never reaches the child process.

Ran ONE short live dispatch as the smoke, per the brief:
`dotmaps queen migration --live --driver claude-code` — real growth
against the migration preset's seed: read `migration.json`, read
`source_items.json`, proposed and **banked** a real primitive
("source_items.json contains exactly 5 items"), grew a map. Cost:
\$0.0776. Artifacts committed at `runs/queen-live/migration/`.

`queen/live.py` is the only module in the package that makes a model
call; nothing else imports it. `--driver` accepts exactly `claude-code`
— never `AnthropicLearner`, ever. `TINY_LIVE_BUDGET` (max_pokes=3) keeps
this a smoke test, not a growth campaign.
**Done (4 offline tests + one live artifact):** `_extract_move` parsing,
the system-prompt contract, API-key-stripping are unit-tested offline;
the live path itself is proven by the committed run artifacts, not
re-mocked into the deterministic suite (same convention as
`test_ollama_driver.py`).

### Also landed
- `metabolism-spec-v0_1.md` at repo root (was outside the queenchat.zip
  staging, found directly in `~/Downloads/`).
- `docs/queen.html`, `docs/queen-for-everyone.html`, `docs/memory.html`,
  `docs/memory-loop.html`, `docs/memory-graphs.html` — renamed per the
  brief (`queen-console-demo.html` → `queen.html`,
  `memory-metabolism.html` → `memory.html`; the others already matched).
  Linked from README.md next to the existing instrument demos.

## The acceptance test — result

```
$ dotmaps queen pilot
{"target": "pilot", "map": "grown-cold-seed",
 "covered": [4 dots, all passed], "frontier": [],
 "model_calls": 0, "cost_usd": 0.0}

$ dotmaps sleep
{"shelf_rechecks": 0, "shelf_recheck_skills": [], "dedup_conflicts": [],
 "coverage": 5, "frontier": 1}

$ dotmaps surface
Nothing needs you.
$ echo $?
0
```

Plus, demonstrating the frontier side of the same story:

```
$ dotmaps queen migration
{"covered": [], "frontier": [5 staffing plans, budget attached,
 learner: "requires Q7 or human-run"], "model_calls": 0, "cost_usd": 0.0}
```

The resulting trip log (`runs/queen/trips.jsonl`, committed, hash-chain
verified OK) reads top-to-bottom as the story of the run: 4 CERTIFIED
(pilot coverage, \$0) → 1 SLEEP (consolidation tick) → 5 SHELVED
(migration frontier staffed for growth). `dotmaps queen pilot` also
updated the real `skills/*.yaml` decay blocks (C3, write-on-read) —
that mutation is the metabolism actually working, not test pollution,
and is committed as part of this flight's evidence.

**Full pytest: 158 passed, 1 skipped** (the skip is
`test_compiler.py`'s known live-network case — environmental, pre-
existing, called out as acceptable in the build brief). Every gate above
is a separate commit on `queen-v0`.

## Known limits

- **Pilot-domain only.** The dry-run path is proven against exactly two
  maps (the grown pilot map and `map-content-migration`) — both drawn
  from the same `corpus/pilot/seed-ws` family the EQUIP campaign already
  validated. A third, unrelated domain has not been dispatched through
  this queen.
- **Live growth works but is not the default.** Q7 fixed and demonstrated
  `ClaudeCodeLearner`, but every default path in this package (`dispatch`,
  `sleep`, `surface`, `governor`) stays model-call-free by construction —
  `queen/live.py` is the sole, explicit opt-in. Cost per live call
  observed at \$0.02–\$0.08; `TINY_LIVE_BUDGET` caps a smoke run, not a
  campaign.
- **Persistence budget is thin.** The backtested constant is 1 poke
  (median hypothesis confirms first-try in the archived data) — the
  governor leans on `MIN_N_FOR_VERDICT=3` more than on the budget itself
  to avoid premature WALL/CHURN verdicts. More live data (Q7's path) would
  let this sharpen.
- **Gatekeeper and Purple are structurally ready but not fed live data
  yet.** Both are fully built and tested against synthetic ledgers;
  neither has run against a real multi-period Composter audit cycle
  because the queen has only flown once so far.
- **FSRS-lite in `reconsolidate.py` is deliberately crude** (see
  EMPIRICAL-TODO list below) — a flat per-use stability bump and a fixed
  half-life, not a fitted curve. This is the v0 the metabolism spec
  itself calls for; C7's "needs rewiring to C3" is done, "needs fitting"
  is not.
- **`docs/index.html` has no nav structure to extend** — it's a narrative
  report page, not a site shell. Demo links landed in README.md instead
  (the closest existing "index if trivial"), per the brief's own
  conditional.

## EMPIRICAL-TODO

All three live in `queen/reconsolidate.py`, the FSRS-lite v0:
- `STABILITY_INCREMENT = 1.0` — flat per-use bump, unweighted by
  invocation context or skill criticality.
- `SHELF_HALF_LIFE_DAYS = 30.0` — order-of-magnitude guess; no re-cert
  failure data exists yet to fit a real decay curve against.
- `SHELF_THRESHOLD = 0.2` — the decay fraction that triggers a re-check
  proposal; same reason, no failure data yet.

None of these are silent magic numbers — each is imported from one place
(`reconsolidate.py`), commented at the point of definition, and will get
real data to fit against once `dotmaps sleep` has run for real across
enough elapsed time to observe actual re-cert outcomes.

## BLOCKED

Nothing. Every gate closed; the acceptance test passes end to end.

## The human's first flight — exact commands

```bash
# 1. the whole acceptance sequence, in order
dotmaps queen pilot        # routes 4/4 covered, $0, zero model calls
dotmaps sleep               # one consolidation tick
dotmaps surface             # "Nothing needs you." (exit 0) or a decision (exit 1)

# 2. see the frontier staffing plan on the second domain
dotmaps queen migration

# 3. read the trip log as a story
python3 -m dotmaps.queen.trips runs/queen/trips.jsonl

# 4. Purple's act-rate ledger (refuses below 20 events — expected empty/refused this early)
dotmaps surface --purple

# 5. resolve a decision, if surface ever asks one
dotmaps surface --resolve <id> --choice <n>

# 6. re-run the governor's backtest (free, deterministic, no model)
python3 experiments/governor_backtest.py

# 7. OPTIONAL, subscription-billed, real money-equivalent usage: live
#    dispatch against the frontier (tiny budget, ~$0.10-0.30 observed)
dotmaps queen migration --live --driver claude-code

# 8. full test suite
cd dotmaps && python3 -m pytest tests -q
```

Build well. Gates, not advice. Silence except trips. 🦈

## Human flights 1–4 (Aug 12–13) — the first conversation

**Flight 1** (`bd7909b`): `dotmaps queen migration` — all five frontier
predicates shelved honestly; after the second shelve the queen raised her
first five ESCALATE questions. The surface flipped from "Nothing needs
you." to five real decisions with three options each.

**Flight 2** (`cce82ed`): the human answered all five (choice 1, grow now —
Purple's first five acted events, seq 23–27) and ran the first live
subscription-billed growth. Five primitives banked, including r004, a real
mutation rule. **Gap found:** grown primitives were never harvested into
the library, and "grow now" dispatched a 3-poke smoke.

**Gap closure** (`flight-2 gap closure` commit): HARVEST wired into sleep
(bank_extract over runs/queen-live/*), library-wide dedup in the extractor,
certify_all hardened to run on a disposable seed copy, AUTHORIZED_BUDGET
(60 pokes) + `--authorized`. Integration: harvested 5, coverage 5→9.

**Flight 3** (`847d46f`): authorized campaign, 14 more primitives banked,
library 25 cards / 23 certified. **Miss:** the TARGET STATEMENTS directive
never reached the reused agent-ws (board still ended at the July 12
approval); the learner foraged the source corpus instead of the five dots.

**Flight 4** (`481bed2`, after the directive-delivery fix): the mission
brief reached the board — and the learner still banked 16 source
invariants and never created target_items.json. **The program's own law
explains it: mechanical gates beat informational surfacing (36/36 vs
5/10). A mission written as board text is advice; the grow protocol is the
mechanism, and the mechanism hunts invariants.** The five migration dots
describe a COMPLETED migration; verification-only growth cannot make them
true.

**Standing finding → next organ:** separate DO from VERIFY. A work-order
phase — full agentic Claude Code (tools on) scoped to a temp workspace,
one job: perform the migration — followed by targeted growth against the
completed state, where the five statements are finally bankable. Execution
as mechanism, verification as growth. This is Layer 2's first plank,
arrived by evidence.

**Colony state at close:** 61 hash-chained trips (chain verified intact) ·
library 25 cards / 23 certified · Purple 5/20 events · migration map
honestly 0/5 covered, pilot map 4/4 at $0 · every flight and every miss on
the public record.

## QUEEN OS v1 — she's in service.

Branch `queen-os`, off `queen-v1` with `queen-watch`'s W1–W3 already in the
line. Built per `QUEEN_OS_PRD.md` in four commit-per-gate steps (G1–G4);
`COMPANION_BRIEF.md`, named in the brief as required reading for its C1/C2
mechanics, was not present in this checkout — its two mechanics (a
first-launch home-folder pick, and route-first-then-work-order chat) were
rebuilt from the PRD's own description rather than skipped.

**What shipped, gate by gate:**

- **G1 — `queen/init.py` + `queen/chat.py` + `queen/workflows.py`.**
  `dotmaps init` (C1): one-screen, once — home folder + linked folders,
  `runs/queen/home.json`. `dotmaps chat` (Tab 1's engine): a parallel
  hash-chained ledger (`runs/queen/chat.jsonl`, same chain math as
  `trips.py`, a separate file on purpose — chat messages aren't trip
  types). ROUTE FIRST checks named workflows (`queen/workflows.py`, seed:
  the demo workspace + the menu migration; chat-born: discovered live from
  `maps/map-chat-*/chat_trigger.json`, no parallel registry) via
  `bank/route.py` — $0, zero model calls, mechanically re-earned every
  time, never a stored label. Not covered → a WORK ORDER: `claude -p`,
  tools on, scoped to a disposable copy of the demo workspace, streamed
  (`--output-format stream-json`) into `WORK_ORDER phase=step` trips so
  the Run tab can show live steps as they happen. A mechanical completion
  gate (an `answer.json` naming a real file + a real check, never
  self-report) decides the reply; a passing answer gets re-validated with
  `grow/banking.confirm()` — the actual discriminating bank gate, not a
  rubber stamp — before she ever offers to learn it. "Yes" (via
  `surface.py`'s escalate/resolve, reused verbatim, per the brief) writes
  a real primitive under `runs/queen-live/chat-*/` (picked up by the
  *existing* `sleep()` harvest — zero new code there) and compiles a real
  one-dot map under `maps/map-chat-*/`, so the identical ask routes free
  through the ordinary dispatch path the moment `dotmaps sleep` certifies
  it.
- **G2 — the four remaining tabs' backend.** `queen/paper.py`: a small,
  dependency-free markdown→HTML pass over `docs/paper/*.md`, with live
  numbers substituted from the real record before render. Six sections
  written (The Receipt, How She Learns, What Died, The 12× Finding, The
  Laws, The Colony & The Keeper) — every one hand-checked against the
  zero-jargon list, one caught mid-draft ("frontier of the model" in The
  Receipt's own prose) and rephrased. `queen/ui.py` gained
  `/api/init`, `/api/chat` (+ `/api/chat/resolve`), `/api/run/state` (the
  live step feed, grouped by `WORK_ORDER` `run_id`), `/api/memory`,
  `/api/workflows` + `/api/workflow/<name>/run` (always the free dispatch
  pass — a click never silently spends), `/api/watchers`, `/api/paper` —
  all read-only except the two writes (chat, resolve), same discipline as
  Q10.
- **G3 — the five-tab rebuild.** `queen/static/index.html` rewritten
  whole: light, soft-paper ground, one honey accent, Instrument Serif for
  her voice only — DESIGN LAW, replacing `queen-v1`'s dark "night hive."
  Chat (default) · Run (live steps, receipt-tap, idle tape replay) ·
  Memory (honeycomb + list toggle, section-header stats, tap-through
  detail sheet) · Workflows (coverage dot-row + RUN button, "point her at
  something" folded in from the existing watch endpoints) · The Paper.
  Onboarding overlay wired to `/api/init`, shown once. A second banned
  word (`frontier_count`, a field name leaking into the page's own JS) was
  caught by the scan and renamed to `not_yet` on both ends.
- **G4 — `assure` grows three claims.** #12 chat routes covered work
  modelless (stub-tested with a runner that raises if called — a
  regression that falls through to a work order on covered ground fails
  loud, not silent); #13 zero jargon across all five tabs (re-scans the
  static page **and** the live-rendered paper — a page-only scan would
  miss a paper regression); #14 chat chain integrity. `dotmaps assure`:
  **14/14 PASS.**

**The acceptance test — run for real, live, subscription-billed where the
brief calls for it:**

```
$ dotmaps init --home ~/dotmaps
{"home": "/Users/joefiorillo/dotmaps", "linked": [], "initialized_at": "..."}

$ dotmaps hive --port 8811   # → onboarding once (already done above) → Chat tab

POST /api/chat {"message": "check the demo workspace"}
→ {"chip": {"kind": "free", "label": "$0 · certified replay", "model_calls": 0}}
   (4/4 confirmed, $0, zero model calls)

POST /api/chat {"message": "Is there a putting class in the schedule? Check
                exactly which item slug it is."}
→ live: 10 WORK_ORDER trips (start → 8 streamed steps, real tool names and
   elapsed times → complete), watchable in the Run tab as they happened
→ {"reply": "Yes, the putting class is \"Putting Intensive\", with the item
   slug \"putting-intensive\".",
   "chip": {"kind": "model", "label": "model called · 7 turns", "turns": 7,
            "cost_usd": 0.0776},
   "learn_offer": {"id": "77d5cf543c7c",
     "statement": "source_items.json contains an item with slug \"putting-intensive\""}}

POST /api/chat/resolve {"id": "77d5cf543c7c", "choice": 1}
→ {"learned": true, "map": "map-chat-is-there-a-putting-class-in-the-schedule",
   "note": "Got it — she'll know that for free after her next sleep."}
   (runs/queen-live/chat-is-there-a-putting-class-in-the-schedule/primitives/r001.yaml
    written; maps/map-chat-is-there-a-putting-class-in-the-schedule/ compiled)

$ dotmaps sleep
{"harvested_candidates": 1, "coverage": 33, "frontier": 2}
   (skills/source-items-json-contains-an-item-with-slug-put.yaml: candidate
    → certified, wilson [0.839, 1.0], n=20 — the real oracle gate, not a
    rubber stamp)

POST /api/chat {"message": "Is there a putting class in the schedule? Check
                exactly which item slug it is."}   # the SAME ask
→ {"reply": "Yes, the putting class is \"Putting Intensive\", with the item
   slug \"putting-intensive\".",
   "chip": {"kind": "free", "label": "$0 · certified replay", "model_calls": 0}}
   (identical reply text, zero model calls — the loop closed)

POST /api/workflow/migrate-the-menu-data/run
→ {"covered": 0, "not_yet": 5, "model_calls": 0}   # honest — real, one-button, $0

$ dotmaps assure    # ALL GREEN, 14/14
$ cd dotmaps && python3 -m pytest tests -q    # 260 passed, 1 skipped
```

Colony state at close of this flight: **116** hash-chained decision-record
entries (chain verified intact) · **7** chat messages (own chain verified
intact) · library **35** cards / **33** certified, one of them — the
putting-intensive fact — born entirely inside a chat conversation, banked,
certified, and now replaying for $0 · **9** free executions on the record ·
the one live model call this flight made cost **\$0.0776**, subscription-
billed, no API key ever touched. Every claim in this section is one query
away from the file that proves it, same as the paper tab says of itself.

**Known limits, honestly carried forward:** the migration play still
shows honestly 0/5 (its real work-order + authorized-growth path,
`queen/live.py --authorized`, is a separate, deliberately-not-one-click
action — MONEY LAW; the Workflows RUN button always takes the free
dispatch pass). Chat's WORK ORDER is scoped to the demo workspace only
(`corpus/pilot/seed-ws`) in this flight — home/linked-folder scoping from
`dotmaps init` names the *allowed* directories (`queen/init.py`'s
`scoped_dirs()`) but chat's default `seed` parameter isn't yet threaded to
prefer them over the demo workspace; a real keeper's non-demo folder would
need `dotmaps chat` called with `--home`-aware wiring not yet built. A
freshly re-asked, not-yet-certified chat question (between "yes" and the
next `dotmaps sleep`) currently re-runs a full billed work order rather
than saying "ask me again after she sleeps" — mechanically honest, just
not the cheapest possible UX; out of scope for this brief's acceptance
test, which never exercises that path.

The keeper's next act after this merge is USE, not another brief. 🐝
