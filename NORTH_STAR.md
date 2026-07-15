# NORTH STAR — read this first, build nothing from it yet

*What the whole stack is actually for, revised after the bottom-up insight. This document changes the INTERPRETATION of the specs, not their execution. The research loop runs exactly as written. CRITERIA.md stays frozen.*

---

## The revised destination

The product is not "maps sold to people so their agents can execute tasks." That's v0.1 — the training-wheels version, still worth shipping, still the revenue seed. The actual destination is:

**An agent that builds its own map when it hits a novel task.** Not automation — instinct. The mechanism of adaptation itself: take a raw agent on a weak model and give it the faculty of equipping itself — deriving its own roadmap, its own checks, its own plan of attack — for tasks nobody decomposed for it. When that exists, memory/skills/MCPs/prompt-engineering stop being things a human bolts on and become things the agent's own map recruits.

## The mechanism (the bottom-up correction)

The self-mapping agent does NOT work by knowing what "done" means for a novel task (top-down decomposition from a stated goal — that's how the current maps are made, by a human cartographer). It works bottom-up, the way a human learns baseball:

1. **POKE** — probe the environment; harvest primitives and their FREE LOCAL CHECKS (did the bat contact the ball; did the API return 200; did the branch hold). Rules are pre-installed local validators. A novel task decomposed into fundamentals IS the act of discovering its rules.
2. **FORAGE** — research only the questions the world wouldn't answer by poking. Escalate poke→research only when marginal-rules-per-poke hits zero with questions still open. Never research first.
3. **METABOLIZE** — synthesize harvested rules into a candidate ruleset: the grown map. The map is grown from primitives forward, not drawn from the destination back.
4. **SANDBOX** — attempt under local-check pressure, staged (safe pokes; the staging layer from the product spec is the poking apparatus for expensive/irreversible domains).
5. **CONSOLIDATE** — reflect; promote survivors to the permanent primitive library (episodic→semantic, the consolidation architecture); log gaps.
6. Return to POKE one level up. It is a spiral, not a circle: pass 1 probes primitives, pass 2 tactics, pass 3 strategy. The 0 (incompleteness) drives every revolution; the 1 (consolidation) is what each revolution banks; the banked 1 is the floor the next 0 probes from.

Two validators, never blurred: local checks prune ACTIONS inside the run; consolidation prunes KNOWLEDGE after it.

## Why the current research program is still exactly the right first move

Every phase transition in the loop above is a CONVERGENCE EVENT (novelty-per-poke decaying, questions-to-answers converting, sandbox greening or stalling, extract stabilizing). The convergence instrumentation already built (novelty rate, participation ratio, AR(1)) is therefore not just a map-grader — it is the candidate PHASE CLOCK of the instinct engine: the thing that turns the wheel without a homunculus.

**H1 is the keystone.** If the weak-probe instrument can read road quality, then a self-mapping agent can grade ITS OWN candidate maps — propose a decomposition, run the cheap probe, read whether the road it grew is traversable — before committing. Map-maker and map-grader close into a loop. Without H1, the self-mapping agent is a faster hallucination grading its own homework with a broken ruler.

So the dependency chain, plainly:
- H1 lands → the instrument is real → the phase clock and the self-grading faculty are buildable → the POKE-loop agent becomes the next spec.
- H1 dies → the instinct engine as designed has no internal critic → back to fleet-difficulty labeling and a human-gated cartographer; the vision survives but the mechanism changes.
Either way, the twenty Stage-0 runs are the first bits of ground truth the north star gets.

## What is explicitly NOT changing

- The research loop spec runs verbatim. No new dots. This document is not in scope for any session.
- CRITERIA.md remains frozen. The north star does not touch pre-registered thresholds.
- v0.1 product (three maps, one domain, one paying/serious stranger) still ships — it is the revenue seed, the natural-corpus collector, AND the first-contact artifact for finding the crew. Human-made maps are how the primitive library gets seeded before agents can grow their own.
- The honest prior-art note carries forward: the loop's SHAPE exists in fragments (curiosity-driven exploration, Voyager's curriculum + skill library, which works because Minecraft supplies a free oracle). The unclaimed part is grounded local-check discipline at every phase + a CERTIFIED instrument as the phase clock + manufacturing the oracle per domain via poke-harvested local checks. The loop is old. The grounding of every spoke is the contribution.

## The one-line version

Prove the instrument (research loop, running now) → ship the human-made maps (v0.1, funds and recruits) → then build the agent that grows its own: POKE → FORAGE → METABOLIZE → SANDBOX → CONSOLIDATE, spiraling up, phase-turned by the certified detector. The frontier bet, named: **instinct = grounded selection pressure, running bottom-up, with a measured clock.**
