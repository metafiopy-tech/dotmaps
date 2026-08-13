"""LIVE — Q7 (optional) + Q9: subscription-billed live dispatch.

The ONLY module in this package that makes a model call (together with
workorder.py, which it now drives) — nothing else in the package imports
either (dispatch.py, sleep.py, surface.py, governor.py stay live-blind by
construction). Explicit opt-in only:

    dotmaps queen <target> --live --driver claude-code [--authorized]

MONEY LAW: never wires AnthropicLearner. `--driver` accepts exactly one
value, claude-code — the subscription-billed ClaudeCodeLearner (grow/
learner.py). If ANTHROPIC_API_KEY is set in the environment, the learner
itself strips it before shelling out, so a present key is never used.

The frontier plan from dispatch() stands as-is; live growth is offered as
a SEPARATE step on top of it, capped by a deliberately tiny default
budget — this is a smoke test, not a growth campaign.

Q9 (DO then VERIFY, per flight 4's finding): an AUTHORIZED dispatch first
runs the Q8 work order — the full agentic Claude Code actually PERFORMING
the task in a temp workspace, mechanically gated on completion — and only
if that gate passes does growth proceed, targeted at the SAME completed
workspace (never a fresh, unmigrated copy). If the gate fails, live
dispatch stops: WORK_ORDER_FAILED already trip'd by workorder.py, and no
growth runs against an incomplete workspace.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..grow.clock import ClockConfig
from ..grow.learner import ClaudeCodeLearner
from ..grow.runner import grow
from . import dispatch as dispatch_mod
from . import trips as trips_mod
from . import workorder as workorder_mod

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
                   authorized: bool = False,
                   _work_order: Any = workorder_mod.run_work_order
                   ) -> dict[str, Any]:
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

    workspace = Path(t["workspace"])
    targets = [f["statement"] for f in plan["frontier"] if f.get("statement")]
    work_order = None
    if authorized and targets:
        # Q8/Q9 — DO before VERIFY: perform the task for real, in a fresh
        # temp workspace, mechanically gated, BEFORE any growth touches it.
        work_order = _work_order(target, trips_path=trips_path)
        if not work_order["ok"]:
            return {**plan, "live": False, "work_order": work_order,
                    "note": "WORK_ORDER_FAILED — mechanical completion gate "
                            "did not pass; growth never ran on an incomplete "
                            "workspace"}

        # Growth targets the SAME completed workspace the work order just
        # produced — never a fresh, unmigrated copy (flight 4's mistake).
        workspace = Path(work_order["workspace"])
        board = workspace / ".dotmaps" / "approved_board.txt"
        base = board.read_text() if board.exists() else ""
        board.parent.mkdir(exist_ok=True)
        board.write_text(base.rstrip() + "\n\n" +
            "AUTHORIZED MISSION (do-then-verify):\n"
            "This workspace has ALREADY been migrated by a completed, "
            "mechanically-gated work order (queen/workorder.py). Bank rules "
            "whose statement text is EXACTLY, verbatim:\n" +
            "\n".join(f"   - {x}" for x in targets) + "\n"
            "A rule matching one of these statements verbatim, confirmed "
            "against this (already-migrated) workspace, is the mission. "
            "Fine-grained source invariants are already covered — do not "
            "re-bank them.\n")

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

    out = {**plan, "live": True, "driver": driver, "model": model,
           "learner_usd_estimate": round(learner.usd_estimate, 4),
           "grow_summary": summary, "run_dir": str(run_dir)}
    if work_order is not None:
        out["work_order"] = work_order
    return out
