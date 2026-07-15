# Fog — what map 3 (health re-certification) does NOT decide

Map 3 re-runs map 1's *read-only* checks against production on a schedule. It
inherits map 1's fog (design quality, content accuracy, full form-delivery
chain, a11y/SEO, security, cross-browser) and adds these boundaries:

- **It does not fix anything.** A red dot is an alert, not a repair. Remediation
  (if enabled) is a separate traveler action gated by Phase-2 safety; the health
  certificate only reports state.
- **It does not check the build or the signup write path.** By design: a health
  check never rebuilds and never POSTs to production. Those live in map 1.
- **It certifies a moment, not a warranty.** "All checks green at 06:00 UTC" is
  exactly that — the next run may differ. Map rot is expected and is precisely
  what the recurring cadence exists to catch.
