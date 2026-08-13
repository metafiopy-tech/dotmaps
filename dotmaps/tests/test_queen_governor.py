"""Q3 gate: the abort governor's three criteria + persistence-budget
counterweight, unit-tested with synthetic data (the backtest in
experiments/governor_backtest.py grades her against real history)."""
from pathlib import Path

import pytest

from dotmaps.queen import governor

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "corpus" / "pilot" / "seed-ws"


# -- (a) competence-flatness -------------------------------------------- #

def test_classify_category_typed_from_observation_strings():
    assert governor.classify_category("REJECTED: bad rule") == "check-authoring"
    assert governor.classify_category("BLOCKED (already-fogged)") == "duplicate-block"
    assert governor.classify_category("DUPLICATE of banked [r1]") == "duplicate"
    assert governor.classify_category("UNCONFIRMED: obs") == "wrong-output"
    assert governor.classify_category("CONFIRMED: obs") is None
    assert governor.classify_category("") is None


def test_churn_test_insufficient_below_min_n():
    v = governor.churn_test(["wrong-output", "wrong-output"])
    assert v["verdict"] == "INSUFFICIENT"


def test_churn_test_wall_same_category_repeated():
    v = governor.churn_test(["check-authoring"] * 5)
    assert v["verdict"] == "WALL"


def test_churn_test_directional_migrating_toward_success():
    # each attempt gets further along: rejected -> duplicate -> wrong-output
    v = governor.churn_test(["check-authoring", "duplicate-block", "wrong-output",
                             "wrong-output", "wrong-output"])
    assert v["verdict"] == "DIRECTIONAL"


def test_churn_test_churn_oscillating_no_net_progress():
    # duplicate-block and duplicate share CATEGORY_RANK (both 1), so net
    # displacement is exactly 0 by construction, not a coin flip — while
    # strict alternation maximizes transitions (7 of 7 possible), a
    # pattern a random shuffle of this multiset rarely reaches.
    v = governor.churn_test(["duplicate-block", "duplicate"] * 4)
    assert v["net_displacement"] == 0
    assert v["verdict"] == "CHURN"


def test_assess_within_budget_overrides_premature_verdict():
    # a single failed attempt is within the (backtested) persistence
    # budget of 1 — never punished, whatever its raw verdict would be
    v = governor.assess(["check-authoring"], attempts=1)
    assert v["verdict"] in ("WITHIN_BUDGET", "INSUFFICIENT")


def test_assess_beyond_budget_lets_wall_through():
    v = governor.assess(["check-authoring"] * 5, attempts=5)
    assert v["verdict"] == "WALL"


# -- (b) oracle-validity: delegates, never reimplements ------------------ #

def test_oracle_valid_delegates_to_certify_oracle_gate():
    import yaml
    skill = yaml.safe_load((REPO / "skills" /
                           "the-source-items-json-file-contains-items-with-a.yaml"
                           ).read_text())
    ok, verdict = governor.oracle_valid(skill, SEED)
    assert ok is True
    assert "oracle gate passed" in verdict

    from dotmaps.bank.certify import oracle_gate
    assert governor.oracle_valid(skill, SEED) == oracle_gate(skill, SEED)  # thin pass-through, not a reimplementation


# -- (c) objective-provenance: hard assert -------------------------------- #

def test_check_provenance_passes_on_inherited():
    assert governor.check_provenance({"provenance": "inherited"}) is True


def test_check_provenance_hard_asserts_on_self_generated():
    with pytest.raises(AssertionError):
        governor.check_provenance({"provenance": "self-generated"})


def test_check_provenance_hard_asserts_on_missing():
    with pytest.raises(AssertionError):
        governor.check_provenance({})


# -- counterweight: persistence budget ------------------------------------ #

def test_persistence_budget_is_a_positive_backtested_constant():
    assert governor.PERSISTENCE_BUDGET_POKES >= 1
    assert governor.within_persistence_budget(governor.PERSISTENCE_BUDGET_POKES)
    assert not governor.within_persistence_budget(governor.PERSISTENCE_BUDGET_POKES + 100)
