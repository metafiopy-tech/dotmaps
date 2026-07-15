# Blast radius — smoke map

Worst case if the traveler misbehaves between checkpoints: it writes junk files
inside the run's scoped workspace directory. Nothing outside the workspace is
reachable (filesystem tool refuses paths that escape it; the `.dotmaps` board is
read-only to the traveler). No network, no accounts, no credentials.

Mitigation: none needed — the workspace is disposable.
