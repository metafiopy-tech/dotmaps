"""Pick the next uneaten dot whose dependencies are all satisfied.

Pure function over (board, dots) — no side effects, trivially testable.
"""

from __future__ import annotations

from typing import Optional

from ..models import Dot
from ..scoreboard.state import Scoreboard


class Selector:
    @staticmethod
    def next_uneaten(
        board: Scoreboard,
        dots: tuple[Dot, ...],
        skip: frozenset[str] | set[str] = frozenset(),
    ) -> Optional[Dot]:
        for dot in dots:
            if dot.id in board.eaten or dot.id in skip:
                continue
            if all(dep in board.eaten for dep in dot.depends_on):
                return dot
        # nothing eligible: all eaten, gate-blocked (skip), or waiting on a
        # dependency that itself can't be eaten. Orchestrator treats None as
        # "no progress possible this cycle".
        return None
