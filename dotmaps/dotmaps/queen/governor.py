"""GOVERNOR — the abort governor (QUEEN spec §4a hole 3, complete anatomy).

Three orthogonal criteria plus a counterweight:
  (a) competence-flatness  — reads the SKILL: typed failure categories +
      a chi-null churn test over a hypothesis's attempt stream. WALL (same
      mode repeating) / CHURN (variance without net displacement) /
      DIRECTIONAL (failure mode migrating — keep spending even at zero
      success). EQUIP §2.1a.
  (b) oracle-validity      — reads the EVALUATOR: delegates to
      bank/certify.py's oracle_gate, verbatim (never reimplemented —
      frozen law #2's spirit: one oracle gate, one place).
  (c) objective-provenance — reads the OBJECTIVE: v0 invariant, every
      queen objective is inherited from the manifest/compiler, never
      self-generated. Hard assert, not a check that can be silently
      skipped (the quit-at-.400 shaft: this criterion fires while
      performance looks fine).
  counterweight: the persistence budget — spent independent of returns,
      backtested (not invented) from archived e1b/e1c/e1d journals via
      experiments/governor_backtest.py. Without it the other three make
      the colony a quitting machine.

"History grades her before any live run does" — see
experiments/governor_backtest.py and runs/governor-backtest/report.json.
"""
from __future__ import annotations

import random
from typing import Any

from ..bank.certify import oracle_gate  # (b) delegates, never reimplements

# --------------------------------------------------------------------------- #
# (a) competence-flatness: typed failure categories + chi-null churn test    #
# --------------------------------------------------------------------------- #

# Typed FIRST (EQUIP §2.1a: "typed categories first, embeddings only if
# categories fail to separate"), derived mechanically from the grow loop's
# own observation vocabulary (grow/runner.py, grow/banking.py) — not
# invented ad hoc.
CATEGORY_RANK = {
    "check-authoring": 0,   # REJECTED — validate_rule failed; never replayed
    "duplicate-block": 1,   # BLOCKED — in-flight/fogged duplicate
    "duplicate": 1,          # DUPLICATE — already banked
    "wrong-output": 2,       # UNCONFIRMED — replayed, check just didn't hold
}


def classify_category(observation: str) -> str | None:
    """Typed failure category from a poke_journal observation string.
    None = not a failure record (a poke, or CONFIRMED success)."""
    if not observation:
        return None
    if observation.startswith("REJECTED"):
        return "check-authoring"
    if observation.startswith("BLOCKED"):
        return "duplicate-block"
    if observation.startswith("DUPLICATE"):
        return "duplicate"
    if observation.startswith("UNCONFIRMED"):
        return "wrong-output"
    return None


def _transitions(seq: list[str]) -> int:
    return sum(1 for a, b in zip(seq, seq[1:]) if a != b)


MIN_N_FOR_VERDICT = 3  # a permutation test needs room to have power; n=2 has
                       # only one non-trivial shuffle and calling that a
                       # WALL is a false verdict waiting to happen (caught
                       # by the e1d backtest — 7 two-attempt families that
                       # went on to bank). Same floor as certify.py's
                       # STABILITY_N: 3 replays before a verdict is trusted.


def churn_test(categories: list[str], trials: int = 500, seed: int = 0
              ) -> dict[str, Any]:
    """Chi-null churn test (EQUIP §2.1a): null hypothesis is a same-length
    random walk — here, a random permutation of the SAME observed category
    multiset. "Permutation test in practice", per the spec's own words.
    Classifies WALL / CHURN / DIRECTIONAL / INSUFFICIENT."""
    if len(categories) < MIN_N_FOR_VERDICT:
        return {"n": len(categories), "verdict": "INSUFFICIENT",
                "t_obs": None, "p_low": None, "p_high": None,
                "net_displacement": None}

    t_obs = _transitions(categories)
    rng = random.Random(seed)
    pool = list(categories)
    null = []
    for _ in range(trials):
        rng.shuffle(pool)
        null.append(_transitions(pool))
    p_low = sum(1 for t in null if t <= t_obs) / trials
    p_high = sum(1 for t in null if t >= t_obs) / trials

    ranks = [CATEGORY_RANK.get(c, 0) for c in categories]
    net_displacement = ranks[-1] - ranks[0]

    if len(set(categories)) == 1:
        verdict = "WALL"                       # same mode, every attempt
    elif net_displacement > 0 and p_high < 0.10:
        verdict = "DIRECTIONAL"                 # migrating toward success
    elif net_displacement <= 0 and p_high < 0.10:
        verdict = "CHURN"                       # noisy, no net progress
    else:
        verdict = "DIRECTIONAL" if net_displacement > 0 else "WALL"

    return {"n": len(categories), "t_obs": t_obs,
            "p_low": round(p_low, 3), "p_high": round(p_high, 3),
            "net_displacement": net_displacement, "verdict": verdict}


# --------------------------------------------------------------------------- #
# (b) oracle-validity: delegates to certify's oracle gate                    #
# --------------------------------------------------------------------------- #

def oracle_valid(skill: dict, seed) -> tuple[bool, str]:
    """No policy update until the evaluator itself passes structural
    validity. Literally bank/certify.py's oracle_gate — never
    reimplemented (§2.3b: 'certify the certifier', one instrument)."""
    return oracle_gate(skill, seed)


# --------------------------------------------------------------------------- #
# (c) objective-provenance: v0 all inherited, hard assert                    #
# --------------------------------------------------------------------------- #

def check_provenance(objective: dict[str, Any]) -> bool:
    """v0: every queen objective is inherited from the manifest/compiler,
    never self-generated. Hard assert — capable of firing while
    performance is intact (the quit-at-.400 shaft, QUEEN spec §4a hole 3)."""
    prov = objective.get("provenance")
    assert prov == "inherited", (
        f"objective provenance guard fired: {prov!r} is not 'inherited' — "
        "the queen never updates policy on a self-generated objective")
    return True


# --------------------------------------------------------------------------- #
# counterweight: the persistence budget                                     #
# --------------------------------------------------------------------------- #

# Backtested, not invented (frozen law #6): 75th percentile of
# pokes-before-first-bank across every hypothesis family that ultimately
# banked, pooled across the archived e1b/e1c/e1d journals (33 runs, n=1195
# banked families). Provenance: experiments/governor_backtest.py ->
# runs/governor-backtest/report.json (committed, both frozen inputs and
# this constant's derivation auditable). Recompute if new archived
# journals land; the archived journals themselves are frozen (law #2) and
# never edited. The honest result: p75 = 1 poke — the overwhelming
# majority of banked hypotheses confirm on their FIRST attempt; forage
# revision is the tail case, not the median case. A budget this tight
# means (a)'s WALL/CHURN verdicts lean on MIN_N_FOR_VERDICT (below) to
# avoid punishing that first attempt, not on the budget alone.
PERSISTENCE_BUDGET_POKES = 1


def within_persistence_budget(attempts: int) -> bool:
    """The counterweight: without this, criteria (a)-(c) make the colony a
    quitting machine. A hypothesis family gets at least this many attempts
    on its own recognizance before flatness/churn verdicts are trusted."""
    return attempts <= PERSISTENCE_BUDGET_POKES


def assess(categories: list[str], attempts: int) -> dict[str, Any]:
    """Combine (a) with the persistence-budget counterweight: a family
    still inside its budget is never WALL/CHURN-aborted, whatever its
    category trace looks like so far — confidence is not a validator,
    the budget is."""
    verdict = churn_test(categories)
    if attempts <= PERSISTENCE_BUDGET_POKES and verdict["verdict"] in ("WALL", "CHURN"):
        return {**verdict, "verdict": "WITHIN_BUDGET",
                "raw_verdict": verdict["verdict"],
                "persistence_budget": PERSISTENCE_BUDGET_POKES}
    return {**verdict, "persistence_budget": PERSISTENCE_BUDGET_POKES}
