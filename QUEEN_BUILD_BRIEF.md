# QUEEN v0 — AUTONOMOUS BUILD BRIEF
## Mission for a Claude Code session. Run until the acceptance test passes.

You are building Queen v0 in this repo (dotmaps). She is a dispatch organ over
already-proven parts. Almost everything you need exists; your job is wiring,
not invention. Work on branch `queen-v0`. Commit after every gate with a
message that states what was built and what its test proved. Do not push;
the human reviews and pushes.

READ FIRST (in repo): `QUEEN_v0_spec.md`, `metabolism-spec-v0_1.md`,
`EQUIP_v1_spec.md`, `runs/e1d-verdict/verdict.json`, and skim
`dotmaps/dotmaps/bank/` (extractor/certify/route) + `dotmaps/dotmaps/grow/`
(runner/banking/store/clock/learner) + `experiments/e1_paired_runs.py`
(preequip pattern).

## FROZEN LAWS — violating any of these fails the mission
1. Mechanical gates, never advice. Every rule is code that blocks, not text
   that suggests.
2. Never modify: `bank/extractor.py` rubric constants, `bank/certify.py`
   oracle-gate ordering, the compiler's frozen tier rubric, anything under
   `runs/` (append new runs only), any `*_registration.md`.
3. Re-synthesis never touches crystallized artifacts: certified skill steps
   replay VERBATIM. C3 reconsolidation applies to usage stats and traces,
   never to `method.steps` or `check` of a certified skill.
4. The queen dispatches for frontier depth and free coverage — never for
   cost savings (that claim is dead; see e1d verdict).
5. Every component ships with pytest coverage. Suite must be green (the one
   known live-network test failure in test_compiler.py is environmental and
   acceptable) before a gate counts as closed.
6. No new magic numbers. Any threshold is either imported from existing
   config, backtested (Q3), or marked `# EMPIRICAL-TODO` with a comment.

## BUILD ORDER — serial, each gate has a done-test

### Q1 — Trip bus + Fio surface
Build `dotmaps/dotmaps/queen/trips.py`: append-only JSONL event log
(`runs/queen/trips.jsonl`) with typed events: CERTIFIED, CONVICTED, BLOCKED,
BUDGET_EXHAUSTED, ORACLE_FAIL, SHELVED, ESCALATE, SLEEP. Emit points: wire
into bank/certify.py outcomes, route.py frontier verdicts, and the grow
runner's gate blocks (import-light: a tiny `emit(event, payload)` helper;
grow modules may not import queen — use a callback/hook pattern so grow
stays standalone).
Build `dotmaps/dotmaps/queen/surface.py`: renders the one-card surface from
the trip log — "Nothing needs you." unless unresolved ESCALATE events exist,
in which case show them as decisions (question + options), never as reports.
CLI: `dotmaps surface`.
DONE-TEST: emitting a synthetic ESCALATE flips the surface; resolving it
(`dotmaps surface --resolve <id> --choice <n>`) restores calm; trips.jsonl
is append-only (test that rewrite attempts fail).

### Q2 — The dispatcher
Build `dotmaps/dotmaps/queen/dispatch.py` + CLI `dotmaps queen <task.yaml|preset>`:
READ: compile task → predicates (reuse existing compiler path; for v0 accept
a map.yaml directly as the compiled form — presets: the pilot grown map and
maps/map-content-migration).
ROUTE: manifest coverage via bank/route.py — covered predicates execute
certified skills at $0 (emit nothing; silence is the point), frontier
predicates listed.
STAFF: for frontier predicates, assemble an equipped grow dispatch using the
preequip() pattern from experiments/e1_paired_runs.py (certified skills
banked as inherited primitives). Learner: AnthropicLearner if
ANTHROPIC_API_KEY present; otherwise run in --dry-run mode that stops after
routing and prints the dispatch plan (the human runs live growth).
BUDGET: ClockConfig budgets per dispatch; emit BUDGET_EXHAUSTED trip on cap.
ESCALATE: any predicate SHELVED twice → ESCALATE trip with a concrete
question.
DONE-TEST: `dotmaps queen pilot --dry-run` routes the learned map 4/4
covered/$0/zero model calls (matches G3's committed result) and the
content-migration preset shows 5 frontier with a staffing plan. End-to-end
pytest with a stub learner proving dispatch→trips→surface flow.

### Q3 — Abort governor, BACKTESTED (free, no API)
Build `dotmaps/dotmaps/queen/governor.py`: the three orthogonal criteria
from QUEEN spec §4a.3 — (a) competence-flatness via typed failure categories
+ chi-null churn test over a dispatch's hypothesis stream; (b) oracle-validity
structural check (delegates to certify.py's oracle gate); (c) objective
provenance flag (inherited vs self-generated; v0: all inherited, guard is a
hard assert). Plus the persistence budget: initial constant = 75th percentile
of pokes-before-first-bank per hypothesis family computed FROM THE 32+
ARCHIVED E1b/E1c/E1d JOURNALS in runs/ — write the backtest as
`experiments/governor_backtest.py`, output `runs/governor-backtest/report.json`.
DONE-TEST: the governor, run retroactively over the archived e1* journals,
reproduces the published verdicts (churn walls flagged in the runs where
verdicts recorded them; zero false WALL verdicts on the clean e1d runs).
This is the gate: history must grade it before live money does.

### Q4 — C3 reconsolidation hook (the metabolism's first organ)
In `bank/`: on every certified-skill invocation via route.py, update the
skill card's decay block (`last_used`, invocation count, FSRS stability
update) and append a usage delta to the trip-adjacent usage log. NEVER touch
method.steps or check (law 3). Add shelf-recheck scheduling: skills whose
stability decays past threshold get a SHELVED trip proposing re-certification
(certify.py rerun — deterministic, cheap).
DONE-TEST: invoking a skill twice updates its clock; simulated time
advance (inject clock) triggers exactly one re-check trip; a re-certified
skill resets; steps/check bytes are hash-identical before and after.

### Q5 — Purple's ledger
`dotmaps/dotmaps/queen/purple.py`: every ESCALATE resolution records
(category, acted/deferred/ignored, latency). v0 policy: everything
escalates (over-escalation is honest cold-start); the act-rate table is
computed and displayed via `dotmaps surface --purple` but the threshold is
NOT auto-applied until ≥20 events (hard-coded gate with the count visible).
DONE-TEST: ledger accrues; threshold application refuses below 20 events.

### Q6 — Sleep
`dotmaps/dotmaps/queen/sleep.py` + `dotmaps sleep` (also cron-ready):
one consolidation pass = FSRS decay tick across all skill cards →
manifest recompute (extractor/certify state re-read, coverage/frontier
refreshed) → dedup sweep → due shelf re-checks executed (deterministic) →
SLEEP trip emitted with a morning-readable summary (skills held/decayed/
re-checked, trips digested).
DONE-TEST: a full sleep run on the current repo state completes, emits one
SLEEP trip, and is idempotent (second immediate run changes nothing).

## ACCEPTANCE TEST — "the first flight" (mission complete when this passes)
`dotmaps queen pilot` (live if key present, --dry-run otherwise) then
`dotmaps sleep` then `dotmaps surface` produces:
- covered work executed at $0 with zero model calls,
- frontier plan (or live growth) with governor active,
- a trip log a human can read top to bottom as the story of the run,
- a surface that either says "Nothing needs you." or asks one real question,
- a sleep summary,
- full pytest suite green, every gate committed separately on `queen-v0`.
Write `QUEEN_FLIGHT_LOG.md` at repo root: what was built, every done-test
result, known limits (pilot-domain only; live-learner steps needing the
human; the one EMPIRICAL-TODO list), and the exact commands for the human's
first real flight.

## WHAT YOU MUST NOT ATTEMPT (human-only, out of scope)
Ben's-site oracle (needs his access) · any new pre-registered experiment ·
pushing to origin · the fifteen emails · touching FioVault · spending money
beyond dispatch runs the human explicitly okays at launch.

Build well. Gates, not advice. Silence except trips. 🦈

## ADDENDUM
### Q4b — Gatekeeper v0 (insert after Q4, before Q5)
`dotmaps/dotmaps/queen/gatekeeper.py`: the three-test mutualist audit from
QUEEN spec §4a.1 (state-change via act-rate, transfer via cross-domain skill
firing, parasite via friction-class trend), run against the Composter's real
ledger data. Hard gate: refuses to render a verdict on insufficient data
(<1 audit period) — an audit that can't fail is not an audit.
DONE-TEST: synthetic ledgers for pass and fail cases; empty ledger refuses.

### Session hygiene
- If resuming after interruption/compaction: `git log --oneline queen-v0`,
  read QUEEN_FLIGHT_LOG.md if present, continue from last committed gate.
- If a live dispatch dies to network/API: mv the run dir to `-VOID-<reason>`,
  commit, retry once, then continue the mission and note it in the flight log.
- If truly blocked on a decision only the human can make: write the question
  into QUEEN_FLIGHT_LOG.md under "BLOCKED", commit, and stop cleanly.
