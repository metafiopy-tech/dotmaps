# corpus/ — the Instrument Experiment layer

Experiment layer for [`instrument_experiment_spec.md`](../instrument_experiment_spec.md).
Builds ON TOP of the harness; changes no harness semantics. Three pre-registered
hypotheses (B1 weak-probe-as-instrument, B2 ladder-floor dual certificate, B3
adversarial certification), all readouts of one sweep over this corpus.

## Layout

```
corpus/
├── recipes/               # variant recipes + human-authored weak/dense verifiers
│   └── map2-pilot/        # Stage-0 ambush pilot: 4 variants of map-2
│       ├── t1-sparse-blunt.yaml   (T1: sparsify 0.5 + blunt — heavy)
│       ├── t2-blunt.yaml          (T2: one mild operator)
│       ├── t3-base.yaml           (T3: certified base, the anchor)
│       ├── t4-dense.yaml          (T4: densified, real finer dots)
│       └── assets/                (hand-written verifiers — synthesis is NOT under test)
├── pilot/                 # generated variant repos + the shared seed workspace
│   └── seed-ws/           # compiled config (.dotmaps authoritative + protected source)
├── pilot_analysis.py      # applies the PRE-REGISTERED Stage-0 decision rule verbatim
└── README.md
```

## Ground truth by construction

Quality tiers are planted: WE apply the degradations, so the ordering
T0 < T1 < T2 < T3 < T4 is ground truth by construction (the E3 move). Honest
limitation, stated up front: constructed degradation ≠ natural variation; real
customer maps over time are the follow-up dataset.

## Commands

```bash
# build a variant from a recipe (runs integrity checks: DAG valid + every
# non-tautology verifier must FAIL on a broken workspace)
dotmaps corpus recipes/map2-pilot/t1-sparse-blunt.yaml --out pilot/m2-t1-sparse-blunt

# probe a variant exactly like a product map (5 fresh runs, Wilson bounds)
dotmaps probe pilot/m2-t1-sparse-blunt --workspace-base /tmp/pb --runs 5 --seed pilot/seed-ws

# apply the Stage-0 decision rule
python3 pilot_analysis.py
```

## Stage-0 discipline (spec §5)

The pilot runs BEFORE anything beyond the corpus operators gets built. Decision
rule, pre-registered: if T1 and T3/T4 do not separate (Wilson overlap AND
cycles-to-green indistinguishable), H1 is dead-on-arrival in this regime — stop,
report the early kill, do not build the sweep. `dotmaps ladder` / `dotmaps sweep`
are deliberately absent from the CLI until Stage 0 passes.
