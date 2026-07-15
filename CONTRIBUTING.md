# Contributing

Small project, strong invariants. Before you open a PR:

- **Never edit run data.** Everything under `runs/`, plus the registrations
  and reports in `corpus/` and `grow/`, is append-only history. Formatting,
  trimming, or "cleaning" those files is a breach, not a cleanup.
- **A check that cannot fail is not a check.** New verifiers must fail on a
  broken workspace — the test suite enforces this pattern; follow it.
- **Claims carry evidence.** If your PR adds a quantitative claim to any
  doc, cite the bundled file it traces to, inline.
- Run `pytest` (from the repo root). It needs no models, no network, no
  Docker — anything requiring those must skip cleanly when absent.

Bug reports with a replayable journal attached are worth ten without one.
