"""The outer loop — owns lifecycle, budget, and termination (rule 4).

This is the whole runtime, honestly. It mirrors the reference loop in spec §4b:

    board = Scoreboard.load_or_init(workspace)        # rule 2: resume == replay
    while board.budget_remaining(budget):
        results = Verifier.run_full_manifest(map, ws) # rule 4: FULL board / cycle
        board.reconcile(results)                      #         (catches regressions)
        if board.all_green(): return end("all_green")
        dot = Selector.next_uneaten(board, dots)      # deps-aware
        Traveler.attempt(dot, map, ws)                # rules 3+5 by mounts/registration
        board.log_attempt(dot)
    return end("budget_exhausted")

Only THIS process writes the terminal event. The traveler's claims of
completion are never parsed for control flow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..models import END_ALL_GREEN, END_BUDGET, Map
from ..safety import gates
from ..scoreboard.state import Scoreboard
from ..verifier.runner import Verifier
from .selector import Selector
from .traveler import Traveler


class Orchestrator:
    def __init__(self, m: Map, workspace: str | Path, verify_mode: str = "local",
                 verbose: bool = True, dry_run: bool = False,
                 gate_config: Optional[gates.GateConfig] = None):
        self.map = m
        self.workspace = Path(workspace).resolve()
        self.verifier = Verifier.for_map(m, mode=verify_mode)
        self.verbose = verbose
        self.dry_run = dry_run
        self.gates = gate_config or gates.GateConfig(dry_run=dry_run)

    def run(self, resume: bool = False) -> Scoreboard:
        problems = self.map.validate()
        if problems:
            raise ValueError("map failed validation:\n  - " + "\n  - ".join(problems))

        self.workspace.mkdir(parents=True, exist_ok=True)
        board = Scoreboard.load_or_init(self.workspace, self.map)
        if board.ended and not resume:
            self._say(f"run already ended ({board.ended}); pass resume=True to continue")
            return board
        board.ended = None  # a resume reopens the run
        board.start_run(self.map)

        # dots blocked by the destructive gate stay blocked for the whole run —
        # a declined confirm is a decision, not a per-cycle question.
        blocked: set[str] = set()

        while board.budget_remaining(self.map.budget):
            board.start_cycle()
            # rule 4: re-verify the ENTIRE manifest every cycle
            results = self.verifier.run_full_manifest(self.map, self.workspace)
            board.reconcile(results)
            self._report_cycle(board, results)

            if board.all_green(self.map):
                return board.end(END_ALL_GREEN)

            # gate check (Phase 2): destructive dots need dry-run, human confirm,
            # or an explicit per-run --allow-destructive. Blocked dots are
            # skipped this run — never silently attempted.
            dot = Selector.next_uneaten(board, self.map.dots, skip=blocked)
            while dot is not None and gates.guard(dot, self.gates) == gates.BLOCK:
                self._say(f"  gate: dot {dot.id} is destructive and unconfirmed — skipping")
                blocked.add(dot.id)
                dot = Selector.next_uneaten(board, self.map.dots, skip=blocked)
            if dot is None:
                # no eligible dot but not all green: dependency deadlock, all
                # remaining dots gate-blocked, or a dot the traveler cannot
                # satisfy. Don't spin — end honestly.
                self._say("no eligible dot to attempt (blocked); ending run")
                return board.end(END_BUDGET)

            self._say(f"  cycle {board.cycle}: attempting dot {dot.id} — {dot.statement}")
            try:
                result = Traveler.attempt(dot.id, self.map, self.workspace, board,
                                          dry_run=self.dry_run)
            except Exception as e:
                # a traveler crash is just a failed attempt — the sovereign loop
                # survives it, logs it, and the budget bounds the retries (rule 4:
                # the agent, even by dying, cannot end the run).
                self._say(f"  traveler crashed on dot {dot.id}: {e}")
                result = {"driver": self.map.traveler.driver, "usd": 0.0,
                          "crashed": str(e)}
            board.log_attempt(dot.id, actions=result.get("actions"))
            board.tick_budget(board.usd_spent + float(result.get("usd", 0.0)))
            if self.dry_run:
                self._persist_dryrun_journal(board.cycle, dot.id, result.get("journal", []))

        return board.end(END_BUDGET)

    def _persist_dryrun_journal(self, cycle: int, dot_id: str, journal) -> None:
        """Append this attempt's intended actions to .dotmaps/dryrun.jsonl.

        The journal IS the product of a dry run: what the traveler would have
        done, reviewable before anything is allowed to touch the real world.
        """
        import json
        path = self.workspace / ".dotmaps" / "dryrun.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            for entry in journal:
                f.write(json.dumps({"cycle": cycle, "dot": dot_id, **entry}) + "\n")

    # -- reporting ---------------------------------------------------------- #
    def _report_cycle(self, board: Scoreboard, results) -> None:
        if not self.verbose:
            return
        green = sum(1 for r in results if r.passed)
        self._say(f"cycle {board.cycle}: {green}/{len(results)} dots green")

    def _say(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)


def run(m: Map, workspace: str | Path, resume: bool = False,
        verify_mode: str = "local", verbose: bool = True,
        dry_run: bool = False) -> Scoreboard:
    return Orchestrator(m, workspace, verify_mode=verify_mode, verbose=verbose,
                        dry_run=dry_run).run(resume=resume)
