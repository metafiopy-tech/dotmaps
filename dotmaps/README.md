# dotmaps

**A harness where an agent's word counts for nothing.**

A *map* decomposes a task into *dots* — promises about world-state, each with
its own verifier script. A *traveler* (any model; deliberately the most
replaceable part) acts through whitelisted tool *walls* to make the promises
true. A *sovereign verifier* — the only thing that runs verifier code — reads
the world each cycle. The scoreboard is append-only. **The board goes green
when the verifiers say so, never when the agent does.**

Five rules, no exceptions:

1. A map is a valid DAG whose dots carry runnable verifiers.
2. The event log is append-only; agents read the board, never the raw past.
3. Illegal actions are absent from the action space, not discouraged.
4. Agent claims of completion are ignored; verifiers are sovereign.
5. Errors surface as errors; nothing false ships on a green label.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -e .

# watch a scripted traveler cross the smoke map
.venv/bin/dotmaps run ../maps/map-smoke --workspace /tmp/smoke-ws

# run a real map with a free local model (needs ollama + qwen2.5-coder:7b)
.venv/bin/dotmaps run ../maps/map-content-migration \
    --workspace /tmp/migrate-ws --driver ollama

# read the run as a story — every attempt, every tool call, every verdict
.venv/bin/dotmaps replay /tmp/migrate-ws
```

## The certification stamp

A map earns its stamp with two artifacts, both regenerated on every version
change:

```bash
# probe: N fresh weak-traveler runs -> pass rate with Wilson 95% bounds
.venv/bin/dotmaps probe <map> --workspace-base /tmp/probe --runs 5 --seed <seed-ws>

# attack: four adversarial attempts to earn a false green
.venv/bin/dotmaps attack <map> --seed <seed-ws>
```

The attack suite tries: dots green with no work done; dots surviving a
corrupted workspace; writes through the protected-path walls; and planted
completion-claim files (`DONE.txt`, `status.json` — a real 3B model's actual
attack, observed live, replayed deliberately on every certification).
Verdict `HARDENED` requires all four repelled.

## Commands

| command | what it does |
|---|---|
| `run` | traverse a map (scripted / anthropic / ollama traveler; `--dry-run` stages) |
| `verify` | one sovereign verification pass, no traveler |
| `compile` | intake dialogue → workspace config + board approval |
| `probe` | N-run certification with Wilson intervals |
| `attack` | adversarial certification → `attack_report.json` |
| `replay` | render a workspace's event log as a readable story |
| `connect` | prompt for + live-verify tokens for a map's external services |
| `corpus` | build planted-quality map variants (research tooling) |
| `grow` / `readout` | the POKE loop: grow a map from a cold environment |
| `board` / `audit` | scoreboard summary · secrets scan |

## Repo layout

Maps live beside the package (`../maps/*` — each is `map.yaml` + `verifiers/`
+ examples). Research artifacts (pilot registrations, verdicts, run logs)
live in `../corpus/` and `../grow/`. The full project report: `../REPORT.md`.

Runtime is stdlib-only. The traveler is replaceable; the verifier is not
negotiable.
