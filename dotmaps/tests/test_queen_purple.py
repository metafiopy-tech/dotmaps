"""Q5 gate: Purple's ledger accrues from ESCALATE resolutions; threshold
application hard-refuses below 20 events, count visible."""
from dotmaps.queen import purple
from dotmaps.queen import surface as surface_mod


def _raise_and_resolve(p, i, category, choice_label_wanted):
    options = ["grow now", "keep shelving"]
    choice = 1 if choice_label_wanted == "grow now" else 2
    surface_mod.escalate(f"e{i}", f"q{i}?", options, path=p, category=category)
    surface_mod.resolve(f"e{i}", choice, path=p)


def test_ledger_accrues(tmp_path):
    p = tmp_path / "trips.jsonl"
    for i in range(3):
        _raise_and_resolve(p, i, "budget", "grow now")
    rows = purple.ledger(p)
    assert len(rows) == 3
    assert all(r["outcome"] == "acted" for r in rows)
    assert all(r["category"] == "budget" for r in rows)


def test_unresolved_escalation_is_ignored(tmp_path):
    p = tmp_path / "trips.jsonl"
    surface_mod.escalate("e1", "q?", ["a", "b"], path=p, category="frontier")
    rows = purple.ledger(p)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "ignored"
    assert rows[0]["latency_trips"] is None


def test_deferred_outcome_from_defer_marker(tmp_path):
    p = tmp_path / "trips.jsonl"
    _raise_and_resolve(p, 0, "budget", "keep shelving")
    rows = purple.ledger(p)
    assert rows[0]["outcome"] == "deferred"


def test_refusal_below_20_events_enforced(tmp_path):
    p = tmp_path / "trips.jsonl"
    for i in range(19):
        _raise_and_resolve(p, i, "budget", "grow now")
    summary = purple.act_rate_table(p)
    assert summary["n_events"] == 19
    assert summary["threshold_applicable"] is False
    try:
        purple.apply_threshold("budget", path=p)
        assert False, "expected RuntimeError below threshold"
    except RuntimeError as e:
        assert "19" in str(e)


def test_threshold_applies_at_20_events(tmp_path):
    p = tmp_path / "trips.jsonl"
    for i in range(20):
        _raise_and_resolve(p, i, "budget", "grow now")
    summary = purple.act_rate_table(p)
    assert summary["n_events"] == 20
    assert summary["threshold_applicable"] is True
    rate = purple.apply_threshold("budget", path=p)
    assert rate == 1.0


def test_act_rate_table_per_category(tmp_path):
    p = tmp_path / "trips.jsonl"
    for i in range(10):
        _raise_and_resolve(p, i, "budget", "grow now")
    for i in range(10, 20):
        _raise_and_resolve(p, i, "frontier", "keep shelving")
    summary = purple.act_rate_table(p)
    assert summary["table"]["budget"]["act_rate"] == 1.0
    assert summary["table"]["frontier"]["act_rate"] == 0.0
    assert summary["table"]["frontier"]["deferred"] == 10
