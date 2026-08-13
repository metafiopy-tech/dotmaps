"""LIVE — Q7 (optional): subscription-billed live dispatch.

The ONLY module in this package that makes a model call, and nothing else
in the package imports it (dispatch.py, sleep.py, surface.py, governor.py
stay live-blind by construction). Explicit opt-in only:

    dotmaps queen <target> --live --driver claude-code

MONEY LAW: never wires AnthropicLearner. `--driver` accepts exactly one
value, claude-code — the subscription-billed ClaudeCodeLearner (grow/
learner.py). If ANTHROPIC_API_KEY is set in the environment, the learner
itself strips it before shelling out, so a present key is never used.

The frontier plan from dispatch() stands as-is; live growth is offered as
a SEPARATE step on top of it, capped by a deliberately tiny default
budget — this is a smoke test, not a growth campaign.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..grow.clock import ClockConfig
from ..grow.learner import ClaudeCodeLearner
from ..grow.runner import grow
from . import dispatch as dispatch_mod
from . import trips as trips_mod

# Q7 smoke budget: as small as the wheel allows while still exercising a
# real propose/confirm cycle. Each learner call is a real subscription-
# billed call (~$0.02-0.07 observed during diagnosis) — this is a smoke
# test, not a growth campaign.
TINY_LIVE_BUDGET = ClockConfig(max_pokes=3, max_spirals=1, forage_attempts=1,
                               max_fetches=1)

# Human-authorized growth (a resolved "grow now" ESCALATE): a real budget.
# ~run-005 scale; each call subscription-billed. Flight-2 finding: a 3-poke
# smoke cannot close deep predicates — authorization means a campaign.
AUTHORIZED_BUDGET = ClockConfig(max_pokes=60, max_spirals=2)


def live_dispatch(target: str, *, driver: str = "claude-code",
                   model: str = "claude-sonnet-5",
                   cfg: ClockConfig | None = None,
                   trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                   run_dir: Path | None = None,
                   authorized: bool = False) -> dict[str, Any]:
    if driver != "claude-code":
        raise ValueError(
            "live dispatch only supports --driver claude-code — "
            "AnthropicLearner/API-key billing is out of scope, ever (MONEY LAW)")

    t = dispatch_mod.resolve_target(target)
    cfg = cfg or (AUTHORIZED_BUDGET if authorized else TINY_LIVE_BUDGET)
    plan = dispatch_mod.dispatch(target, trips_path=trips_path, cfg=cfg)
    if not plan["frontier"]:
        return {**plan, "live": False,
                "note": "nothing frontier to grow — the dry-run plan stands"}

    # Flight-3 fix: the directive must reach the workspace the learner
    # actually flies (flight 3 reused an old agent-ws and never saw the
    # targets). Copy the seed to a temp workspace, write the directive
    # THERE, and fly from a fresh numbered run_dir every authorized flight.
    workspace = Path(t["workspace"])
    targets = [f["statement"] for f in plan["frontier"] if f.get("statement")]
    if authorized and targets:
        import shutil as _sh, tempfile as _tf
        ws_copy = Path(_tf.mkdtemp(prefix="queen-authorized-")) / "ws"
        _sh.copytree(workspace, ws_copy)
        board = ws_copy / ".dotmaps" / "approved_board.txt"
        base = board.read_text() if board.exists() else ""
        board.parent.mkdir(exist_ok=True)
        board.write_text(base.rstrip() + "\n\n" +
            "AUTHORIZED MISSION (do-then-verify):\n"
            "1. PERFORM the migration described by migration.json — read the\n"
            "   source, write the migrated target file it specifies.\n"
            "2. THEN bank rules whose statement text is EXACTLY, verbatim:\n" +
            "\n".join(f"   - {x}" for x in targets) + "\n"
            "A rule matching one of these statements verbatim, confirmed\n"
            "against the migrated workspace, is the mission. Fine-grained\n"
            "source invariants are already covered — do not re-bank them.\n")
        workspace = ws_copy

    learner = ClaudeCodeLearner(model=model)
    if run_dir:
        run_dir = Path(run_dir)
    else:
        base = trips_mod.REPO_ROOT / "runs" / "queen-live" / t["name"]
        if authorized:
            n = 1
            while (base.parent / f"{t['name']}-auth{n:02d}").exists():
                n += 1
            run_dir = base.parent / f"{t['name']}-auth{n:02d}"
        else:
            run_dir = base
    summary = grow(workspace, run_dir, learner, cfg=cfg)

    return {**plan, "live": True, "driver": driver, "model": model,
            "learner_usd_estimate": round(learner.usd_estimate, 4),
            "grow_summary": summary, "run_dir": str(run_dir)}
