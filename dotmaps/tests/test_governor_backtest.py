"""Q3 gate: the governor, retroactively graded against archived history.
Reads runs/e1b*/e1c*/e1d* (frozen, read-only — never written to) and the
committed runs/governor-backtest/report.json this script produces."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments"))
import governor_backtest as gb  # noqa: E402


def test_iter_run_dirs_excludes_void_and_verdict():
    dirs = gb.iter_run_dirs("e1b")
    names = {d.name for d in dirs}
    assert "e1b-verdict" not in names
    assert not any("VOID" in n for n in names)
    assert "e1b-cold-01" in names and "e1b-eq-01" in names


def test_persistence_budget_computed_from_real_journals():
    budget = gb.compute_persistence_budget()
    assert budget["n"] > 0
    assert budget["p75"] is not None
    assert budget["per_prefix_n"]["e1b"] > 0
    assert budget["per_prefix_n"]["e1c"] > 0
    assert budget["per_prefix_n"]["e1d"] > 0


def test_reproduces_churn_in_e1c_and_its_elimination_in_e1d():
    v = gb.reproduce_verdicts()
    assert v["e1c_refog_total"] > 0     # e1c-verdict: in-flight-race churn
    assert v["e1d_refog_total"] == 0    # e1d-verdict: "refog=0 in ALL 16 runs"
    assert v["churn_reproduced"] is True


def test_zero_false_wall_on_e1d_banked_families():
    v = gb.reproduce_verdicts()
    assert v["e1d_false_wall_count"] == 0


def test_full_backtest_passes_and_matches_committed_report():
    report = gb.run_backtest()
    assert report["pass"] is True
    committed = json.loads((REPO / "runs" / "governor-backtest" / "report.json").read_text())
    assert committed["pass"] is True
    assert committed["persistence_budget"]["p75"] == report["persistence_budget"]["p75"]


def test_persistence_budget_constant_matches_backtest():
    """queen/governor.py's PERSISTENCE_BUDGET_POKES must equal the
    backtest's own p75 — a magic number that drifted from its citation
    would violate frozen law #6."""
    from dotmaps.queen import governor
    budget = gb.compute_persistence_budget()
    assert governor.PERSISTENCE_BUDGET_POKES == int(budget["p75"])
