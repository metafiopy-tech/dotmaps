# Blast radius — map 1 (deploy-verify-cloudflare)

Worst-case damage if the traveler misbehaves between checkpoints, per spec §4.3.
If any worst case here were unacceptable and unmitigated, the map would not ship.

| Action surface | Worst case | Mitigation |
| --- | --- | --- |
| Cloudflare deploy (dot 001→002) | Bad build promoted to production, site broken for visitors | Workers deploys are **versioned**; rollback to the prior version is one action. Deploy dot is reversible, so it ships. Phase-2 gating adds a staging deploy first. |
| Signup form POST (dot 007, `destructive: true`) | A junk/test lead written to the live Google Sheet + a real Web3Forms email to the business | Verifier **refuses to POST to production** unless `form_staging_base` is set (or `allow_prod_form` explicit). Test payload is clearly marked synthetic. Phase-2 safety layer owns this gate properly. |
| DNS (dot 008) | none — read-only lookup | n/a |
| HTTP GETs (dots 002–005) | none — read-only, rate-limited to the sitemap page count | n/a |
| Filesystem (workspace) | Junk files in the disposable run workspace | Scoped filesystem tool; `.dotmaps` board read-only; nothing outside workspace reachable. |
| Secrets | Token leak into workspace/logs/replay | Runtime never reads raw credentials; all auth via MCP OAuth. Phase-2 secrets audit greps workspace+logs for zero token hits after a real run. |

**Net:** the only irreversible-ish surface is the form write, and it is gated to
staging by default. Deploys are reversible by construction. Map ships for v0.1
under these mitigations; production form + auto-deploy without confirm is a
Phase-2 gate, not a Phase-1 assumption.
