---
tags: [dot-maps, case-study, compiler, external-validity]
date: 2026-07-30
status: complete — first certified map from a real-world procedure
---

# Case Study: The Closing Procedure — Four Rounds to Certification

**Subject:** real restaurant shift-close procedure (drawer count, cooler temp, line wrap, dish machine, door, alarm). Described informally by the procedure's owner; compiled by the Dot Maps translation layer; tested by a frozen weak agent against θ = 0.70 with Wilson intervals.

**Result:** CERTIFIED on round 4 — n=40, pass rate 1.00, CI [0.91, 1.00] — after three published failures. Predicate typing went 4-green/3-amber → 5/2 → 7-green-but-failed → 7-green-certified.

**Why this matters:** one evening of contact with one real procedure surfaced four distinct design findings, each now a required section of the method. Whiteboarding found none of them; contact found all of them.

---

## Finding 1 — Branch flattening (round 1)
The compiler turned "if it's more than $20 off, text the manager" into a *pass requirement* that variance stay under $20 — flattening a conditional branch into a gate. A $30-off night with a perfect manager alert would have failed. Caught only by comparing the map against ground truth with the procedure's owner.
**Design consequence:** conditional predicates need explicit branch semantics in the schema; compiler must preserve if/then structure, not collapse it.

## Finding 2 — The evidence ladder (round 2)
After human-level ambiguity was fixed, surviving ambers revealed a second rung: *human-legible* is not *machine-verifiable*. Physical-world steps bottom out in evidence artifacts (a named file, a written count) because a verifier can't walk into the kitchen.
**Design consequence:** verification tiers are real — T1 judgment / T2 named observable state or artifact / T3 tamper-evident attestation — and the schema needs an attestation/evidence-binding predicate type. (Connects to the oracle-validity gating hypothesis.)

## Finding 3 — The unfrozen verifier (round 3)
An identical sentence ("arm the alarm at the keypad before leaving") graded CHECKABLE in one round and NEEDS CLARITY the next. The compiler was re-rolling its standards per invocation — an unfrozen verifier inside a system whose entire thesis is frozen verification. Left uncorrected, it demands infinite attestation regress (photos, timestamps, marker colors) and no map can ever converge.
**Fix applied:** froze the compiler with an explicit tier rubric, graded at T2, hard no-escalation clause. Same input then compiled 7/7 CHECKABLE.
**Design consequence — promoted to method principle:** *every verifier in the pipeline, including the compiler, must operate under frozen, pre-registered rules.* The instrument caught its own violation of its own thesis.

## Finding 4 — Length–quality conflation (round 3 test run)
A zero-amber, 7-predicate map failed at 0.35: whole-run conjunction scoring compounds per-step probability, so meticulous long maps score worse than sloppy short ones. Real traversal permits within-budget retries (this is what max_steps is for).
**Fix applied (demo):** deterministic base rate 0.88–0.99 + one within-run retry per step.
**Design consequence (instrument):** the real answer is per-predicate certification — each predicate clears θ individually; the certificate is the conjunction of certified predicates, not a whole-run gamble. Map length must not masquerade as map quality.

## Open calibration note (round 4)
Post-fix, the clean map passed at a flat 1.00 — the correction likely overshot lenient. The true per-predicate base rates are an empirical constant obtainable only from real sandboxed traversals. This is precisely the boundary between the demo and the instrument, and where the paper's experiments begin.

---

## The loop, demonstrated end-to-end
vague words → FAILED (published) → guided clarification → FAILED (published) → frozen compiler → FAILED (published, instrument's fault) → fixed physics → CERTIFIED.

The translation layer taught the operator to specify; the operator's ground truth debugged the translation layer. Both directions of the loop produced findings. This is the external-validity story: a domain not constructed by the author, graded honestly, with negatives published.

## Prediction record (pre-registered each round)
R1: typing largely hit, P2-reasoning wrong-for-right-reasons. R2: predicted 0 ambers, got 2 — compiler stricter than modeled. R3: predicted certify, got instrument failure — model of compiler wrong, stopped predicting, fixed instrument. R4: predicted certify 40–75, certified at 40. Final: 2/4. The misses produced Findings 2–4; the record itself is the methodology.
