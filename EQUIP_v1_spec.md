---
tags: [dot-maps, spec, skill-acquisition, equip]
status: SPEC — no code until gates defined here are accepted
date: 2026-07-31
depends_on: [NORTH_STAR.md, dot_maps_v0.1_build_spec.md, instrument_experiment_spec.md, docs/case-study-closing-procedure.md]
---

# EQUIP v1 — The Self-Equipping Faculty
## Novel-task skill acquisition with a certifiable manifest

*One sentence: when an agent hits a task nobody decomposed for it, it grows its own map, banks what it learned as certified skills, and declares them in a manifest — so the next agent starts where this one finished.*

This spec covers ONLY the acquisition faculty. The Body/queen dispatch layer is explicitly out of scope (blueprints exist; build after this). Compiler tweaks are out of scope (frozen at T2 rubric as published). Robotics is in the Parking Lot where it belongs.

---

## 0 · What already exists (do not rebuild)

| Piece | Where | State |
|---|---|---|
| Bottom-up growth loop (POKE→FORAGE→METABOLIZE→SANDBOX) | NORTH_STAR.md | Doctrine, partially proven |
| A learner growing a certifiable map from nothing | Run 005 (`runs/grow-005`) | **Proven once**: claude-sonnet-5, no task description, no oracle, 4 banked primitives, 5/5 probe-cert, $0.50, signal MET |
| The convictions | Runs 001–004, H1 instrumentation kill | Published |
| The known cap | Bottleneck ladder | Harness observation window (~120-char journal truncation) capped the frontier learner — **window fix is prerequisite #1** |
| Frozen weak traversal | harness + ollama driver | 7b smoke map all_green, 44s, $0.00 |
| Compiler (plain English → predicate map) | docs/try.html + frozen T2 rubric | Live, published, F1–F4 corrected |
| Capabilities manifest concept | docs/instrument.html §5 | Schema sketched, not implemented |
| Skill auto-extraction pattern | Hermes integration target (standing) | Pattern identified, not built |
| Certification statistics | Wilson intervals, θ, re-cert on version change | In production |
| Five-governor loop + technical review | session 2026-07-29 (chi-null churn threshold, τ error-budget, oracle gating, Whittle shelf re-checks, quarantine-before-adoption) | Doctrine, folded into §2.1a/2.3a-c |

## 1 · The claim (what "extraordinary" means, falsifiably)

**C1:** An agent that banks skills from one traversal completes a *related but distinct* novel task cheaper and/or more reliably than an identical agent starting cold. Skill acquisition must show up as a measurable delta on the second task, or it's bookkeeping, not learning.

**C2:** Banked skills are *certifiable objects* — each carries its own interval, its own provenance, and can be revoked. A manifest of certified skills is therefore a trust document, not a brag sheet. (This is the piece nobody else has: Hermes banks skills, nobody certifies them.)

## 2 · The mechanism — EQUIP = grow + BANK + MANIFEST

The existing loop grows the map. Two new stages make it compound:

### 2.1 GROW (exists — NORTH_STAR mechanism, unchanged)
POKE the environment, harvest primitives with free local checks. FORAGE only when marginal-rules-per-poke hits zero. METABOLIZE harvested rules into a candidate map. SANDBOX under local-check pressure. Output: a grown map + a journal of what was tried.

**§2.1a — The growth abort governor (H9, operationalized).** Per frontier predicate, the growing agent's failures are typed by stage category (import / check-authoring / selection / timeout / wrong-output — typed categories FIRST, embeddings only if categories fail to separate; 10× cheaper, nothing to pin). Three verdicts on the failure trajectory: **WALL** (same mode repeating → shelve with re-check schedule), **CHURN** (variance without net displacement → shelve; the noisy-TV case naive persistence would grind on), **DIRECTIONAL** (failure mode migrating with net displacement → keep spending even at zero success rate; learning is happening under a flat score). The churn threshold is not a tuning knob: null hypothesis is a same-length random walk (expected directionality ≈ c_d/√W; permutation test in practice). Confound control, mandatory: swap the diagnoser once per run batch — if drift doesn't survive the swap, the signal was the describer, not the described.

### 2.2 BANK (new)
After a traversal (grown or assigned), a **skill extractor** mines the journal for reusable units. A skill is NOT a memory blob. A skill is:

```yaml
# skills/<name>/SKILL.yaml
name: sheets-append-via-jwt
trigger: predicates it can satisfy        # e.g. [sheet.row_appended, auth.jwt_valid]
method: frozen procedure + tool calls     # the how, pinned
requires: {mcp: [sheets], tools: [...]}   # its own sub-manifest
provenance:
  banked_from: run-id                     # which traversal produced it
  banked_by: model@sha                    # who learned it
  cost_to_acquire: $x.xx
certificate:
  status: candidate | certified | shelved | revoked
  theta: computed                         # NOT a global constant — see §2.3a
  wilson: [lo, hi]                        # from ITS OWN probe runs
  n: trials
  oracle_gate: passed                     # certifier sanity-checked BEFORE grading (§2.3b)
  recert_on: [env_version, tool_version]  # drift triggers (F-lineage: re-cert on change)
decay:
  last_used: date                         # FSRS-style: unused skills demote before rotting
  stability: score
  shelf_recheck: scheduled                # SHELVED is not a grave — Whittle-style staleness
                                          # schedule re-probes abandoned skills (§2.3c)
```

**The certification rule (non-negotiable, F3 lineage):** a banked skill enters as *candidate*. It becomes *certified* only by its own probe runs — the frozen weak instrument attempts the skill's trigger predicates N times; Wilson lower bound ≥ θ certifies. **Per-skill certification, not whole-run** (F4 lesson: length must not masquerade as quality). The skill certifier runs frozen rules, same as every verifier in the pipeline.

**§2.3a — θ is per-skill, not global (τ error-budget result, 2026-07-29 review).** Certification threshold is a function of invocation frequency and failure cost: θ = clip(1 − B/(f·c), θ_min, θ_max). A skill called ten thousand times cheaply may certify at θ_min; a rare, irreversible skill sits near θ_max and may be marked *never-satisfice* (human sign-off required). One number for all skills was the same mistake as one pass line for all map lengths (F4). The pre-registered global θ=0.70 survives only as θ_min, the floor.

**§2.3b — Certify the certifier (G1 lineage, non-negotiable ordering).** Before any probe run updates a certificate, the certifier passes structural oracle-validity checks (does the verifier terminate, discriminate on planted pass/fail pairs, return stable verdicts on identical input). Proven mechanically in the five-governor demo: a broken oracle produces scattered failures indistinguishable from an unlearnable skill — downstream, the misdiagnosis is confident and wrong. Oracle gate runs FIRST, always. No certificate math on an ungated verifier.

**§2.3c — SHELVED is not permanent (the permanence hole, patched).** A skill or frontier predicate abandoned as a wall gets a staleness-scheduled re-probe (restless-bandit/Whittle framing: cheap periodic checks whose frequency decays but never hits zero). A wall at tick 100 may not be a wall at tick 5,000 — new tool, promoted dependency, better context. Same FSRS machinery, pointed at abandonment instead of retention. Without this the loop does "giving up permanently" and calls it satisficing.

**The extractor is a verifier too.** It runs under a frozen rubric (what counts as a reusable unit: satisfies ≥1 predicate, method is replayable, requires-list is complete). No unfrozen judgment calls — we learned this Wednesday.

### 2.3 MANIFEST (new)
The colony-level ledger every agent reads before touching a task:

```json
{
  "skills": [{"name": "...", "trigger": [...], "certificate": {...}}],
  "coverage": {"predicate → best certified skill" },
  "frontier": ["predicates with no certified skill"]   // H1's target list
}
```

Three consumers: **agents** (can I satisfy this predicate with a certified skill, or must I grow?), **the queen, later** (staffing = matching manifest coverage to map predicates), **humans** ("what can this thing actually do" — grandpa's question, answered by a document with intervals on it).

### 2.4 The novelty gate (H3, operationalized)
When a task arrives, route each predicate:
- **Covered** — a certified skill's trigger matches → execute the skill. Deterministic path.
- **Frontier** — no certified match → GROW on that predicate. Ambiguous path.
- **Promotion criterion** (H3's open question, now concrete): a grown solution promotes to the deterministic path when its banked skill certifies. Demotion: certificate revoked on drift or failed re-cert → predicate returns to frontier.

**Budget policy is H1, literally:** stop investing in covered predicates at certification (good enough = certified, not perfect); spend the growth budget exclusively on the frontier list. The manifest's `frontier` array *is* the frontier of incompetence, machine-readable.

### 2.5 Assembly over storage (the specialist rule)
What gets stored is the **skill** (gene), never the configured agent (body). The queen — when she exists — routes by *manifest coverage*: compile task → predicates → match certified skills → assemble the insect on the spot. A "specialist" is a recurring assembly pattern, not a stored creature. **Caching rule:** a pattern that assembles identically ≥50 times may be cached as a named specialist — earned by repetition, revoked if any constituent skill's certificate drops. This is H3's promotion criterion applied one level up, and it's the guard against the documented skill-library failure mode (monotonic growth, no retirement, retrieval dilution): units stay small enough to expire cleanly.

### 2.6 Model arbitrage (reverse-siphon with a trigger)
Three rungs, one rule: the **frontier model grows** the skill (expensive, once — Run 005 pricing), the **frozen weak instrument certifies** it, and the **weakest model holding the certificate executes** it thereafter. The certificate is the downgrade permit: execution always runs on the cheapest rung whose Wilson lower bound clears that skill's θ. Climbing down a rung requires re-certification at that rung — that's the toll. Climbing up (frontier fallback) is permitted only when a certified skill fails live, and the failure feeds BANK as a new journal. Cost columns (`cost_to_acquire`, `cost_per_execution`) ride in provenance so routing-on-cost is free later; token efficiency is a measured column, not a research program.

## 3 · Pre-registered experiments (the spec's teeth)

**E0 — Window fix (prerequisite).** Lift the ~120-char journal truncation. Re-run the Run-005 lineage. Pre-registered expectation: banked-primitive count strictly exceeds 4 with fogged-proposal waste below Run 005's ~20. If the window fix doesn't move these, the ladder's third rung was misdiagnosed — investigate before proceeding.

**E1 — The reuse delta (tests C1, the whole ballgame).**
Design: two maps, A and B, sharing ≥2 predicates, differing in ≥2 (e.g., two Ben-domain maps — content-migration and health-recert already share structure).
- Arm 1 (cold): fresh agent traverses A, then fresh agent traverses B. Record cost + cert outcome for B.
- Arm 2 (equipped): fresh agent traverses A, BANK runs, second agent traverses B *with the manifest*.
- Pre-registered success: Arm 2's B-traversal shows ≥30% cost reduction OR a cert outcome Arm 1 fails to reach, across 5 paired runs.
- **Kill criterion:** if equipped ≤ cold across 5 pairs, BANK as designed is dead weight — publish the negative, redesign the skill unit before any further build.

**E2 — Certification discriminates (tests C2).**
Bank skills from a clean traversal and from a deliberately-degraded one (planted-flaw method from the corpus generator). Pre-registered: certification rate for clean-sourced skills exceeds degraded-sourced by a margin the Wilson intervals separate at n=20 probes per skill. If certification can't tell good skills from bad ones, the manifest is a brag sheet — C2 dies honestly.

**E2b — Abort governor separates (piggybacks on existing data, near-free).** Run typed-category migration analysis retroactively on the grow-001..005 journals and the 140-build never-solved set: prediction — eventually-solved tasks show directional drift before solving; never-solved split into wall and churn. Judge-swap ablation included. If the three classes don't separate, the abort governor ships as naive repetition-detection only and H9 dies cleanly in public.

**E3 — Decay is load-bearing (deferred to v1.1, registered now).**
Version-bump a tool a certified skill depends on; verify re-cert triggers and the stale skill demotes before an agent trusts it. (Runs after E1/E2 pass; listed so it can't be quietly dropped.)

## 4 · v1 boundary (the anti-rabbit-hole clause)

IN: skill extractor (frozen rubric), SKILL.yaml format, per-skill probe certification, manifest generation + novelty-gate routing, E0–E2.
OUT (Parking Lot, explicitly): queen/dispatch, multi-agent colonies (when they arrive: shared manifests are a Byzantine-consensus problem — quarantine-before-adoption, one agent's certified skill is another's unverified claim), internet traversal beyond existing Ben-domain maps, compiler changes, skill marketplaces, covenants/swarm scale, robots, grandpa UI polish.

**Done =** E0 complete, E1 and E2 pre-registrations resolved (pass OR published kill), manifest consumed end-to-end by one agent on one novel task. That's the full product. Chiseling starts after.

## 5 · Build order (each gate blocks the next)

1. **G0:** Window fix + Run-005 lineage rerun (E0). ~1 session.
2. **R1 (single research pass, hard-capped at one session):** skill anatomy — the right unit size. Harvest design rules from Voyager library bloat, Hermes extraction format, skill-drift literature; output is the extractor's frozen rubric, nothing else. No second pass.
3. **G1:** SKILL.yaml + extractor with frozen rubric, run against existing grow-001..005 journals retroactively — free training data already in the repo. ~1–2 sessions.
4. **G2:** Per-skill probe certification wired to existing Wilson machinery. ~1 session.
5. **G3:** Manifest + novelty gate; one agent, one Ben-domain map, routing live. ~1–2 sessions.
6. **G4:** E1 paired runs. E2 degraded-source runs. Publish results either way. ~2 sessions.

Estimated: 6–8 sessions to a resolved claim. Cost ceiling per E1 arm at Run-005 rates: dollars, not hundreds.

## 6 · Why this is the extraordinary piece

Every agent framework ships memory. Hermes ships skill extraction. Nobody ships **skills with confidence intervals** — a manifest where "this agent can do X" is a certified, revocable, provenance-stamped claim instead of marketing. If E1 shows the reuse delta and E2 shows certification discriminates, the manifest becomes the first honest answer to grandpa's question — *what can it do now?* — with math behind every line. And it's the exact substrate the queen needs: staffing becomes manifest-coverage matching, which means building this first makes the Body nearly mechanical.

The claim is falsifiable, the kill criteria are written before the code, and the first training data (five grow journals) is already sitting in the repo you published tonight.
