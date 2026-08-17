"""WORK ORDER — Q8: DO, mechanically separated from VERIFY.

Flight 4's finding (QUEEN_FLIGHT_LOG.md, "Human flights 1-4"): a mission
written as board text is advice, and advice loses to mechanism (36/36 vs
5/10). The five migration dots describe a COMPLETED migration; verification-
-only growth cannot make them true — something has to actually DO the
migration first. So execution becomes its own phase, upstream of growth:

  1. Copy the target's seed workspace to a fresh temp dir (never the repo's
     committed seed — same disposable-copy pattern as bank/certify.py).
  2. Run the FULL agentic Claude Code (tools ON — this is what the persona
     is for, unlike grow/learner.py's ClaudeCodeLearner which strips the
     persona down to a bare move generator) via `claude -p`, scoped to that
     workspace by cwd, with ONE job composed from the map: "Perform the
     task described by <config>. Work only inside this directory."
     Subscription-billed, budget-capped (--max-turns, wall-clock timeout).
  3. MECHANICAL COMPLETION GATE, not self-report: after the run, the map's
     own frozen dot verifiers (verifier/runner.py, local mode — reused
     unmodified) are the sole authority on whether the workspace is done.
     Gate fails -> WORK_ORDER phase=failed trip ("WORK_ORDER_FAILED") and
     `ok=False`; the caller (queen/live.py, Q9) must never proceed to
     growth on an incomplete workspace.

MONEY LAW: this module makes a real model call (like queen/live.py, Q7) —
it is never imported by dispatch.py/sleep.py/surface.py/governor.py, and it
only runs under an explicit `--authorized` live dispatch.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml

from ..models import Map
from ..verifier.runner import Verifier
from . import dispatch as dispatch_mod
from . import runner_adapter as runner_adapter_mod
from . import trips as trips_mod

WORK_ORDER_MODEL = "claude-sonnet-5"
WORK_ORDER_MAX_TURNS = 30
WORK_ORDER_TIMEOUT_S = 1800  # 30 min wall-clock cap, independent of --max-turns

# Config filenames this organ knows how to name explicitly in the job text
# (the verifiers' own read contract, e.g. bank/_lib.py's load()). Falls back
# to the first *.json file found in the workspace root for any future
# preset that doesn't match — the dot statements below carry the real
# acceptance criteria either way.
KNOWN_CONFIGS = ("migration.json",)


def _discover_config(workspace: Path) -> str:
    for name in KNOWN_CONFIGS:
        if (workspace / name).exists():
            return name
    jsons = sorted(p.name for p in workspace.glob("*.json"))
    return jsons[0] if jsons else "the files in this directory"


def compose_job(map_dir: Path, workspace: Path) -> str:
    """ONE job, composed from the map — never invented per-run. The
    acceptance criteria are the map's own dot statements, so this text
    cannot drift from what the mechanical gate below actually checks."""
    m_data = yaml.safe_load((Path(map_dir) / "map.yaml").read_text())
    config = _discover_config(workspace)
    lines = [
        f"Perform the task described by {config}. Work only inside this directory.",
        "",
        f"Domain: {m_data.get('domain') or m_data.get('name')}",
        "",
        "When you finish, the following will be checked MECHANICALLY against "
        "this workspace's files (there is no self-report step — do not "
        "announce completion, just make these true):",
    ]
    for d in m_data.get("dots", []):
        lines.append(f"  - {d['statement']}")
    return "\n".join(lines)


# H8 (HARDENING_BRIEF): subprocess construction + CLI output-field reading
# now lives in queen/runner_adapter.py's ClaudeCliAdapter, one version-
# pinned contract shared with chat.py instead of two hand-rolled ones.
_adapter = runner_adapter_mod.ClaudeCliAdapter()


def _run_agentic(workspace: Path, job: str, *, model: str, max_turns: int,
                  timeout_s: int) -> dict[str, Any]:
    """The full agentic Claude Code, tools ON, via the local `claude` CLI —
    subscription-billed. Scoped to `workspace` by cwd, no --add-dir, so no
    tool call can reach outside it (though cwd alone is not OS isolation —
    see queen/sandbox.py for the real boundary: an empty-allowlist child
    env, not a wholesale os.environ passthrough, plus a real docker mode
    when configured). `--dangerously-skip-permissions` is required for a
    non-interactive `-p` run to actually write files; it is safe here
    because `workspace` is always a disposable temp copy, never the repo."""
    return _adapter.run(workspace, job, model=model, max_turns=max_turns, timeout_s=timeout_s)


def mechanical_completion_gate(map_dir: Path, workspace: Path) -> dict[str, Any]:
    """Cheap, mechanical probes against the workspace — never self-report.
    Reuses the map's own frozen dot verifiers (verifier/runner.py, local
    mode) unmodified: for this preset every dot is stdlib-only and
    file-local (no docker, no network — map-content-migration's
    internal_link_base is null), so running the FULL manifest still counts
    as 'cheap probes where derivable'. A dot the run never touched (e.g. no
    target file written) fails exactly like a broken one — there is no
    partial credit for a claim, only for a passing predicate."""
    m = Map.load(map_dir)
    results = Verifier.for_map(m, mode="local").run_full_manifest(m, workspace)
    dots = [{"dot": r.dot, "passed": r.passed, "evidence": r.evidence,
             "errored": r.errored} for r in results]
    return {"passed": all(d["passed"] for d in dots), "dots": dots}


def run_work_order(target: str, *, model: str = WORK_ORDER_MODEL,
                    max_turns: int = WORK_ORDER_MAX_TURNS,
                    timeout_s: int = WORK_ORDER_TIMEOUT_S,
                    trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                    _runner: Callable[..., dict[str, Any]] = _run_agentic
                    ) -> dict[str, Any]:
    """DO, mechanically separated from VERIFY. Returns before any growth
    touches the workspace — queen/live.py (Q9) decides what happens next,
    and never proceeds to growth when `ok` is False.

    `_runner` is injectable so the wiring (temp workspace -> job -> gate ->
    trip) is pytest-covered deterministically and for free; the real
    subscription-billed agentic call is exercised live, once, the same
    convention Q7 used for ClaudeCodeLearner's live path."""
    t = dispatch_mod.resolve_target(target)
    map_dir = Path(t["map"]).parent
    seed = Path(t["workspace"])

    workspace = Path(tempfile.mkdtemp(prefix="queen-workorder-")) / "ws"
    shutil.copytree(seed, workspace)

    job = compose_job(map_dir, workspace)
    trips_mod.emit("WORK_ORDER", path=trips_path, phase="start", target=t["name"],
                   workspace=str(workspace), max_turns=max_turns)

    claude_result = _runner(workspace, job, model=model, max_turns=max_turns,
                            timeout_s=timeout_s)
    gate = mechanical_completion_gate(map_dir, workspace)
    # H1 (defense-in-depth, see queen/chat.py's _chat_gate): the gate re-runs
    # the map's own real verifiers, so it already re-derives truth rather than
    # trusting self-report — but a subtype!=success run must never count as ok
    # even if the workspace happens to already satisfy the verifiers.
    ok = bool(gate["passed"]) and bool(claude_result.get("ok"))

    if ok:
        trips_mod.emit("WORK_ORDER", path=trips_path, phase="complete",
                       target=t["name"], workspace=str(workspace), gate=gate,
                       claude=claude_result)
    else:
        trips_mod.emit("WORK_ORDER", path=trips_path, phase="failed",
                       target=t["name"], workspace=str(workspace), gate=gate,
                       claude=claude_result,
                       reason="WORK_ORDER_FAILED — mechanical completion gate "
                              "did not pass; never proceeding to growth on an "
                              "incomplete workspace")

    return {"target": t["name"], "workspace": str(workspace), "job": job,
            "claude": claude_result, "gate": gate, "ok": ok}


if __name__ == "__main__":
    import sys
    print(json.dumps(run_work_order(sys.argv[1]), indent=2, default=str))
