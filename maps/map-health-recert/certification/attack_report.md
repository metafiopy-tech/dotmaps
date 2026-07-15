# Attack report — map 3 (health-recert) v0.1.0

**Status: first adversarial pass (model-generated, 2026-07-10). Joe's pass
pending. Proves gaps exist, never that none remain.**

Map 3's attack surface is intentionally the smallest of the three: every dot is
read-only, and in its primary mode (scheduled `dotmaps verify`) there is no
traveler at all — nothing agentic exists to misbehave. Findings therefore focus
on the certificate's honesty rather than agent malice.

## Findings

### C1 — Config tampering (CRITICAL in traveler mode → FIXED, structural)
**Attack:** if a remediation traveler is enabled, it could repoint
`target.json`'s `base_url` at a healthy site and "cure" every red dot.
**Disposition: HARDENED.** Same structural fix as map 1's A1 (authoritative
config in `.dotmaps/`, verifier precedence — map 3 shares map 1's verifier lib).

### C2 — Moment-in-time laundering (MEDIUM → wording rule)
**Attack:** none needed — a site that is up at 06:00 and down 23 hours a day
collects a daily green certificate.
**Disposition: WORDING + CADENCE.** The certificate states the timestamp of the
checks and nothing else ("all checks green at T"), per the §4.6 scoped-claims
rule; fog says explicitly that a heartbeat certifies a moment. Cadence is
user-chosen; more frequent runs are the product's answer, not stronger claims.

### C3 — Cached/CDN ghost passes (MEDIUM → accepted for v0.1)
**Attack:** an origin that is dead behind a CDN still serves 200s from cache;
dots h01–h04 pass while the site is effectively unmaintained.
**Disposition: ACCEPTED + fogged.** For a *health* map, "visitors get a working
page" is arguably the truth that matters, and CDN-cached is working. Origin
liveness (cache-busting probe) is a v0.2 dot if buyers need it.

### C4 — Lighthouse flap (LOW → same as map 1 A6)
Scores near the threshold flap run-to-run; in a *recurring* map this generates
regression noise. **Disposition: ACCEPTED for v0.1**; median-of-3 is the v0.2
hardening. Regression events are honest — noisy beats silent.

## Residual verdict
With C1 closed, a false green requires the deployment itself to lie (C3) or a
moment-vs-warranty misreading (C2), both addressed by scoped wording + declared
fog. This map is certification-ready pending Joe's pass + probe against a
healthy target.
