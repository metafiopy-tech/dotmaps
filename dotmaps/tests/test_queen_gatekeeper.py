"""Q4b gate: the mutualist audit — three tests, hard-refuses on insufficient
data ("an audit that can't fail is not an audit")."""
from dotmaps.queen.gatekeeper import LedgerPeriod, audit


def test_empty_ledger_refuses():
    v = audit([])
    assert v["verdict"] == "REFUSED"
    assert "insufficient data" in v["reason"]


def test_synthetic_pass_ledger():
    periods = [
        LedgerPeriod(period=1, invocations=10, state_changes=6,
                    domains_fired=("scheduling",), friction_class_count=4,
                    friction_class_count_prev=None),
        LedgerPeriod(period=2, invocations=12, state_changes=7,
                    domains_fired=("scheduling", "billing"),
                    friction_class_count=3, friction_class_count_prev=4),
    ]
    v = audit(periods)
    assert v["verdict"] == "PASS"
    assert v["failed_on"] == []
    assert v["state_change"]["passed"]
    assert v["transfer"]["passed"]
    assert v["parasite"]["passed"]


def test_synthetic_fail_ledger_growing_friction_is_parasitism():
    periods = [
        LedgerPeriod(period=1, invocations=10, state_changes=6,
                    domains_fired=("scheduling",), friction_class_count=4,
                    friction_class_count_prev=None),
        LedgerPeriod(period=2, invocations=12, state_changes=7,
                    domains_fired=("scheduling",), friction_class_count=9,
                    friction_class_count_prev=4),   # friction GREW under its watch
    ]
    v = audit(periods)
    assert v["verdict"] == "DEMOTE"
    assert "parasite" in v["failed_on"]
    assert v["parasite"]["growing"] is True


def test_synthetic_fail_ledger_no_state_change_is_the_golf_gig_kill_tell():
    periods = [
        LedgerPeriod(period=1, invocations=10, state_changes=0,
                    domains_fired=("scheduling",), friction_class_count=2,
                    friction_class_count_prev=2),
    ]
    v = audit(periods)
    assert v["verdict"] == "DEMOTE"
    assert "state-change" in v["failed_on"]
    assert v["state_change"]["act_rate"] == 0.0


def test_synthetic_fail_ledger_never_transfers_is_narrative():
    periods = [
        LedgerPeriod(period=1, invocations=10, state_changes=5,
                    domains_fired=(), friction_class_count=2,
                    friction_class_count_prev=2),
    ]
    v = audit(periods)
    assert v["verdict"] == "DEMOTE"
    assert "transfer" in v["failed_on"]
    assert v["transfer"]["domains"] == []


def test_single_period_is_sufficient_for_a_verdict():
    periods = [LedgerPeriod(period=1, invocations=5, state_changes=3,
                            domains_fired=("x",), friction_class_count=1,
                            friction_class_count_prev=1)]
    v = audit(periods)
    assert v["verdict"] in ("PASS", "DEMOTE")   # not REFUSED — one period clears the gate
