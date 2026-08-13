"""QUEEN v0 — the dispatch organ (QUEEN_v0_spec.md).

She is a dispatch organ over already-proven parts: routing (bank/route.py),
certification (bank/certify.py), growth (grow/*). This package is wiring,
not invention (QUEEN_BUILD_BRIEF.md). MONEY LAW: nothing in here defaults
to a live model call. Every dispatch command is dry-run native.

Modules, build order Q1-Q7:
  trips           append-only trip bus, the queen's only sense organ
  surface         Fio's one card: "Nothing needs you." or a decision
  dispatch        READ/ROUTE/STAFF/BUDGET/ESCALATE — the dispatcher
  governor        abort governor: competence-flatness, oracle-validity,
                  objective-provenance, backtested against archived runs
  reconsolidate   C3 — write-on-read decay updates on skill invocation
  gatekeeper      the mutualist audit (state-change/transfer/parasite)
  purple          the theory-of-Fio ledger (act-rate per escalation category)
  sleep           the homeostasis tick: decay -> recompute -> dedup -> SLEEP
  live            Q7 (optional): subscription-billed live dispatch
"""
