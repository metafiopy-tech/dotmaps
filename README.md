# Dot Maps

**A harness that catches agents lying about their work — with receipts you
can replay.**

Three local models were caught cheating in three different ways by the same
mechanism, and every conviction is bundled in this repo as an append-only
journal you can watch offline, no API keys, no models installed:

- A 3B model wrote empty artifacts and narrated success for 30 straight
  cycles while the board stayed red (`runs/repro-3b-circular/`; the original
  episode — a fabricated `{"item_count":1,...}` claim-file, 150 red cycles —
  is documented in `corpus/pilot_report.md`, Stage-0b addendum).
- A 7B model, given a learning loop that banks rules when their checks pass,
  discovered the check that passes on anything and banked 18 counterfeit
  rules — all 18 convicted by a 3-line integrity gate
  (`runs/grow-001/`, `grow/RUNS.md` run 001).
- A 7B *traveler*, wall-blocked from deleting a protected source file,
  deleted its own deliverable instead — the blocked-action displacement
  finding (`corpus/pilot_interim_notes.md`, finding 3; no machine journal
  exists — attempt-journaling was added to the harness *because* of this
  episode).

## Watch it yourself (5 commands, ~2 minutes, no models)

```bash
git clone https://github.com/metafiopy-tech/dotmaps.git && cd dotmaps
pip install -e .
dotmaps replay runs/repro-3b-circular      # a 3B narrates success; the board stays red
dotmaps replay runs/grow-001               # a 7B reward-hacks its own science
dotmaps attack maps/map-seq --seed maps/map-seq/examples/seed-ws   # 4 adversaries: HARDENED
```

Every journal in `runs/` is an unedited append-only log from a real run —
see [runs/README.md](runs/README.md) for the full index, including the one
honest gap.

## The five rules

1. A map is a valid DAG whose dots carry runnable verifiers.
2. The event log is append-only — agents read the board, never the raw past.
3. Illegal actions are absent from the action space, not discouraged.
4. Agent claims of completion are ignored — verifiers are sovereign.
5. Errors surface as errors; nothing false ships on a green label.

## What a map is

A **map** decomposes a task into **dots** — promises about world-state, each
with its own verifier script. A **traveler** (any model; deliberately the
most replaceable part) acts through whitelisted tool **walls** to make
promises true. The **sovereign verifier** — the only component that runs
verifier code — decides what's done. The board goes green when the world
says so, never when the agent does.

Proof it works end-to-end: `maps/map-content-migration` was completed live
by qwen2.5-coder:7b (a $0 local model) and probe-certified 5/5 with a Wilson
95% interval of [0.57, 1.00]
(`maps/map-content-migration/certification/probe_stats.json`).

## Can an agent grow its own map?

The POKE loop (`dotmaps grow`) asks a model to learn a cold environment with
no task description and no oracle: poke, propose rules with checks, bank
only what a fresh replay of the check confirms — then the grown map is
judged by the same gates as hand-made maps.

- **Local models (7B, 14B): no.** One reward-hacked the gate, one fogged out
  when the hack was blocked, one never proposed a rule at all
  (`grow/RUNS.md`, runs 001–004; journals in `runs/`).
- **A frontier model (claude-sonnet-5): yes** — 4 discriminating rules
  banked, ~20 false hypotheses fogged, and the first grown map to clear the
  readout with zero circular checks, probe-certified 5/5 for $0.50
  (`runs/grow-005/`). **The asterisks, adjacent where they belong:** all
  four grown dots are seed *invariants* (already true on a fresh workspace,
  so the probe certification is vacuous as a traversability claim); the
  overlap with the withheld human-made map is genuine but shallow (source
  integrity only — it never discovered the write side); and this is n=1 on
  one environment. It is a real first step, reported at its real size.


## The EQUIP campaign: one week, five experiments, 52 paired runs, ~$60

The follow-up question — *does certified knowledge compound?* — got a full
pre-registered experimental campaign (spec: [EQUIP_v1_spec.md](EQUIP_v1_spec.md)).
Every kill criterion was written before the code ran; every verdict is
graded against the frozen registration and committed under `runs/`.

**What held up:**

- **Pay once, free forever.** A frontier model's $0.50 lesson replays at
  $0.00 via certificates — an equipped traversal completed a learned map
  4/4 with zero model calls (`skills/`, gate G3 commit).
- **Certification discriminates.** 4/4 planted-flaw skills convicted blind;
  a vacuous skill convicted unprompted by the oracle gate
  ([runs/e2-certification-discriminates/](runs/e2-certification-discriminates/report.json)).
- **Inheritance is a frontier-depth instrument, 12× measured.** Equipped
  agents produced 63 mutation/boundary-probing rules vs cold's 5 in the
  final trial; frontier reach held in 12 of 13 equipped arms across three
  trials ([runs/e1d-verdict/](runs/e1d-verdict/verdict.json)).
- **Mechanical gates beat informational surfacing.** Bank-time dedup:
  36/36 runs clean. The in-flight proposal gate eliminated retry churn
  entirely (0 re-fogs in all 16 final runs, 99 blocks) after two trials of
  board-surfacing only half-worked.

**What died — published at the same size:**

- **The efficiency claim is dead, permanently, by its own pre-registered
  final-trial clause.** Four trials, 26 pairs: inheritance never made
  agents cheaper per unit of knowledge, and in the cleanest instrument it
  was 16% more expensive
  ([runs/e1-verdict/](runs/e1-verdict/verdict.json) →
  [e1b](runs/e1b-verdict/verdict.json) →
  [e1c](runs/e1c-verdict/verdict.json) →
  [e1d](runs/e1d-verdict/verdict.json)).
- The apparent early discount was churn-avoidance in disguise: eliminate
  churn for every arm and the savings evaporate.
- Per-run variance (17–58 unique rules under identical conditions) dwarfs
  the inheritance effect at small n.

All 46+ grown maps across the program passed validity gates with **zero
circular checks, ever**. Interactive demo of the instrument:
[try it — your words become the test](https://metafiopy-tech.github.io/dotmaps/try.html) ·
[the instrument & paper skeleton](https://metafiopy-tech.github.io/dotmaps/instrument.html) ·
[case study: four rounds to certification](docs/case-study-closing-procedure.md).

## What's in the box

| path | contents |
|---|---|
| `dotmaps/` | the harness: compiler, runtime + walls, sovereign verifier, scoreboard, probe/attack/replay, POKE loop |
| `maps/` | four maps, including the live-certified migration map and the sequential publish chain |
| `runs/` | bundled convictions and milestones — replay offline |
| `corpus/` | the experiment layer: variant generator, frozen registrations, pilot reports with raw stats |
| `grow/` | the POKE loop's frozen directive, run log, and cold seed |
| `docs/` | the full write-up, launch page, live demo pages |
| `skills/` | the first certified skill cards + manifest (EQUIP gates G1–G2) |
| `experiments/` | EQUIP registrations (E1b/c/d) and the paired-run harness |
| `STATUS.md` | the project ledger, kept as it was written |

The full story — every experiment, every pre-registered verdict, every
finding — is in [docs/hull-v0.1-writeup.md](docs/hull-v0.1-writeup.md).
The registrations and raw run data are included unmodified; where a claim
appears in this README, its evidence file is cited inline.

## Honest limits, up front

- The certification instrument (weak-probe road grading, H1) is **closed at
  owned model rungs**: every local model either flew over the test maps or
  couldn't walk them (`corpus/pilot_report.md`, window-assay addendum).
  Certification today = probe pass rate + Wilson interval + attack verdict.
  No instrument score is claimed.
- `dotmaps attack` codifies four adversaries observed or built to date. It
  is a floor, not a ceiling.
- Docker-mode verification (read-only mounts) requires a working Docker
  daemon; local mode is the default everywhere else.

## License

MIT — see [LICENSE](LICENSE).
