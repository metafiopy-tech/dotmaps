# QUEEN BUILD — FINAL BRIEF (close the loop, show the body, prove it all)
## Claude Code session, subscription-only. Branch `queen-v1`. Same laws as
## QUEEN_BUILD_BRIEF.md (read it + QUEEN_FLIGHT_LOG.md "Human flights 1–4"
## first — flight 4's DO/VERIFY finding is the reason this brief exists).
## MONEY LAW unchanged: no API key, ever. Commit per gate. No push.

### Q8 — The work-order organ (DO, mechanically separated from VERIFY)
Flight 4 proved: a mission written as board text is advice, and advice
loses to mechanism (36/36 vs 5/10). So execution becomes its own phase:
`queen/workorder.py` — for an authorized dispatch, BEFORE any growth:
1. Copy seed → temp workspace (existing pattern in live.py).
2. Run the FULL agentic Claude Code (tools ON — this is what the persona
   is for) via `claude -p` scoped to that workspace with ONE job composed
   from the map: "Perform the task described by <config>. Work only inside
   this directory." Subscription-billed, budget-capped (--max-turns ~30,
   wall-clock timeout).
3. MECHANICAL COMPLETION GATE, not self-report: after the run, check the
   map's frontier statements against the workspace with cheap probes where
   derivable (e.g. target file exists and parses). If the gate fails →
   WORK_ORDER_FAILED trip + stop; never proceed to growth on an
   incomplete workspace.
DONE-TEST: on the migration preset, the work order produces a real
target_items.json (5 items, migrated per migration.json) in the temp
workspace; gate passes; a deliberately-sabotaged config fails the gate
and emits the trip.

### Q9 — Targeted verify-growth on the completed workspace
Extend live.py: authorized flow = workorder → THEN grow in the SAME
completed workspace, board carrying the five target statements (now
true and bankable). Fresh -authNN run dir; harvest already handles the
rest. Add trip type WORK_ORDER (start/complete/failed) to trips.py's
fixed vocabulary (append to the enum + tests; chain format unchanged).
DONE-TEST (the one that matters): after `dotmaps queen migration --live
--driver claude-code --authorized` + `dotmaps sleep`, the route check
`dotmaps queen migration` shows ≥1 dot flipped frontier→covered. If ≤
budget can't flip m04/m05, the flipped subset + honest SHELVED for the
rest is a PASS — flipping SOME dots proves the loop; flipping none fails.

### Q10 — The UI: `dotmaps ui`
One command serves the operator console on localhost (stdlib
http.server; zero deps). Single-file page (adapt docs/queen.html's
night-hive design) reading LIVE state via tiny JSON endpoints:
/api/surface (surface state + open questions w/ resolve buttons that
POST), /api/trips (the chain, integrity-checked, rendered as the feed),
/api/manifest (coverage/frontier per map, skill cards w/ Wilson +
decay clocks), /api/flights (runs/queen-live/* summaries). Read-only
except resolve. This is the "watch everything working" surface —
the demo pages made real.
DONE-TEST: server starts, all four endpoints serve real repo state,
resolve round-trips into trips.jsonl, page renders with no console
errors (verify with a headless fetch of each endpoint + HTML).

### Q11 — `dotmaps assure`: the certainty command
The answer to "how can I be sure it does everything we said."
`queen/assure.py` walks a CLAIMS table — each row: claim text, the
mechanical check, the artifact it reads — and prints PASS/FAIL, exit
nonzero on any FAIL. Minimum rows:
 1. Pilot map routes 4/4 covered, $0, zero model calls (run it).
 2. Every certified skill's certificate re-verifies: re-run its probe
    battery deterministically against a disposable seed copy.
 3. Trip chain integrity: full hash-chain re-verification.
 4. Frozen files unchanged: sha256 of extractor rubric constants,
    certify oracle-gate block, every *_registration.md vs a MANIFEST OF
    FROZEN HASHES committed by this gate (generate it now, verify ever
    after).
 5. Governor backtest reproduces: rerun experiments/governor_backtest.py,
    assert p75 and the e1c/e1d refog reproductions match the committed
    report.
 6. Harvest idempotence: a sleep tick on a temp copy harvests 0 new.
 7. C3 safety: touch() on every certified card leaves method/check bytes
    hash-identical.
 8. Efficiency-claim funeral intact: runs/e1d-verdict/verdict.json parses
    and says DEAD (the repo must never quietly forget its own funeral).
 9. Work-order gate (post-Q8): sabotaged config fails closed.
10. UI endpoints serve (post-Q10).
DONE-TEST: `dotmaps assure` green on this checkout; deliberately
corrupting a trip line or a frozen file flips the right row red.

### Acceptance (mission complete)
`dotmaps assure` fully green · migration shows ≥1 covered dot · `dotmaps
ui` demonstrates surface/trips/manifest/flights live · suite green ·
QUEEN_FLIGHT_LOG.md gains "v1: DO/VERIFY + assure" section with every
done-test result and the exact demo script (the sequence of commands
that shows everything working, for the writeup's final figure and the
fifteen emails' 3-minute demo).
