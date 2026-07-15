# Fog — what map 1 does NOT decide

Rendered honestly to the user (spec §4.1). These are the boundaries of the
certificate. The map certifies the checks in `map.yaml`; it does **not** decide:

- **Visual correctness / design quality.** That every page returns 200 and has
  resolving images says nothing about whether the layout looks right, copy is
  correct, or the brand is on-model. Human-approval item.
- **Content accuracy.** Whether prices, dates, camp details, and contact info
  are *true* — only that the fields render. Content correctness is map 2's
  concern (migration) and ultimately a human sign-off.
- **Form deliverability end-to-end.** Dot 007 confirms the endpoint accepts a
  submission; it does not confirm the Web3Forms email actually arrived in a
  human inbox or that the Google Sheet row is correct downstream. Verifying the
  full delivery chain is fog until a mailbox/sheet MCP is wired.
- **Accessibility & SEO beyond structure.** No WCAG audit; Lighthouse dot 009
  covers performance only, not a11y/SEO/best-practices categories.
- **Security posture.** No pen-test, no header/CSP audit, no secret-leak scan of
  the deployed bundle. (The harness's own secrets audit is separate, Phase 2.)
- **Cross-browser / device matrix.** Dot 006 checks one headless Chromium. Real
  Safari/Firefox/mobile behavior is not decided.
- **Build genuineness (dot 001).** Dot 001 checks that a deployable artifact
  exists, not that it came from a real build — a faked artifact is caught only
  downstream, by the deployed site failing dots 002–006. (Attack report A2.)

If any of the above matters for a given sale, it must be a human-approval step,
not an implied guarantee. Certificates state exactly what was checked.
