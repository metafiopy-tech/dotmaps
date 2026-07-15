# Fog — what map 2 (content migration) does NOT decide

- **Semantic correctness of the content.** Spot-hash proves the migrated fields
  are byte-for-byte the intended source values; it does NOT judge whether the
  source itself was right, whether copy reads well, or whether a price *should*
  have changed. Editorial correctness is a human-approval item.
- **Formatting / rendering fidelity.** Whether migrated HTML renders identically
  (fonts, spacing, embedded media) is not checked — only that fields are present,
  non-empty, and hash-equal on the sampled subset.
- **Coverage beyond the sample.** Dot m04 spot-hashes a deterministic sample
  (default 3 shared items), not every item — a full-corpus hash is a denser dot
  to add if a probe stalls here. Counts (m01) and field presence (m03) DO cover
  every item.
- **External links.** m05 checks INTERNAL links only; external URLs are out of
  scope (their liveness is not this migration's responsibility).
