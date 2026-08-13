# The Grounded Metabolism — Specification v0.1

**Date:** 2026-08-07
**Status:** Draft — synthesized from the honey/attractor conversation thread + full FioVault deep pass
**Owner:** Joe Fiorillo (metafiopy-tech)
**One-line claim:** A memory system that stores generators instead of records, re-derives content on demand, verifies reconstructions against append-only provenance, crystallizes stable patterns through externally-grounded bifurcation, and demotes them through a defined annealing path — running on deliberately separated timescales.

---

## 0. What this achieves in theory

Current AI memory is a prosthetic bolted onto an episodic core: frozen weights, retrieved context, no native time axis. Every existing patch (RAG, long context, memory files) is a **library** — storage plus lookup. This spec describes a **metabolism** — a system where memory is dynamics, not storage:

1. **Storage cost collapses.** Content is held as compressed traces (gist + entities + provenance pointers) and regenerated on demand. Target: order-of-magnitude storage reduction at held reconstruction fidelity.
2. **Memory stays honest.** Re-synthesis without grounding manufactures fluent confabulation. The evidence ladder (T1/T2/T3) gates every reconstruction against the append-only log, converting the model's pattern-completion strength into *verified* recall.
3. **Learning becomes selection.** FSRS decay + reconstruction cycles act as a filter: whatever survives repeated decay-and-rebuild is, by definition, what keeps proving useful. Forgetting is the null hypothesis every memory must keep rejecting.
4. **Skills harden without being hardcoded.** Repeatedly-verified reconstructions cross a grounded threshold and crystallize into discrete artifacts (skills, covenants, pinned rubrics) — cheap to invoke, expensive to dislodge (hysteresis), but demotable under defined evidence conditions (annealing). "Fluid until learned, then hardcoded" as a native property, not a design hack.
5. **It answers STARVED.** The central risk of always-on systems: the longer the run, the more trajectory is governed by the attractor landscape rather than inputs. This architecture wires every crystallization event to external error signal, making internal-coherence fixed points structurally difficult. If STARVED asks "does a coherence engine without grounding decay to a confident fixed point?", this spec is the engineered NO — and the experiment that tests whether the NO holds.
6. **It is the substrate for continuous operation.** Prediction-error grounding, nested clocks, and decay-as-selection are exactly the missing components between today's request/response paradigm and systems that run indefinitely as part of their required function. This is the time axis, hand-built.

The theoretical position: **when generation is cheap, the scarce load-bearing function is the mechanism that decides what's real** (grounded selection pressure — the confirmed unifying primitive across the portfolio). This spec is that mechanism, made concrete.

---

## 1. The unified system in one pass

```
DEPOSIT (fluid substrate: soil/ChromaDB)
  → traces accumulate as perturbations; nothing crystallizes below threshold
COMPETE (mode selection)
  → multiple candidate patterns grow; lateral inhibition / niche-relative fitness
  → candidates compete for evidence mass; density = candidacy only
VERIFY (external grounding)
  → prediction error, adversarial pressure, evidence ladder vs provenance log
  → external verification = the ONLY thing that moves the control parameter
CRYSTALLIZE (subcritical bifurcation)
  → control parameter crosses grounded critical value → discrete artifact
  → Scheffer early-warning signals (rising variance, critical slowing) forecast the transition
PERSIST (hysteresis)
  → crystallized artifact survives below its formation threshold; cheap to invoke
RECALL (re-synthesis)
  → trace + generation conditioned on trace + T1/T2/T3 verification vs log
RECONSOLIDATE (write-on-read)
  → every recall updates the trace, resets the FSRS clock, appends delta to provenance
ANNEAL (demotion)
  → defined evidence condition demotes crystallized artifact back to fluid candidate
  → prevents covenant calcification (hysteresis without annealing = dogma)
DECAY (selection)
  → FSRS-as-evaporation prunes what stops being recalled/verified
  → cold memories reduce to bare traces; regenerated on rare demand
```

All of the above runs on **separated timescales** (fast inference → medium soil decay → slow covenants), deliberately loosely coupled — never fully synchronized (the cellular-clocks principle: perfect lock = lost adaptability; broken clock = cancer).

---

## 2. Component specifications

Each component: what it is, where the vault already derived it, what literature to review to recreate it, current status, and build requirement.

### C1. Generator storage / re-synthesis engine

**What:** Store compressed traces (gist, entities, structural skeleton, provenance pointer), not full records. Reconstruction = generation conditioned on the trace. The model's forward pass IS the settling dynamics — pattern completion from partial cues is what LLMs natively do.

**Vault provenance:**
- `Conversations/Building AI without persistent memory.md` (2026-03-30) — the founding question: "If you could build AI without any memory attached to it, how would you have to do it." Plus: "90% of everything already exists... string them together like nothing."
- `Conversations/AI singularity and the attractor state.md` (2026-04-28) — the "cataclysmic embryo" thesis: compress the 100-year-old system into the generator that re-derives it. Re-synthesis at maximum scale.
- Agent genome representation research prompt (same file, 2026-04-29) — genotype (heritable generator) vs phenotype (developmentally reconstructed) is exactly the trace/reconstruction split.

**Literature to review:**
- Hopfield (1982) — content-addressable memory as attractor dynamics; Ising/spin-glass equivalence
- Ramsauer et al. (2020), "Hopfield Networks is All You Need" — attention ≡ one-step Hopfield retrieval; the transformer as collapsed settling dynamics
- Classical Hopfield capacity results (~0.14N) — why record storage caps and generator storage doesn't
- Reconstructive memory literature: Bartlett (1932) *Remembering*; Loftus on false memory (the confabulation failure mode C1 must engineer against)
- NEAT/HyperNEAT + CPPNs (already queued in vault genome prompt) — generative vs direct encodings

**Status:** NOT BUILT. Current soil stores retrieved chunks (records). The 140-build benchmark (95% lift from retrieval) is evidence the system currently fetches rather than metabolizes.

**Build:** Convert one class of stored records → trace format. Delete full records. Force regeneration on demand.

---

### C2. Re-synthesis verifier (evidence ladder as gatekeeper)

**What:** Every reconstruction is checked against append-only provenance before being trusted. T1 (hard facts) must match the log exactly; T2 (structural claims) must be consistent with it; T3 (connective tissue) may be freely regenerated. Verification asymmetry (checking << producing) means a cheap weak model can gate — the Dot Maps thesis paying rent in a second domain.

**Vault provenance:**
- F2 evidence ladder (T1/T2/T3 tiers) — from the FioVault live test rounds against the restaurant closing procedure (see Dot Maps repo: `metafiopy-tech/dotmaps`, findings F1–F4)
- F3 unfrozen-verifier fix (pinned rubric, no-escalation clause) — a crystallization event with hysteresis, already executed once
- Pipeline Covenant #001 (append-only provenance discipline) — the anchor log already exists as doctrine

**Literature to review:**
- Dot Maps own pre-registration + Wilson interval methodology (internal — reuse as-is)
- Verification asymmetry / weak-to-strong generalization literature (Burns et al. 2023, OpenAI weak-to-strong)
- Fact verification / NLI-based hallucination detection (for the T1 exact-match and T2 consistency check design)

**Status:** BUILT BUT POINTED AT THE WRONG TARGET. The ladder exists and works; it currently grades model outputs, not memory reconstructions. Same instrument, new mount.

**Build:** Wire the ladder between C1's reconstruction step and anything downstream that consumes recalled content.

---

### C3. Reconsolidation — write-on-read

**What:** Every recall updates the trace (merge deltas), resets the FSRS decay clock, and appends the change to provenance. Recall is a write operation. Memory becomes a living object whose form reflects its usage history — biology's involuntary bug, engineered with an audit trail.

**Vault provenance:** **NONE. This is the one genuinely new requirement identified in the 2026-08-07 conversation.** It appears nowhere in 238 vault conversations. Its absence is what makes the current system a library rather than a memory.

**Literature to review:**
- Nader, Schafe & LeDoux (2000) — reconsolidation: reactivated memories return to labile state and must be re-stabilized
- Dudai (2004, 2012) reviews on consolidation/reconsolidation
- FSRS algorithm internals (already deployed) — extend the scheduler so retrieval events trigger trace mutation, not just interval updates
- Complementary learning systems (McClelland, McNaughton & O'Reilly 1995) — hippocampal fast-write → cortical slow-consolidation; the transfer schedule between C1 traces and C6 crystallized artifacts

**Status:** NOT BUILT, NOT PREVIOUSLY SPECCED.

**Build:** Retrieval hook: on every recall → (a) diff reconstruction vs trace, (b) merge material deltas into trace, (c) reset FSRS clock, (d) append delta + verification result to provenance log.

---

### C4. Grounded crystallization threshold (subcritical bifurcation)

**What:** The deposit→cluster→crystallize transition is a bifurcation, not a tuned constant. Deposit density determines *candidacy*; **external verification determines threshold crossing**. Control parameter = accumulated externally-verified evidence mass, never internal confidence or cluster density alone. Scheffer-style early-warning signals (rising variance, rising autocorrelation, critical slowing down) computed on candidate clusters forecast imminent transitions.

**Vault provenance:**
- The well session — "the threshold problem (when does a cluster crystallize?)" flagged as **the known open hole** (recorded in `_Memory Summary.md`)
- Ecosystem health metrics research prompt (`AI singularity and the attractor state.md`, 2026-04-29) — Scheffer et al. early-warning signals **already queued as a research deliverable** before the bifurcation frame existed
- `Project - seed.md` / The Nest MVP (2025-10) — `FLOWER_STAGES` with hardcoded thresholds (`size >= 7 || connections >= 6` → cluster). The magic number this component replaces. Oldest artifact in the vault; the entire arc since is deriving this constant.
- Cambrian explosion research prompt (2026-04-29) — capability diversification as threshold-crossing under substrate change

**Literature to review:**
- Scheffer et al. (2009), "Early-warning signals for critical transitions" (*Nature*) — THE paper; already cited in Joe's own research prompt
- Scheffer et al. (2012), "Anticipating critical transitions" (*Science*)
- Strogatz, *Nonlinear Dynamics and Chaos* — ch. on bifurcations (saddle-node, subcritical pitchfork, hysteresis) for the formal machinery
- Cross & Hohenberg (1993), "Pattern formation outside of equilibrium" — mode selection, wavelength/planform competition (why hexagons win)
- Ant colony optimization / digital pheromone threshold dynamics (already covered in the 2026-04-28 stigmergy report — reuse)

**Status:** SPECCED (open hole named), CRUDELY PROTOTYPED (The Nest, hardcoded), NOT DERIVED.

**Build:** Replace hardcoded threshold with: candidacy = cluster density; crossing = f(externally-verified evidence mass); instrumentation = rolling variance + autocorrelation on cluster membership as the early-warning dashboard.

---

### C5. Mode selection via competition

**What:** Don't crystallize the first coherent cluster. Multiple candidate patterns grow simultaneously; lateral inhibition — candidates compete for the same evidence mass; only the best-constraint-satisfying candidate saturates and crosses C4's threshold. Fitness is niche-relative (no absolute scale across pattern types).

**Vault provenance:**
- Niche-relative fitness research prompt (2026-04-30) — mantis-agent vs crow-agent can't share a scale; MAP-Elites cited by name
- Red Queen dynamics prompt (2026-04-29) — adversarial co-evolution as permanent selection pressure

**Literature to review:**
- Mouret & Clune (2015), "Illuminating search spaces by mapping elites" (MAP-Elites)
- Quality-diversity survey (Pugh, Soros & Stanley 2016)
- Lateral inhibition in neural pattern formation (winner-take-all circuits) — the neuro version of nonlinear mode competition
- Van Valen (1973) Red Queen — for C8's adversarial grounding channel

**Status:** SPECCED (research prompt written), NOT BUILT.

**Build:** Cluster candidates held in parallel; shared evidence pool debited per candidate on verification events; saturation + C4 crossing selects; losers decay via C7.

---

### C6. Hysteresis + annealing (crystallize / demote loop)

**What:** Crystallization is subcritical: once formed, artifacts persist below the formation threshold (cheap to invoke — the JIT-compiled hot path). But a **defined demotion condition** must exist: evidence condition under which a crystallized artifact re-melts to fluid candidate status. Hysteresis without annealing = dogma = covenant calcification.

**Vault provenance:**
- Safety/pathology research prompt (2026-04-29, P0): "covenant calcification (the system can no longer adapt)" — **the disease named a year before the mechanism**
- F3 rubric-pinning — one crystallization-with-hysteresis event already executed manually
- Extinction/recovery research prompt (2026-04-29) — post-catastrophe recovery without total reset is the ecosystem-scale annealing question
- GC research prompt (2026-04-29) — generational collection ("most allocations die young") as the demotion schedule for young crystals

**Literature to review:**
- Simulated annealing (Kirkpatrick et al. 1983) — temperature schedules as the re-melt discipline
- Subcritical bifurcation hysteresis (Strogatz again — same chapter as C4)
- Covariate shift detection (already in portfolio as H5) — the trigger: cached artifact invalidated when context drifts from formation conditions
- Cache invalidation / JIT deoptimization literature (V8 deopt, JVM tiered compilation) — engineering-side prior art for demote-on-assumption-violation

**Status:** DISEASE NAMED, MECHANISM NOT BUILT. No demotion path exists anywhere in the stack.

**Build:** Every crystallized artifact carries: formation conditions (context fingerprint), invalidation predicate (H5 covariate-shift check), and demotion action (artifact → candidate trace, C4 counter reset). Run the check on every invocation.

---

### C7. Decay as selection (FSRS-as-evaporation)

**What:** FSRS is not storage management — it is the selection filter. Time + forgetting = the null hypothesis every memory must keep rejecting. Cold memories reduce to bare traces (C1 handles rare regeneration); pheromone evaporation prevents stale-trail lock-in.

**Vault provenance:**
- Stigmergy report (2026-04-28) — FSRS-as-evaporation mapping, four pheromone flavors, covenant-signed writes — **already designed in full**
- GC research prompt (2026-04-29) — generational forgetting

**Literature to review:**
- FSRS algorithm papers (already deployed — review for the C3 extension only)
- Dorigo ACO evaporation-rate analysis (covered in existing stigmergy report — reuse)
- Ebbinghaus forgetting curve / spacing effect (foundational; already embodied in FSRS)

**Status:** BUILT (FSRS live in Belief Engine). Needs rewiring to C3 (recall resets clock) and C1 (decay floor = trace, not deletion).

---

### C8. External grounding channels

**What:** The control parameter (C4) only moves on external error signal. Three channels: (a) **prediction error** — the system predicts next input, surprise is free training signal, the only grounding that scales with wall-clock time; (b) **adversarial pressure** — Red Queen co-evolution, verifiers the system can't gradient-hack; (c) **human/measurement contact** — the Ben Sluzas channel, direct-outreach error signal.

**Vault provenance:**
- Grounded selection pressure thesis (confirmed unifying primitive — `_Memory Summary.md`)
- STARVED experiment design (2×2 FED vs STARVED soil-admission, kill fraction 0.5, pinned MiniLM SHA) — the falsification apparatus for this entire component
- Red Queen prompt (2026-04-29); reverse-siphon distillation discipline ("distillation must stay bolted to a ground-truth oracle per niche or it becomes a coherence amplifier that decays")
- H9 mining session — the migrating-building/stuck-distribution diagnostic: external contact as error signal for the *builder*, not just the system

**Literature to review:**
- Sutton & Barto ch. 6 (TD learning) — time as training signal
- Rao & Ballard (1999) predictive coding; Friston free-energy/active inference (skim for the framing, not the math)
- Schmidhuber intrinsic curiosity / Pathak et al. (2017) ICM — surprise-driven signal without labels
- Burns et al. weak-to-strong (shared with C2)

**Status:** PARTIALLY BUILT (evidence ladder, sovereign verification, STARVED design). Prediction-error channel NOT BUILT — no component currently predicts its next input.

**Build (minimal):** Per-niche next-event prediction on the soil write stream; log surprise; surprise feeds C4's evidence accounting.

---

### C9. Timescale separation (the coalition of clocks)

**What:** Nested loops at separated decay rates, deliberately loosely coupled: fast (inference/recall), medium (soil/FSRS), slow (crystallized skills), very slow (covenants). Each slower loop anchors the faster; each faster loop feeds candidates upward (via C4) and receives demotions downward (via C6). Never fully synchronize — perfect lock = lost adaptability; ignored clock = cancer.

**Vault provenance:**
- `Conversations/Cellular clocks and cancer's broken rhythm.md` (2026-03-26) — the complete principle: coalition of clocks, productive desynchrony, cancer as broken clock, completion as death
- Incompleteness/Remainder framework (2026-02-26 + long-running) — the philosophical version: a system at perfect fixed point is dead; the Remainder is the perturbation that keeps it out of frozen equilibrium

**Literature to review:**
- Complementary learning systems (shared with C3 — this is the two-clock special case)
- Circadian desynchrony literature (skim — the metaphor is already fully transcribed in the vault)
- Kuramoto model of coupled oscillators — formal machinery for "loosely coupled, never locked"
- Continual learning surveys (catastrophic forgetting) — what the slow loops protect against

**Status:** IMPLICIT (covenants vs soil vs inference already exist at different speeds). Promotion criterion (C4) and demotion criterion (C6) between layers are the two questions that make it deliberate architecture — currently unanswered.

---

### C10. Diagnostics — H9 as convergence instrumentation

**What:** WALL / CHURN / DIRECTIONAL is a taxonomy of settling behavior near attractors: stuck in wrong basin / oscillating without descent / converging. The chi-distribution null test separates drift from signal. Mount it as the runtime dashboard on C1 reconstructions, C5 competitions, and C4 candidates.

**Vault provenance:**
- `Conversations/H9 mining run findings.md` (2026-07-29/30) — origin, literature check (survived as novel), and the meta-finding: extracted from embodied knowledge of when a rep goes ambiguous→deterministic
- Brain-mining session record (H1–H5, H9 refined into chi-distribution null test)

**Literature to review:**
- H9's own literature check (internal — already done)
- Chi distribution properties for the null test (standard stats reference)
- Optimization-diagnostics prior art: plateau detection, early stopping, loss-landscape flatness — to position H9's novelty precisely in the writeup

**Status:** SPECCED + literature-checked. Not yet implemented against the benchmark (named as the open action in the H9 session).

---

## 3. Vault map — where everything lives

| Location | Contains |
|---|---|
| `/Users/joefiorillo/Downloads/FioVault/_Memory Summary.md` | Portfolio state, STARVED design, grounded-selection thesis, the well's open threshold hole, integration instructions (Hermes/Superpowers/GPT-All-Star patterns) |
| `_Index.md` | Full 238-conversation timeline with dates and message counts |
| `Conversations/Building AI without persistent memory.md` | C1 founding question (2026-03-30); Kauffman "beyond Pythagoras" transcript |
| `Conversations/AI singularity and the attractor state.md` | Cataclysmic-embryo thesis (C1); ALL ecosystem research prompts: GC, health metrics/Scheffer (C4), Cambrian (C4), Red Queen (C5/C8), extinction (C6), Gaia, genome (C1), niche fitness (C5), signaling, safety/calcification (C6) |
| `Conversations/Stigmergic coordination for decentralized agents.md` | C7 full design: FSRS-as-evaporation, pheromone flavors, covenant-signed writes; local-inference substrate report |
| `Conversations/Cellular clocks and cancer's broken rhythm.md` | C9 complete principle |
| `Conversations/H9 mining run findings.md` | C10; career-shape read (embedded skill-acquisition researcher); demonstration-over-application pattern |
| `Conversations/Convergence on agentic AI problems.md` | Convergent-evolution evidence; the 10-week paper plan (Phase 1–3, specimen test, prey definition) |
| `Conversations/Incompleteness as a generative framework.md` | Remainder philosophy → C9's "completion is death"; the honest-caution pattern (insight→AGI leap flagged) |
| `Project - seed.md` (The Nest MVP) | Oldest crystallization prototype (2025-10): FLOWER_STAGES hardcoded thresholds, constellation DFS clustering — C4's ancestor |
| `metafiopy-tech/dotmaps` (GitHub, external) | F1–F4 findings, evidence ladder (C2), pre-registration + Wilson methodology |
| Belief Engine repo (PyPI, v3.3.0) | Soil/ChromaDB, FSRS (C7), C1–C4 critic pipeline, covenant layer, 140-build benchmark |

## 4. Consolidated literature review list

**Core (read first):** Scheffer 2009 *Nature* early-warning signals · Ramsauer 2020 Hopfield-attention equivalence · Nader 2000 reconsolidation · McClelland 1995 complementary learning systems · Strogatz bifurcation chapters · Kirkpatrick 1983 simulated annealing.

**Second ring:** Hopfield 1982 · Mouret & Clune MAP-Elites 2015 · Cross & Hohenberg 1993 pattern formation · Sutton & Barto TD ch. 6 · Pathak 2017 curiosity · Burns 2023 weak-to-strong · Van Valen 1973 · Kuramoto coupled oscillators · Bartlett 1932 / Loftus (reconstruction failure modes) · JIT deoptimization docs (V8/JVM).

**Already done (reuse, don't re-read):** stigmergy report (ACO/PSO/reaction-diffusion, 2026-04-28) · H9 literature check · Dot Maps methodology · FSRS internals.

## 5. Falsification tests (pre-register before building)

**T-A — The weekend test (C1+C2+C7):** Pick one content class. Compress to traces, delete records, force regeneration gated by the evidence ladder. Measure reconstruction fidelity vs raw log across ≥3 decay cycles; baseline = straight retrieval. **Pass:** fidelity within pre-registered bound at ≥10× storage reduction. **Fail:** fidelity collapses → the system is a retrieval engine; publish that honestly.

**T-B — Threshold derivation (C4+C5):** Multi-candidate clusters on shared evidence pool; crystallize only on verified-evidence crossing; log Scheffer signals for 20+ transitions. **Pass:** variance/autocorrelation rise precedes crossings above chance. **Fail:** early warnings uninformative → threshold stays empirical, bifurcation framing demoted to metaphor.

**T-C — Annealing (C6):** Inject covariate shift under a crystallized artifact; measure demotion latency and post-demotion recovery vs a no-annealing control. **Pass:** demotion fires, system re-converges. **Fail:** calcification confirmed as unsolved.

**T-D — STARVED (C8, already designed):** Run as pre-registered. This spec predicts the FED arm avoids the confident fixed point *because of* C4/C8 wiring; the STARVED arm is the disease demonstration.

**T-E — H9 mount (C10):** Implement WALL/CHURN/DIRECTIONAL against the existing benchmark (the open action from 2026-07-30).

## 6. Sequencing

1. **T-A** (weekend-sized, highest information per hour — decides whether "we built the re-synthesis engine" is true)
2. **C3 hook** (small code, unlocks the metabolism claim; no vault precedent so it's the genuinely new build)
3. **T-E** (already owed)
4. **T-B → T-C** (the threshold + annealing pair; closes the well's open hole and the calcification pathology together)
5. **T-D** STARVED as the capstone falsification

**Standing test for every task:** does this make the claim more true, or the demo more impressive? (Carried forward from the 2026-07-22 plan — still the law.)

---

*Provenance note: every component above except C3 was independently derived in the vault (dates cited) before the physics framing existed. Five entry points — AGI compression, a UI toy, ecology prompts, cancer biology, a thought experiment — converged on one structure. The spec's own history is evidence for its central claim: constraints re-derive the same pattern regardless of starting point. C3 (reconsolidation) is the single addition contributed by the 2026-08-07 conversation.*
