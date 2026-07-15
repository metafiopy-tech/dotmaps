# STATUS — Dot Maps v0.1 build

Phases are **strictly ordered** (spec §5). The renderer is caged in Phase 4 on
purpose — it's the most fun and least load-bearing component, the known failure
mode. Nothing below re-adds anything from the §2 subtraction list.

## Phase 1 — format + runtime — ✅ CORE PROVEN

| Phase-1 gate (spec §5) | State | Proof |
| --- | --- | --- |
| §4b schemas frozen | ✅ | `dotmaps/models.py` — Map/Dot, DotResult, event vocab |
| Orchestrator loop passes the trivial two-dot smoke map | ✅ | `tests/test_smoke_run.py`; `dotmaps run ../maps/map-smoke` → all_green |
| All three maps exist | ✅ | `map-deploy-verify-cloudflare` (9 dots), `map-content-migration` (5), `map-health-recert` (7) — all dots from the Ben domain |
| Harness completes a map end-to-end with a cheap model | ✅ **CLOSED — live** | **ollama driver** (`qwen2.5-coder:7b`, local, $0.00, no credentials): smoke map **all_green in 3 cycles / 44s**. The bet validated: dense dots + verifier-evidence-informed prompts make the weak model sufficient. (Anthropic `llm` driver also implemented; needs `ANTHROPIC_API_KEY`.) |
| Kill-and-resume works from the JSONL alone | ✅ | `tests/test_resume.py` — state derived by pure replay; interrupted run resumes |
| Full-manifest re-verification catches a planted regression | ✅ | `tests/test_regression.py` |
| A traveler edit of a verifier fails with a filesystem error | ✅ | `tests/test_mount_enforcement.py::test_docker_readonly_mount_rejects_writes` (docker `:ro`) + walls/scope tests |
| Verifier containers built + browser dots pass in-container | ✅ | `dotmap-deploy-verify-cloudflare:0.1.0` built; dots 006 (playwright) + 009 (lighthouse) run and return real results in-container |

`pytest -q` → **11 passed**.

**Live verifier results (the maps have teeth, on a real site):**
- **Map 1** vs live Ben site, in-container: 001-005 + 008 green; **006 FAILS** (3
  console 404s on the live site), **009 FAILS** (Lighthouse perf 75 < 80), 007
  gated (refuses to POST to prod without staging). The two failures are genuine
  findings about Ben's production site, not harness bugs — exactly the point.
- **Map 2** (content migration): happy-path example → **5/5 green**; a
  deliberately-broken migration (dropped item, dup slug, empty field, altered
  price, dangling link) → **all 5 dots fail correctly**.
- **Map 3** (health re-cert): 5/7 green vs live site, 2 browser dots pass
  in-container (same code as map 1's 006/009).

### Deliberately deferred within Phase 1 (not blocking, clearly marked)
- **llm traveler live run of map 1**: needs `ANTHROPIC_API_KEY` and a real
  `cloudflare` MCP server registered in `ToolBox`. The scripted driver already
  proves the loop mechanically. Wiring the cloudflare MCP is the next concrete step.
- **A currently all-green map-1 target for a Phase-3 probe**: the Ben live site
  legitimately fails 006 + 009, so probing "≥4/5 all-green" needs either a
  healthy target site, fixing those two issues, or moving the specific 404s to
  fog. This is a Phase-3 concern, correctly surfaced now.

## Phase 2 — safety + intake — ✅ BUILT & PROVEN

| Phase-2 gate (spec §5) | State | Proof |
| --- | --- | --- |
| Dry-run mode works | ✅ | `safety/dryrun.py` — mocking at the ToolBox seam; `tests/test_dryrun.py`: zero real mutations, intended actions journaled to `.dotmaps/dryrun.jsonl`, walls still raise. `dotmaps run --dry-run` |
| Destructive gating works | ✅ | `safety/gates.py` — destructive dots BLOCK by default; allowed only via dry-run, human confirm (CLI pause), or explicit `--allow-destructive`; a human "no" outranks the flag. `tests/test_gates.py` incl. end-to-end skip (run ends honestly red, action never executed) |
| Secrets audit passes (zero hits post-run) | ✅ | `safety/audit.py` + `dotmaps audit` — scans workspace *including* `.dotmaps/` logs; real run audits clean; planted tokens (anthropic/github/bearer/PEM/…) caught with **redacted** excerpts. `tests/test_audit.py` |
| Tester can parameterize map 1 via dialogue + approve board | ✅ mechanism | `compiler/intake.py` + `templates/*.yaml` (all three maps) — each question carries its "why"; board rendered as plain-English promises with destructive dots flagged + full fog; **approval required** (decline = nothing written); approval artifact recorded. `dotmaps compile`, `tests/test_compiler.py`. *An actual non-technical human hasn't run it yet — that's a person, not code.* |

`pytest -q` → **30 passed** (11 Phase-1 + 19 Phase-2).

## Phase 3 — certification — 🟡 MECHANISM BUILT + FIRST ARTIFACTS

| Piece | State | Proof |
| --- | --- | --- |
| Probe harness (weak traveler × N fresh runs, ≥4/5 rule) | ✅ | `dotmaps/certify.py` + `dotmaps probe`; `tests/test_certify.py` |
| **Live probe certification** (smoke map) | ✅ **5/5 all-green** | real weak traveler (ollama qwen2.5-coder:7b), 3 cycles every run — `maps/map-smoke/certification/probe_stats.json` |
| **Live probe certification — MAP 2** (real product map) | ✅ **5/5 all-green, CERTIFIED** | weak traveler, 2 cycles every run, 6m44s for all five fresh instances — `maps/map-content-migration/certification/probe_stats.json`. Map 2 has now passed both §4.5 gates (attack first-pass + probe); only Joe's adversarial pass remains for full certification. |
| Attack pass — first adversarial reports, all three maps | ✅ first pass | `maps/*/certification/attack_report.md` — model-generated; **Joe's pass pending** per spec §4.5 |
| Attack findings HARDENED in code | ✅ | **A1/B2/C1 config-tamper**: authoritative config in `.dotmaps/` (traveler-read-only), verifier precedence. **B1 source-rewrite**: `source_sha256` pinned at compile; tampered source = hard verifier error. `tests/test_attack_hardening.py` |
| **Map 2 LIVE all-green** (real product map) | ✅ | ollama traveler migrated the content end-to-end: **5/5 dots, 2 cycles, 1m54s, $0** — one traveler action, full-manifest pass ate all five dots. Independently re-verified; source byte-identical; secrets audit clean. |
| **B1 attack OBSERVED LIVE, then prevented** | ✅ | on map 2's first live run the weak model *innocently rewrote the source file* (added a `type` field) — the exact B1 attack. Detection (hash pin) refused to certify. Prevention added: `protect: true` template flag → `.dotmaps/protected_paths.json` → ToolBox walls refuse writes to verification inputs. Re-run: source untouched, all green. |
| Probe map 1 with a live traveler | ⛔ pending | needs cloudflare MCP + healthy target |
| Verifier containers, all four maps | ✅ | smoke 212MB, map2 221MB, map1/map3 2.23GB (playwright+lighthouse); map 3 full suite proven in-container (h05 catches the live 404s; h07 real Lighthouse 74) |

Robustness work the live weak model forced (all now tested):
- textual tool-call fallback parsing (small models emit JSON as prose)
- tool errors feed back to the model in-conversation; it corrects course
- a traveler crash is a failed attempt, never a dead run (rule 4 extended)
- prompts carry the verifier's last verdict on the dot (rule 2 working FOR the traveler)
- protected paths: verification inputs are wall-enforced read-only to the traveler

## Phase 4 — certificate + replay + sale — ⛔ CAGED ON PURPOSE
- `certificate/cert.py` — minimal HTML-from-event-log stub (schema wiring visible).
- `certificate/replay/renderer.py` — raises `NotImplementedError` by design.
  Invariant: deleting `certificate/replay/` must lose nothing but pictures.

## Immediate next actions (everything below needs credentials or a human)
1. **Register a real `cloudflare` MCP server** in `ToolBox` so the traveler can
   deploy — the only thing between map 1 and a live traversal + probe.
   (`ANTHROPIC_API_KEY` is now only needed for the claude *fallback* traveler;
   the primary ollama traveler is live and certified.) Mandatory first run =
   `--dry-run`, per the safety layer.
2. Have a real non-technical tester run `dotmaps compile` on map 1 (the human
   half of the Phase-2 intake gate).
3. Joe's adversarial pass over the three attack reports (spec §4.5 requires it;
   the model-generated first pass found and closed 3 criticals, one live).
4. A healthy target site for map 1's probe — the Ben live site genuinely fails
   006 (3 console 404s) and 009/h07 (Lighthouse 74–75 < 80). Fixing those two
   issues on the Ben site would ALSO make it the healthy target.

### Done since first pass
- ✅ Maps 2 (content-migration) and 3 (health-recert) authored + proven runnable.
- ✅ Map-1 verifier Docker image built (`python:3.11-slim-bookworm` + playwright
  1.48 + lighthouse 12.2); dots 006 + 009 return real results in-container.
- ✅ Map 2 teeth verified (broken migration fails all 5 dots).
- ✅ **Phase 2 safety + intake built & proven** (dry-run, gates, secrets audit,
  compiler dialogues for all three maps) — see Phase-2 table above.

---

# EXPERIMENT LAYER — the Instrument Experiment (instrument_experiment_spec.md)

Added on top of the harness; zero harness-semantics changes. Three
pre-registered bets: B1 weak-probe-as-instrument, B2 ladder-floor dual
certificate, B3 adversarial certification. Sequential execution with an early
kill (spec §5): Stage-0 ambush pilot BEFORE building anything beyond the
corpus operators.

| Build item | State |
| --- | --- |
| `dotmaps corpus` — generator, 6 operators, integrity checks | ✅ built; 10 tests (`test_corpus.py`) |
| Wilson bounds in probe stats (item 3) | ✅ `certify.wilson`; probe stats now carry `wilson_95`, `pass_rate`, `cycles_to_green_median` |
| Stage-0 pilot corpus (4 map-2 variants) | ✅ built + integrity-passed (T1=3 dots, T2=5, T3=5, T4=9); all verifiers fail-on-broken AND pass-on-solved |
| Stage-0 pilot runs (4 × N=5, 7B instrument) | ✅ COMPLETE — **pre-registered EARLY KILL** (all tiers 5/5 @ ~2 cycles; zero separation; the 7B instrument saturates map-2). Full verdict + data: `corpus/pilot_report.md` |
| `dotmaps ladder` / `dotmaps sweep` / attack harness / analysis | ⛔ CANCELLED per the kill rule — the sweep does not get built on this rig |
| Stage-0b weak-rung re-pilot (llama3.2 3B, user-approved, `corpus/pilot2_registration.md`) | ✅ COMPLETE — **FLOOR-OUT** (T3 anchor 0/5, zero dots; grid skipped per anchor-first clause). Map-2's instrument window is EMPTY at tested rungs: 7B saturates, 3B floors. H1 unmeasured, not falsified. Bonus: emergent malicious compliance observed live (3B fabricated a counts-match claim; rule 4 held the board red 30 cycles × 5 runs); prompts now absolute-path-free (weak-traveler transcription hazard). |
| Tool-level walls (Stage-0 hardening) | ✅ `mcp_required` supports single-tool grants; map 2 v0.1.1 drops `filesystem.delete` from its action space (move-mode delete finding, `corpus/pilot_interim_notes.md` finding 3) |
| **Final three tracks (2026-07-15) — COMPLETE** | ✅ **Run 005 (frontier learner, $0.50): v0 SIGNAL MET** — 4 discriminating primitives, R1-clean grown map (zero circular, first ever), probe 5/5, nonzero R3 overlap; new bottleneck = harness observation window (~120-char journal pane). ✅ **map-seq** built + HARDENED; assay: 7b 0/5 dots, 14b 3/5 dots (zero variance) → no all-green window, **H1 closed at owned rungs**; dots-eaten separation banked for any future registration. ✅ **Packaging**: `dotmaps attack` (4 codified attacks; map-2 + map-seq HARDENED), `dotmaps replay`, README. Suite **71 passed**. Full addendum in `REPORT.md`. |
| **"Run everything" directive (2026-07-14/15) — COMPLETE, tree exhausted** | ✅ Grow arc: 4 runs, environment KILL at owned rungs (7B reward-hacked→gated→fogged out; 14B move-selection collapse ×2 incl. post-ergonomics) — mechanics held every run, learners below the claims-with-checks floor; full log `grow/RUNS.md`. ✅ Window assay: qwen3:8b = 0/5 (ate exactly 1/5 every run — floor-adjacent), 14b = 5/5 (saturates) → **no owned rung in window → H1 on map-2 CLOSED as unmeasurable-with-owned-instruments** (`corpus/pilot_report.md` addendum). No questions remain open under pre-stated rules. Next moves are all NEW decisions: frontier-model learner for the POKE loop; sequential task family for H1; product B2/B3 packaging. |
| **POKE Loop v0 (ACTIVE track, Joe's priority change 2026-07-14)** | ✅ Built + wheel-tested (`dotmaps/grow/`): rule banking (declarative steps+predicate specs, confirm-by-fresh-seed-replay, template-compiled read-only check scripts — learner never writes verifier code), phase clock v0 (K=15/ε=1, novelty series logged), FORAGE with fog-not-drop, METABOLIZE → grown_map.yaml (invariant/mutation dots + observed-ordering deps), `dotmaps grow` runner (budgeted, journaled), `dotmaps readout` (R1 automated, R3 scaffold). Both named traps have regression tests (self-referential banking cannot confirm; wall-facts grow no dots). Directive frozen goal-free in `grow/DIRECTIVE.md`; cold seed = source export + protection wall ONLY (no compile outputs — answer-key leak). Suite **67 passed**. Live run 001 (qwen2.5-coder:7b learner) launched. `dotmaps new` cartographer flow DEFERRED per handoff. |
| Real MCP wiring (B1, product track resumed 2026-07-14) | ✅ Generic streamable-HTTP MCP client (`runtime/mcp_client.py`, stdlib-only) + built-in GET-only `fetch.get`. Bindings live user-side in `~/.config/dotmaps/servers.json` (URL + token env NAME; secrets never stored). ToolBox forwards ONLY whitelisted remote tool schemas — 4 granted tools from a 2,500-tool server cost 4 schemas. Live handshake vs `mcp.cloudflare.com` verified (clean 403 without token; codemode=false chosen deliberately: Code Mode's `execute` = arbitrary-endpoint JS = wall bypass). Suite 57. **`dotmaps connect <map>` shipped** (user-requested): the harness owns the credential loop — reads the map's required servers, shows per-server setup hints (`mcp_setup` in map.yaml + built-in registry), takes the token via hidden getpass paste, writes it chmod-600, and VERIFIES with a live MCP handshake immediately; bad pastes get instant feedback and never linger on disk. Map-1 carries its cloudflare hint. User runs `dotmaps connect maps/map-deploy-verify-cloudflare` in their own terminal when ready. |
| Attempt observability | ✅ traveler tool-call journal recorded on `dot_attempted` events |

Suite: **67 passed** (41 harness + 10 corpus). The docker mount test now skips
honestly when the docker daemon is unresponsive (was a 2-minute timeout-failure
that read like an enforcement regression; daemon was hung on this machine).
