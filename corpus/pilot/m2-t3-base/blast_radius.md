# Blast radius — map 2 (content migration)

The verifiers are read-only: they read source/target JSON from the workspace and
(only in m05 HTTP mode) issue GETs to resolve internal links. No writes to any
CMS, sheet, or site; no destructive dots.

**Worst case:** during traversal the traveler writes an incorrect
target_items.json into the disposable workspace — caught by m01/m03/m04 before
any human promotes it. The migration to the *live* target (writing to the CMS or
site) is a separate, gated step outside this verify suite; this map certifies the
staged artifact, not a live overwrite.

Mitigation: keep the live-write step behind the Phase-2 destructive gate; ship
only the staged, verified content once the board is all-green.
