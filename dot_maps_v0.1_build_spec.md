# Dot Maps — v0.1 Build Spec (Cowork Handoff)

*Verified task completion for agents: compile a goal into checkable dots, let any cheap agent eat them, prove it with a watchable certificate.*

Status: pre-build. This is the NARROW cut. The scope discipline in §2 is the product decision — everything cut from v0.1 was cut deliberately, not forgotten. Do not re-add.

---

## 0. One-paragraph thesis (context for the builder)

Agents fail commercially not because models are weak but because completion is unverifiable — users re-check everything, which erases the value. This product inverts the reliance: the goal is compiled into a manifest of externally verifiable predicates ("dots"), a cheap agent traverses them inside a constrained harness, a sovereign verifier that the agent cannot touch decides when it's done, and the run is rendered as a watchable pixel replay that doubles as a completion certificate. Expensive cartographer, cheap traveler: frontier-model compilation once per map, open-model traversal per run, margins live in the map.

---

## 1. v0.1 deliverable (definition of done)

One domain. Three maps. One traveler agent. One paying stranger.

**Domain:** small-business website deploy + verify (the domain already personally traversed via the Ben Sluzas build: Cloudflare Workers, Google Sheets integration, Web3Forms, DNS/custom domain).

**The three maps:**
1. **Deploy + verify a static/SSR site to Cloudflare Workers** — dots: build succeeds, deploy returns 200, every page in sitemap loads, no console errors, all images resolve, forms submit and deliver, lighthouse score ≥ threshold, DNS resolves if custom domain configured.
2. **Content migration + verify** — move page/product content from source (sheet, old site, docs) to target site; dots: item counts match, no duplicate slugs, every migrated field non-empty, spot-hash comparisons source↔target, all internal links resolve.
3. **Site health re-certification** — the E4 heartbeat as a standalone map: re-run map 1/2's verifier suite on an existing deployment on demand or on schedule; dots are the same checks, run against production.

**Definition of done for v0.1:** all three maps pass their own certification (see §5 probe), one full run each recorded as replay artifacts, one person who is not Joe and not a friend pays money for a run or a map.

---

## 2. Non-goals for v0.1 (the subtraction list — enforce it)

- NO marketplace, NO map submissions from others, NO map library beyond the three.
- NO "automate anything" intake. Intake supports the one domain only.
- NO custom API integrations built in-house. All tool access via existing MCP servers; if a needed connector has no MCP server, the map is out of scope for v0.1.
- NO Belief Engine integration. This is a standalone thin repo (~2–3K lines target). Borrow *patterns* (critic-style attack stage, receipt-style certificates), never import the 82K-line engine.
- NO research experiments (E1–E3, E5 from grounded_convergence_spec.md). Decoupled. The product uses explicit verifiers, not internal signals. Exception: E4's frozen-vs-tethered logic ships as map 3.
- NO payment infrastructure beyond a Stripe link. NO auth system beyond what MCP OAuth flows provide.
- Pixel renderer is Phase 4, LAST. A working verifier with an ugly log beats a beautiful maze with no teeth.

---

## 3. Architecture — the five harness rules (constitutional; every component must satisfy all five)

1. **Compile before launch.** No agent starts until the goal exists as a manifest of verifiable predicates. No dots, no run.
2. **The board remembers, not the agent.** All progress state lives in the workspace + scoreboard files. Agent context is disposable; any run can be killed and resumed by a fresh agent with zero context loss.
3. **Walls: whitelisted tools only.** The agent's action space = the map's declared MCP servers + scoped filesystem. Illegal actions are absent, not discouraged.
4. **Sovereign verifier owns termination.** A separate process re-runs the FULL manifest every cycle (regressions detected as loudly as progress). Run ends only on all-green or budget exhaustion. The agent cannot end its own run and its claims of completion are ignored.
5. **Read-only scoreboard.** Agent has write access to the workspace, read-only access to manifest + verifier code + scoreboard. Enforce at the filesystem/permissions level, not by instruction.

---

## 4. Components (build in this order)

### 4.1 Map format (`map.yaml` + verifier repo) — Phase 1
A map is a git repo:
- `map.yaml`: name, version, domain; list of dots `{id, statement (plain English promise), verifier (script path), depends_on[], destructive: bool}`; required MCP servers; budget (max cycles, max tokens/$); traveler config (model, temperature).
- `verifiers/`: one script per dot. Each exits 0/1, runs in seconds, is mechanical (no LLM-judge dots in v0.1 — if a check needs an LLM opinion, redesign the dot or move that item to the map's declared **fog**).
- `fog.md`: explicit list of what this map does NOT decide (human-approval items). Rendered honestly to the user.
- Environment pinning: verifiers run in a container (Dockerfile in repo) so a dot verifies identically on any machine. **This portability is the moat; treat it as a first-class requirement, not packaging.**

### 4.2 Runtime (the harness) — Phase 1
- Loop: `select uneaten dot (respecting depends_on) → construct minimal prompt (dot statement + relevant workspace state) → agent acts via whitelisted MCP tools → yield → verifier re-runs full manifest → update scoreboard → repeat`.
- Scoreboard: append-only JSONL event log (`dot_eaten`, `dot_regressed`, `cycle_complete`, `budget_tick`) + current-state summary. The event log later feeds both the replay and the certificate.
- Traveler: model-agnostic client; v0.1 targets one open/cheap model via API + one frontier model as fallback config. The bet to validate: dense dots make the cheap model sufficient.
- Kill/resume: `run --resume` must work from scoreboard alone (rule 2 test).

### 4.3 Safety layer — Phase 2, BEFORE any real-account run
- **Destructive-middle protection:** any dot flagged `destructive: true` runs against staging first; production actions must be reversible (deploy = versioned rollback available) or gated behind an explicit human-confirm pause in the run.
- **Dry-run mode:** full traversal with all mutating MCP calls mocked; mandatory first run for every new user/map pairing.
- **Secrets:** runtime never reads raw credentials; all auth lives in MCP server OAuth flows. No tokens in workspace, scoreboard, logs, or replays. Audit this explicitly.
- **Blast radius doc per map:** one section in map.yaml listing worst-case damage if the agent misbehaves between checkpoints, and the mitigation. If worst case is unacceptable and unmitigated, the map doesn't ship.

### 4.4 Compiler (intake dialogue) — Phase 2
- v0.1 compiler is domain-templated, not general: each of the three maps has a parameterization dialogue (source? target? domain name? which forms?) that fills a manifest template. This is a conversation flow, not a form — but it is NOT open-ended goal compilation. General compilation is v0.2+.
- Output shown to user BEFORE run: the full dot list as plain-English promises + the fog. User approves the board, then runs.

### 4.5 Attack + probe certification (internal QA gate) — Phase 3
Every map must pass before it's sellable:
- **Attack:** adversarial pass (frontier model + Joe) attempting malicious compliance — construct an output passing every dot while failing the real goal. Each finding either becomes a new/hardened dot or is documented in fog. Record the report; note it proves gaps exist, never that none remain.
- **Probe:** run the WEAK traveler on a fresh instance 5 times. Certification requires ≥4/5 all-green within budget. Stall points → decompose that stretch into denser dots and re-probe.
- Certification artifacts (attack report + probe stats) ship with the map.

### 4.6 Certificate + replay — Phase 4 (last)
- Certificate: signed summary generated from the event log — dots passed (n/n), retries, regressions caught, cost, duration, map version + verifier hashes. Plain HTML first.
- Replay: pixel-art render of the event log — board as maze, dots labeled with their plain-English statements, sprite traversal, regression flickers, all-green stamp. Export as GIF/webm. This is the marketing surface and the trust artifact; build it only after certificates are already real.
- Wording rule for anything user-facing: certificates state exactly what was checked ("34/34 declared checks passed"), never blanket guarantees ("your site is perfect"). Scoped claims only — this is the liability posture.

---

## 4b. Code architecture — how to attack it

**Language & stack:** Python 3.11+ (matches the existing ecosystem; borrow patterns from Belief Engine, never imports). Verifiers are standalone bash/python scripts. Containers via Docker. No framework for the harness — it's a loop, a state file, and subprocesses; keep it boring.

**Repo topology — two kinds of repo, strictly separated:**

```
dotmaps/                      # THE HARNESS (one repo, the product's engine)
├── dotmaps/
│   ├── compiler/             # intake dialogues → manifest (Phase 2)
│   │   └── templates/        # per-map parameterization flows
│   ├── runtime/
│   │   ├── orchestrator.py   # the outer loop; owns lifecycle, budget, termination
│   │   ├── traveler.py       # agent client: model API + MCP tool registration
│   │   ├── selector.py       # pick next uneaten dot (depends_on-aware)
│   │   └── prompt.py         # minimal per-dot prompt construction
│   ├── verifier/
│   │   ├── runner.py         # executes full manifest in container, collects results
│   │   └── contract.py       # dot result schema + timeout handling
│   ├── scoreboard/
│   │   ├── log.py            # append-only JSONL writer (events)
│   │   └── state.py          # derived state.json from replaying the log
│   ├── safety/
│   │   ├── dryrun.py         # MCP call mocking layer
│   │   └── gates.py          # destructive-dot staging/confirm pauses
│   └── certificate/
│       ├── cert.py           # HTML certificate from event log
│       └── replay/           # pixel renderer (Phase 4, isolated, deletable)
├── tests/
└── pyproject.toml

map-<name>/                   # A MAP (one repo per map, consumed by the harness)
├── map.yaml                  # manifest: dots, deps, MCP requirements, budget, fog ref
├── verifiers/
│   ├── 001_build_succeeds.sh
│   ├── 002_deploy_200.py
│   └── ...                   # one script per dot, numbered = dot id
├── fog.md
├── blast_radius.md
├── Dockerfile                # pinned verifier environment (the portability moat)
└── certification/            # attack report + probe stats (added at Phase 3)
```

The separation is architectural, not organizational: the harness never contains task knowledge; a map never contains execution logic. A map is data + checks. That's what makes maps sellable artifacts and the harness reusable.

**The five rules, enforced in code (not by instruction):**
- *Rule 3 (walls):* traveler.py registers ONLY the MCP servers listed in map.yaml as its tool set. The whitelist isn't a filter over available tools — un-listed tools are never registered, so they don't exist in the agent's action space.
- *Rule 5 (read-only scoreboard):* enforced by mounts, not politeness. The agent subprocess runs with the workspace mounted read-write and manifest/verifiers/scoreboard mounted read-only (same pattern as this very sandbox's read-only /mnt/skills). A traveler that tries to edit a verifier gets a filesystem error, not a scolding.
- *Rule 4 (sovereign verifier):* orchestrator.py is the only process that can write the terminal event. verifier/runner.py executes in its own container with the workspace mounted read-only — the verifier can see everything and touch nothing. Agent output claiming "done" is never parsed for control flow.
- *Rule 2 (board remembers):* the JSONL event log is the single source of truth; state.json is always derivable by replay. `--resume` = replay log → rebuild state → continue. If resume needs anything from agent context, that's a rule-2 violation and a bug.

**Core schemas (freeze these first — everything else is refactorable, these are load-bearing):**

```yaml
# map.yaml (abridged)
name: deploy-verify-cloudflare
version: 0.1.0
mcp_required: [cloudflare, filesystem, fetch]
budget: {max_cycles: 40, max_usd: 2.00}
traveler: {model: <cheap-default>, fallback: <frontier>}
dots:
  - id: "007"
    statement: "Every page in the sitemap returns HTTP 200"
    verifier: verifiers/007_pages_200.py
    depends_on: ["004"]
    destructive: false
```

```json
// scoreboard event (one JSONL line)
{"ts": "...", "cycle": 12, "event": "dot_eaten", "dot": "007",
 "evidence": "34/34 pages returned 200", "attempt": 2}
// event types: run_started | cycle_started | dot_attempted | dot_eaten
//              | dot_regressed | budget_tick | run_ended{reason: all_green|budget|killed}
```

```
# verifier contract
- invoked as: <script> --workspace /ws (read-only mount)
- exit 0 = pass, exit 1 = fail, exit 2 = error (treated as fail, flagged)
- stdout: single JSON line {"dot": id, "pass": bool, "evidence": "<one human sentence>"}
- hard timeout 60s; no network except domains declared in map.yaml
```

**The orchestrator loop (the whole runtime, honestly):**

```python
def run(map, workspace):
    board = Scoreboard.load_or_init(workspace)          # rule 2: resume = replay
    while board.budget_remaining(map.budget):
        results = Verifier.run_full_manifest(map, workspace)   # rule 4: FULL board,
        board.reconcile(results)                               # every cycle (catches regressions)
        if board.all_green(): return board.end("all_green")
        dot = Selector.next_uneaten(board, map.dots)           # deps-aware
        Traveler.attempt(dot, map, workspace)                  # rules 3+5 enforced by mounts/registration
        board.log_attempt(dot)
    return board.end("budget_exhausted")
```

Everything else — compiler dialogues, certificates, the frog — is peripheral to this loop. If the loop plus mounts plus the verifier contract are right, the five rules hold mechanically and the product's trust claim is structural. Build and test THIS first with a trivial two-dot map (create a file / file contains X) before touching Cloudflare.

**Renderer isolation:** certificate/replay/ consumes only the JSONL log. Zero imports from runtime. It must be possible to delete the entire directory and lose nothing but pictures — that's the test that it stayed peripheral.



**Phase 1 (format + runtime):** schemas in §4b frozen; the orchestrator loop passes the trivial two-dot smoke map; map 1 exists; harness completes it end-to-end on a test site with a cheap model; kill-and-resume works from the JSONL alone; full-manifest re-verification catches a deliberately planted regression; a traveler attempt to edit a verifier fails with a filesystem error (mount enforcement proven, not assumed).
**Phase 2 (safety + intake):** dry-run mode works; destructive gating works; secrets audit passes (grep the workspace/logs for tokens after a real run = zero hits); a non-technical tester can parameterize map 1 via the dialogue and approve the board.
**Phase 3 (certification):** all three maps pass attack + 4/5 probe; certification artifacts produced.
**Phase 4 (certificate + replay + sale):** replay GIF renders from a real event log; landing page = the GIF + the three map pages (each showing its board + fog + price) + Stripe link; first stranger transaction.

Sequencing note: phases are strictly ordered. The renderer (4.6) is deliberately caged in Phase 4 — it is the most fun and least load-bearing component, which is exactly the known failure mode.

---

## 6. Open questions for the build (decide during, don't block on)

- Pricing shape: per-run vs per-map-license vs run+heartbeat subscription (map 3 is naturally recurring — likely the revenue spine).
- Traveler hosting: user brings their own agent/keys vs hosted runs (hosted = simpler UX, adds cost + liability; v0.1 can be "bring your key" with hosted as fast-follow).
- How much of the Ben Sluzas build generalizes: extract its acceptance checks into map 1's verifier suite as the starting dot set.
- Name. "Dot Maps" is a placeholder.

## 7. Known risks (acknowledged, not blocking)

- **Certificate liability:** mitigated by scoped wording (§4.6) + refund policy written before first sale.
- **Map rot:** mitigated structurally by map 3 (heartbeat re-certification) — rot becomes a product feature.
- **Convenience-value erosion** (labs making agents one-click): the durable value is verification, not setup ease; all messaging leads with "provably done."
- **Solo-founder scope creep:** the non-goals list in §2 is the control. Marketplace/library/general-compiler unlock ONLY after a stranger pays.

## 8. Restatement for future-you

You are not building an agent. You are building the board: the thing that makes any agent's work checkable, watchable, and provable. The agent is deliberately the most replaceable component in the system. Three maps, one domain, boringly bulletproof, one paying stranger — then, and only then, the shelf.
