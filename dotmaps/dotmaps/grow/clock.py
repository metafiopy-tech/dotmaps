"""Phase clock v0 — crude thresholds, logged series, deliberately replaceable.

This is the component H1 would have upgraded (a certified convergence
detector instead of counters). v0 uses the spec's defaults and logs the
novelty-rate series regardless, so a future certified clock can be compared
against these very runs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClockConfig:
    window_k: int = 15      # pokes per novelty window
    epsilon: int = 1        # POKE->FORAGE when new banks in window < epsilon
    forage_attempts: int = 3   # fetches per hypothesis before it fogs
    max_pokes: int = 150    # hard budget per spiral
    max_fetches: int = 20
    max_spirals: int = 3


class PhaseClock:
    def __init__(self, cfg: ClockConfig | None = None):
        self.cfg = cfg or ClockConfig()
        self._bank_pokes: list[int] = []  # poke numbers at which banks happened
        self._pokes = 0
        self._fetches = 0

    def tick_poke(self) -> None:
        self._pokes += 1

    def tick_bank(self) -> None:
        self._bank_pokes.append(self._pokes)

    def tick_fetch(self) -> None:
        self._fetches += 1

    @property
    def pokes(self) -> int:
        return self._pokes

    @property
    def banked(self) -> int:
        return len(self._bank_pokes)

    def novelty_in_window(self) -> int:
        floor = self._pokes - self.cfg.window_k
        return sum(1 for n in self._bank_pokes if n > floor)

    def should_forage(self, open_hypotheses: int) -> bool:
        """POKE -> FORAGE: novelty dried up AND questions remain."""
        return (self._pokes >= self.cfg.window_k
                and self.novelty_in_window() < self.cfg.epsilon
                and open_hypotheses > 0)

    def poke_budget_left(self) -> bool:
        return self._pokes < self.cfg.max_pokes

    def fetch_budget_left(self) -> bool:
        return self._fetches < self.cfg.max_fetches

    def should_metabolize(self, open_hypotheses: int) -> bool:
        """POKE/FORAGE -> METABOLIZE: nothing left to ask, or budgets gone."""
        exhausted = (not self.poke_budget_left())
        dried = (self._pokes >= self.cfg.window_k
                 and self.novelty_in_window() < self.cfg.epsilon
                 and open_hypotheses == 0)
        return exhausted or dried
