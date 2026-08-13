# QUEEN v0 — AUTONOMOUS BUILD BRIEF (subscription-only edition)
## Mission for a Claude Code session (Max plan, no API key, $0 build).
## Run until the acceptance test passes.

You are building Queen v0 in this repo (dotmaps). She is a dispatch organ
over already-proven parts. Your job is wiring, not invention. Work on branch
`queen-v0`. Commit after every gate stating what was built and what its test
proved. Do not push; the human reviews and pushes.

## MONEY LAW — READ FIRST
This entire mission runs on the human's Claude subscription (this session)
and costs $0 beyond it. **Never use or require ANTHROPIC_API_KEY.** If it is
set in the environment, ignore it; never wire AnthropicLearner into any
default path. All dispatch commands default to `--dry-run`. Live model-driven
growth is OUT OF SCOPE except optional gate Q7 (subscription-billed via the
local `claude` CLI). The acceptance test is designed to pass with zero model
calls: the pilot map is fully covered by certified skills, which execute by
verbatim replay — no model in the loop.

## FILES FROM ~/Downloads/queenchat.zip (human has staged these)
Expect at repo root (copy from the unzipped folder if missing):
- QUEEN_v0_spec.md            (the queen, v0.3 — read fully)
- metabolism-spec-v0_1.md     (the substrate — read fully)
- Campaign Record — Aug 2-7 2026.md  (context + frozen laws)
Also in the zip, for docs/ (copy, add nav links from index if trivial):
- queen-console-demo.html  → docs/queen.html
- queen-for-everyone.html  → docs/queen-for-everyone.html
- memory-metabolism.html   → docs/memory.html
- memory-loop.html, memory-graphs.html → docs/
Also read in-repo: EQUIP_v1_spec.md, runs/e1d-verdict/verdict.json, and skim
dotmaps/dotmaps/bank/ (extractor/certify/route), dotmaps/dotmaps/grow/
(runner/banking/store/clock/learner), experiments/e1_paired_runs.py
(the preequip pattern).

## FROZEN LAWS — violating any of these fails the mission
1. Mechanical gates, never advice. Every rule is code that blocks, not text
   that suggests.
2. Never modify: bank/extractor.py rubric constants, bank/certify.py
   oracle-gate ordering, the compiler's frozen tier rubric, anything under
   runs/ (append new runs only), any *_registration.md.
3. Re-synthesis never touches crystallized artifacts: certified skill steps
   replay VERBATIM. C3 updates usage stats and traces only — never
   method.steps or check.
4. The queen dispatches for frontier depth and free coverage — never for
   cost savings (claim dead; see e1d verdict).
5. Every component ships with pytest coverage; suite green before a gate
   closes (the known live-network failure in test_compiler.py is
   environmental and acceptable).
6. No new magic numbers: thresholds are imported, backtested (Q3), or
   marked `# EMPIRICAL-TODO`.

## BUILD ORDER — serial; each gate has a done-test

### Q1 — Trip bus + Fio surface
`dotmaps/dotmaps/queen/trips.py`: append-only JSONL log
(runs/queen/trips.jsonl) with typed events: CERTIFIED, CONVICTED, BLOCKED,
BUDGET_EXHAUSTED, ORACLE_FAIL, SHELVED, ESCALATE, SLEEP. Wire emits into
certify outcomes, route frontier verdicts, and grow gate blocks via a
callback/hook (grow modules must not import queen).
`dotmaps/dotmaps/queen/surface.py` + CLI `dotmaps surface`: one card —
"Nothing needs you." unless unresolved ESCALATE events exist; those render
as decisions (question + options), never reports.
`dotmaps surface --resolve <id> --choice <n>` restores calm.
DONE-TEST: synthetic ESCALATE flips the surface; resolve restores; append-
only enforced (rewrite attempts fail a test).

### Q2 — The dispatcher (dry-run native)
`dotmaps/dotmaps/queen/dispatch.py` + CLI `dotmaps queen <preset|map.yaml>`:
READ: accept a compiled map directly (presets: `pilot` = the grown pilot map;
`migration` = maps/map-content-migration).
ROUTE: manifest coverage via bank/route.py — covered predicates execute
certified skills at $0 (silently; silence is the point); frontier listed.
STAFF: for frontier predicates, produce the full dispatch PLAN (inherited
primitives via the preequip pattern, budget, learner slot marked
"requires Q7 or human-run") — plan only, never a live model call.
BUDGET: ClockConfig budgets attached per plan; BUDGET_EXHAUSTED trip wired
for future live runs. ESCALATE: predicate SHELVED twice → ESCALATE trip
with a concrete question.
DONE-TEST: `dotmaps queen pilot` routes 4/4 covered / $0 / zero model calls
(must match G3's committed result); `dotmaps queen migration` shows 5
frontier with a complete staffing plan; end-to-end pytest with a stub
learner proves dispatch→trips→surface flow.

### Q3 — Abort governor, BACKTESTED (free)
`dotmaps/dotmaps/queen/governor.py`: (a) competence-flatness via typed
failure categories + chi-null churn test over a hypothesis stream;
(b) oracle-validity (delegates to certify's oracle gate); (c) objective-
provenance flag (v0: all inherited; hard assert). Persistence budget initial
constant = 75th percentile of pokes-before-first-bank per hypothesis family
computed FROM the archived e1b/e1c/e1d journals in runs/. Backtest:
`experiments/governor_backtest.py` → runs/governor-backtest/report.json.
DONE-TEST: run retroactively over archived e1* journals, the governor
reproduces the published verdicts — churn flagged where verdicts recorded
it, zero false WALL verdicts on the clean e1d runs. History grades her
before any live run does.

### Q4 — C3 reconsolidation hook (the metabolism's first organ)
On every certified-skill invocation via route: update the card's decay block
(last_used, invocation count, FSRS stability) and append a usage delta.
NEVER touch method.steps or check (law 3). Shelf-recheck scheduling: decayed
stability → SHELVED trip proposing re-certification (certify rerun —
deterministic, free).
DONE-TEST: two invocations update the clock; injected time-advance triggers
exactly one re-check trip; re-cert resets; steps/check bytes hash-identical
before and after.

### Q4b — Gatekeeper v0
`dotmaps/dotmaps/queen/gatekeeper.py`: the three-test mutualist audit
(QUEEN spec §4a.1) — state-change via act-rate, transfer via cross-domain
skill firing, parasite via friction-class trend — against the Composter's
ledger data. Hard gate: refuses any verdict on insufficient data (<1 audit
period); an audit that can't fail is not an audit.
DONE-TEST: synthetic pass + fail ledgers; empty ledger refuses.

### Q5 — Purple's ledger
`dotmaps/dotmaps/queen/purple.py`: every ESCALATE resolution records
(category, acted/deferred/ignored, latency). v0: everything escalates;
act-rate table via `dotmaps surface --purple`; threshold application
hard-refuses below 20 events (count visible).
DONE-TEST: ledger accrues; refusal below 20 enforced.

### Q6 — Sleep
`dotmaps/dotmaps/queen/sleep.py` + `dotmaps sleep` (cron-ready): FSRS decay
tick across cards → manifest recompute (coverage/frontier refreshed) →
dedup sweep → due shelf re-checks executed (deterministic) → SLEEP trip
with a morning-readable summary.
DONE-TEST: full run completes, one SLEEP trip, idempotent on immediate rerun.

### Q7 (OPTIONAL — attempt once, timebox ~1 hour) — subscription learner
The ClaudeCodeLearner in grow/learner.py failed smoke (claude -p returned
RESULT None with errors). You have the `claude` CLI locally: diagnose with
one minimal call (check stderr, errors field, flag syntax, --disallowedTools
validity, whether --max-turns 1 truncates before text). If a small fix makes
a real move parse: commit it, run ONE short live dispatch
(`dotmaps queen migration --live --driver claude-code`, budget-capped tiny)
as its smoke, note results in the flight log. If not fixable in the timebox:
document findings in the flight log under "Q7 parked" and finish the mission
without it. Never fall back to the API learner.

## ACCEPTANCE TEST — "the first flight"
`dotmaps queen pilot` → `dotmaps sleep` → `dotmaps surface` yields:
covered work executed at $0 with zero model calls · migration preset shows
its frontier staffing plan · governor active and backtest report committed ·
a trip log readable top-to-bottom as the story of the run · a surface that
says "Nothing needs you." or asks one real question · sleep summary · full
pytest green · every gate a separate commit on queen-v0.
Write `QUEEN_FLIGHT_LOG.md` at repo root: what was built, every done-test
result, known limits (pilot-domain; live growth pending Q7 or human), the
EMPIRICAL-TODO list, and the exact commands for the human's first flight.

## SESSION HYGIENE
- Resuming after interruption/compaction: `git log --oneline queen-v0`,
  read QUEEN_FLIGHT_LOG.md if present, continue from the last committed gate.
- Anything dies to network: mv artifacts to `-VOID-<reason>`, commit, retry
  once, continue; note in flight log.
- Truly blocked on a human decision: write it into QUEEN_FLIGHT_LOG.md under
  "BLOCKED", commit, stop cleanly.

## OUT OF SCOPE (human-only)
Ben's-site oracle · new pre-registered experiments · pushing to origin ·
the fifteen emails · FioVault · any API-key usage, ever.

Build well. Gates, not advice. Silence except trips. 🦈
