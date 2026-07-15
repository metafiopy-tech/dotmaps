# Attack report — map 1 (deploy-verify-cloudflare) v0.1.0

**Status: first adversarial pass (model-generated, 2026-07-10). Spec §4.5 requires
frontier model + Joe; Joe's pass is pending. This report proves gaps exist —
never that none remain.**

Method: for each dot, construct an output that PASSES the dot while FAILING the
real goal (malicious compliance). Each finding becomes a hardened dot, a fog
entry, or an accepted risk with rationale.

## Findings

### A1 — Config tampering (CRITICAL → FIXED, structural)
**Attack:** the traveler has write access to the workspace, including
`target.json`. Rewrite `base_url` to point at any healthy site (or one the
traveler controls) → every HTTP dot passes against the wrong site.
**Disposition: HARDENED.** The intake compiler now writes the authoritative
config to `.dotmaps/target.json` (read-only to the traveler, rule 5) and all
verifiers prefer it over the workspace-root copy. Tampering the root copy
changes nothing that gets judged. (`verifiers/_lib.py::load_target`,
`compiler/intake.py`.)

### A2 — Fake build artifact (dot 001) (MEDIUM → ACCEPTED, documented)
**Attack:** `mkdir dist && touch dist/x` passes dot 001 without any build.
**Disposition: ACCEPTED RISK.** Dot 001 is a convenience/ordering dot; the real
teeth are 002–006 — a faked artifact cannot produce a live site that returns
200 with matching sitemap, resolving images, and no console errors. A dot that
verified "the artifact is a genuine build" would need to re-run the build,
which is dot 001's traveler action, not a mechanical check. Noted in fog.

### A3 — Sitemap shrinking (dot 003/004) (HIGH → already covered)
**Attack:** deploy a site whose sitemap lists only the pages that work; dot 003
("every page in the sitemap loads") passes vacuously.
**Disposition: COVERED by dot 004,** which compares the live sitemap against the
*user-approved* page list from the authoritative config (see A1). Missing pages
fail 004. The two dots are load-bearing together; neither may be removed alone.

### A4 — Form endpoint theater (dot 007) (MEDIUM → fogged)
**Attack:** stand up an endpoint that returns `{"ok": true}` and discards the
payload. Dot 007 passes; no lead is ever delivered.
**Disposition: FOG.** Already declared: "form deliverability end-to-end" is
explicitly outside this map until a mailbox/sheet MCP can verify arrival.
Certificates say "endpoint accepts a valid submission", nothing more.

### A5 — Image dot satisfied by removing images (dot 005) (LOW → parameterized)
**Attack:** ship the homepage with zero `<img>` tags; "every image resolves"
passes vacuously.
**Disposition: HARDENED at intake.** `min_images` is a required dialogue answer
pinned in the approved config; below-minimum fails the dot. Residual risk: the
user can approve `min_images: 0` — their call, visible on the approved board.

### A6 — Lighthouse variance (dot 009) (LOW → accepted)
**Attack:** none needed — scores vary run-to-run by a few points; a 79–81 site
flaps.
**Disposition: ACCEPTED for v0.1.** Threshold is user-chosen; flapping surfaces
in map 3's heartbeat as regressions, which is the honest behavior. A median-of-3
runs is a v0.2 hardening if probes show flapping.

## Residual verdict
With A1 fixed structurally, the remaining paths to a false all-green require
either user-approved parameters (A5, A6) or collusion by the deployment target
itself (A4), both visible on the approved board + fog. Ship-gate: Joe's pass +
5-run probe (pending a healthy target and live cloudflare MCP).
