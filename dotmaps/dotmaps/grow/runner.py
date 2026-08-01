"""The wheel: POKE -> FORAGE -> METABOLIZE, spiraling, budgeted, resumable.

SANDBOX and beyond are deliberately NOT here — the grown map is judged by the
existing pipeline (`dotmaps run/probe` + the integrity gate), with no special
treatment. That separation IS the experiment design.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .banking import confirm, already_banked, already_fogged, dot_eligible, run_steps, validate_rule
from .clock import ClockConfig, PhaseClock
from .metabolize import grow_map
from .store import GrowStore

DIRECTIVE_PATH = Path(__file__).parent.parent.parent.parent / "grow" / "DIRECTIVE.md"


def load_directive() -> str:
    """The frozen, goal-free standing directive (between the --- markers)."""
    text = DIRECTIVE_PATH.read_text()
    parts = text.split("---")
    if len(parts) >= 3:
        return parts[1].strip()
    raise RuntimeError(f"directive file {DIRECTIVE_PATH} is malformed")


def board_context(directive: str, store: GrowStore, clock: PhaseClock,
                  phase: str, workspace: Path) -> str:
    obs_w = clock.cfg.obs_window
    """Rule-2 context: board + tail, never the full journal."""
    lines = [directive, ""]
    listing = sorted(p.name for p in workspace.iterdir()
                     if not p.name.startswith("."))
    lines.append(f"Workspace files: {', '.join(listing) or '(empty)'}")
    prims = store.primitives()
    # E1 finding F-E1a: a 20-line tail let knowledge scroll off the board and
    # the learner re-derived it (dup counts 14,2,8,1,33). The board now shows
    # EVERY banked statement, compact — self-knowledge must not truncate.
    lines.append(f"\nBanked rules ({len(prims)}) — already known, do NOT re-propose:")
    for r in prims:
        lines.append(f"  [{r['id']}] {r['statement']}")
    # E1 finding F-E1b: fog was written to disk and never shown back; the
    # learner re-proposed undecidable hypotheses 10-40x per run (churn walls).
    fogged = store.fogged_statements()
    if fogged:
        lines.append(f"\nFOGGED — undecidable by this agent, do NOT re-propose "
                     f"({len(fogged)}):")
        for st in fogged[-30:]:
            lines.append(f"  ✕ {st}")
    hyps = store.open_hypotheses()
    lines.append(f"\nOpen hypotheses ({len(hyps)}):")
    for h in hyps[-10:]:
        lines.append(f"  [{h['id']}] {h['statement']}")
    lines.append(f"\nRecent pokes:")
    for rec in store.journal_tail(8):
        act = rec["action"]
        lines.append(f"  {act.get('tool')}({act.get('args')}) -> "
                     f"{rec['observation'][:obs_w]}")
    lines.append(f"\nPhase: {phase}. Pokes used: {clock.pokes}/"
                 f"{clock.cfg.max_pokes}. Rules banked: {clock.banked}.")
    return "\n".join(lines)


def grow(seed_dir: str | Path, run_dir: str | Path, learner,
         cfg: ClockConfig | None = None, say=print) -> dict[str, Any]:
    """Run the wheel. Returns a summary dict; the grown map (if any) lands at
    <run_dir>/grown-map/."""
    seed = Path(seed_dir).resolve()
    store = GrowStore(run_dir)
    cfg = cfg or ClockConfig()
    directive = load_directive()

    # the agent's working copy — pokes land here; banking NEVER consults it
    workspace = store.root / "agent-ws"
    if not workspace.exists():
        shutil.copytree(seed, workspace)

    rule_seq = len(store.primitives()) + len(store.open_hypotheses())
    summary: dict[str, Any] = {"spirals": []}

    for spiral in range(1, cfg.max_spirals + 1):
        clock = PhaseClock(cfg)
        phase = "POKE"
        say(f"— spiral {spiral} —")
        while True:
            if clock.should_metabolize(len(store.open_hypotheses())):
                break
            if phase == "POKE" and clock.should_forage(len(store.open_hypotheses())):
                phase = "FORAGE"
                say(f"  clock: POKE->FORAGE at poke {clock.pokes}")

            if phase == "FORAGE":
                _forage(store, clock, learner, directive, seed, workspace, say)
                phase = "POKE"  # forage resolves/fogs, then the wheel re-checks
                continue

            board = board_context(directive, store, clock, phase, workspace)
            move = learner.next_move(board)

            if move.get("rest"):
                say(f"  learner rests at poke {clock.pokes}")
                break
            if "poke" in move:
                action = move["poke"]
                obs = run_steps({"steps": [action]}, workspace)
                # mechanical truth, not coaching: an exact repeat is labeled
                # as one, so the board itself shows the learner it is looping
                recent = [r["action"] for r in store.journal_tail(5)]
                if action in recent:
                    obs = "(repeat of an earlier poke — no new information) " + obs
                clock.tick_poke()
                n = store.journal_poke(spiral, action, obs)
                store.log_novelty(spiral, n, clock.banked, phase)
                continue
            if "propose" in move:
                rule = dict(move["propose"])
                rule_seq += 1
                rule["id"] = f"r{rule_seq:03d}"
                problem = validate_rule(rule)
                clock.tick_poke()  # proposals consume budget too
                if problem:
                    store.journal_poke(spiral, {"tool": "propose",
                                                "args": {"id": rule["id"]}},
                                       f"REJECTED: {problem}")
                    continue
                if already_fogged(rule, store.fogged_statements()):
                    store.journal_poke(spiral, {"tool": "propose",
                                                "args": {"id": rule["id"]}},
                                       "FOG-BLOCKED: statement already fogged — not re-proposed")
                    say(f"  FOG-BLOCKED [{rule['id']}]")
                    continue
                dup = already_banked(rule, store.primitives())
                if dup:
                    store.journal_poke(spiral, {"tool": "propose",
                                                "args": {"id": rule["id"]}},
                                       f"DUPLICATE of banked [{dup}] — not re-banked")
                    say(f"  DUPLICATE [{rule['id']}] = banked [{dup}]")
                    continue
                store.add_hypothesis(rule)
                ok, obs = confirm(rule, seed)
                n = store.journal_poke(spiral, {"tool": "confirm",
                                                "args": {"id": rule["id"]}},
                                       ("CONFIRMED: " if ok else "UNCONFIRMED: ")
                                       + obs[:300])
                if ok:
                    store.bank_primitive(rule, journal_ref=n, spiral=spiral)
                    store.resolve_hypothesis(rule["id"], "banked")
                    clock.tick_bank()
                    say(f"  BANKED [{rule['id']}] {rule['statement'][:70]}")
                store.log_novelty(spiral, n, clock.banked, phase)
                continue
            break  # unrecognized move: treat as rest

        # spiral is ending: every open hypothesis gets its forage shot, and
        # what doesn't resolve FOGS — nothing is silently dropped (spec 2.2)
        if store.open_hypotheses():
            _forage(store, clock, learner, directive, seed, workspace, say)

        summary["spirals"].append({"spiral": spiral, "pokes": clock.pokes,
                                   "banked_total": len(store.primitives())})
        if not store.open_hypotheses() and spiral > 1:
            break  # nothing new to chase; stop spiraling early

    # METABOLIZE
    prims = store.primitives()
    eligible = [r for r in prims if dot_eligible(r)]
    say(f"metabolize: {len(prims)} primitives, {len(eligible)} dot-eligible")
    fog_lines = None
    fog_file = store.root / "fog.md"
    if fog_file.exists():
        fog_lines = [l for l in fog_file.read_text().splitlines()
                     if l.startswith("- ")]
    if eligible:
        map_dir = grow_map(prims, store.root / "grown-map",
                           env_name=seed.name, fog_lines=fog_lines)
        summary["grown_map"] = str(map_dir)
        say(f"grown map -> {map_dir}")
    else:
        summary["grown_map"] = None
        say("no dot-eligible primitives; nothing grown")
    summary["primitives"] = len(prims)
    return summary


def _forage(store: GrowStore, clock: PhaseClock, learner, directive: str,
            seed: Path, workspace: Path, say) -> None:
    """FORAGE v0: each open hypothesis gets up to M revision attempts (the
    learner may consult fetch.get in revised steps); still-unconfirmed
    hypotheses are FOGGED, never silently dropped. Research proposes; the
    world disposes."""
    for hyp in store.open_hypotheses():
        resolved = False
        for attempt in range(clock.cfg.forage_attempts):
            if not clock.fetch_budget_left():
                break
            clock.tick_fetch()
            board = board_context(directive, store, clock, "FORAGE", workspace)
            board += (f"\n\nThis hypothesis did not confirm: "
                      f"[{hyp['id']}] {hyp['statement']}\n"
                      f"Steps tried: {hyp['steps']}\nExpected: {hyp['expect']}\n"
                      f"Revise it (or its check) so a fresh replay can confirm it.")
            move = learner.next_move(board)
            revised = move.get("revise") or move.get("propose")
            if not revised:
                continue
            rule = {**revised, "id": hyp["id"]}
            if validate_rule(rule):
                continue
            if already_fogged(rule, store.fogged_statements()):
                store.resolve_hypothesis(rule["id"], "fog-blocked")
                continue
            if already_banked(rule, store.primitives()):
                store.resolve_hypothesis(rule["id"], "duplicate")
                continue
            ok, obs = confirm(rule, seed)
            n = store.journal_poke(0, {"tool": "confirm-revised",
                                       "args": {"id": rule["id"]}},
                                   ("CONFIRMED: " if ok else "UNCONFIRMED: ")
                                   + obs[:300])
            if ok:
                store.bank_primitive(rule, journal_ref=n, spiral=0)
                store.resolve_hypothesis(rule["id"], "banked")
                clock.tick_bank()
                say(f"  BANKED (forage) [{rule['id']}]")
                resolved = True
                break
        if not resolved:
            store.resolve_hypothesis(hyp["id"], "fogged")
            store.fog(hyp["statement"], "no confirming poke after forage")
            say(f"  FOGGED [{hyp['id']}] {hyp['statement'][:60]}")
