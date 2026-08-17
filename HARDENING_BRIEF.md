# HARDENING BRIEF — the audit response ("the receipt must never lie")
## Claude Code mission. Branch queen-hardened off queen-os. Same laws.
## Source: Dot_Maps_Technical_Product_Diligence_Audit_2026-08-17 (commit the
## docx-derived findings as docs/audit-2026-08-17.md first, verbatim summary).
## Order is priority order. Commit per gate. No push. queen-os does NOT merge
## to main until H1–H7 are green.

### H1 — Chat proof boundary (the thesis bug; everything else waits)
No user-visible asserted answer may exist unless: model process succeeded
(subtype==success) AND answer.json parses AND the proposed predicate/value
is MECHANICALLY EXECUTED and passes AND the rendered reply is DERIVED from
the checked result (deterministic renderer; free text may add color but can
never contradict or precede the checked fact). On any failure: honest
"couldn't verify that" reply + failed trip. 
TESTS (from audit, verbatim): valid path/predicate but false value → no
asserted answer · answer text contradicts true structured fact → renderer
prevents contradiction · subtype!=success but answer.json exists → work
order failed.

### H2 — Work-order isolation (treat Claude Code as untrusted execution)
Sandbox-runner abstraction: disposable workspace mount, EMPTY allowlisted
env (explicit per-tool credential injection only), no host $HOME access,
network deny-by-default with explicit egress grants, CPU/mem/turn/wall
budgets. Platform: use container (Docker) when available; degrade to a
restricted-env + path-guard mode with a LOUD banner "unsandboxed — dev
only" when not. Remove the word "sandbox" from any comment where cwd is
the only boundary.
TEST: planted SECRET_TOKEN in parent env → child env lacks it.

### H3 — SafeFetcher (one egress door for Watch + traveler fetch)
Block: localhost/127.0.0.1/::1, RFC1918, link-local, cloud metadata IPs,
redirect-to-private, DNS-rebind (resolve then pin). Public-IP allow only;
scheme http(s) only; size + timeout caps.
TESTS: full audit matrix (each blocked class) → all refused.

### H4 — Concurrency-safe evidence journals
Process-safe append (file lock + fsync), unique monotonic seq, crash-safe.
Keep hash-chained JSONL as evidence format; add SQLite WAL projection for
product state reads if needed (evidence stays JSONL).
TEST: two processes append 1,000 events → chain linear, unique, complete.

### H5 — Statistical honesty in certification
Deterministic replay stops wearing a confidence interval: report
"consistency: 20/20 deterministic replays" for the stability regime. Wilson
intervals only where probes are INDEPENDENT samples (fresh randomized copy
per probe; isolate mutations — skill A can never mutate the seed used by
skill B). Certificates carry regime label: deterministic-consistency vs
sampled-reliability. Update UI/paper wording accordingly.
TESTS: mutation isolation · reorder skill files → identical certificates.

### H6 — Re-cert semantics + formation context
Freshness resets ONLY after passing re-cert; failure → convicted/demoted +
trip (never a success trip). Stability actually modulates recheck interval.
Every skill card gains formation_context (dataset/site/schema/tool
versions) + invalidation conditions; route refuses stale-context skills
until re-cert.
TESTS: due skill fails oracle → convicted, no reset · context fingerprint
change → route refuses until re-cert.

### H7 — Identity hardening
Persistent IDs = hash of full normalized identity (readable slug as prefix
only). TESTS: same host/different Watch path → distinct watcher IDs ·
long same-prefix questions → distinct chat map IDs.

### H8 — Adapter seam for Claude CLI
queen/runner_adapter.py: version-pinned contract (flags, output fields),
compatibility self-test at init, graceful fail message on drift. Product
logic never touches CLI field names directly.

### H9 — Egress + data labels in UI
Before any frontier submission, chat shows: model will be called · sources
to be read · network destinations · stored-in-record. Per-action egress
label in Run tab. (Audit Q40/Q51.)

### H10 — Positioning + paper corrections
docs/paper updates: "certified" defined as verifier-relative everywhere ·
12x stated as campaign result pending independent replication · repo age
stated honestly (instrument = 2026; ecosystem ideas earlier) · prior-art
section names Voyager/PCC/FSRS first (audit Q52 language) · claim-status
three-column table added · assure grows claims: chat proof boundary
(H1 tests), SSRF matrix green, env isolation, concurrency test.

### ACCEPTANCE
All audit regression tests green · assure expanded and ALL GREEN · suite
green · flight log section "Hardened: the audit response" listing each
finding → fix → test · THEN queen-os+hardened merges to main.
