"""G1 gates: extractor obeys the frozen rubric."""
import json
from pathlib import Path
from dotmaps.bank.extractor import bank, extract_run

REPO = Path(__file__).resolve().parents[2]
RUNS = sorted((REPO / "runs").glob("grow-00*"))


def test_extraction_yields_candidates_only(tmp_path):
    m = bank(RUNS, tmp_path / "skills")
    assert m["counts"]["skills"] >= 1
    for s in m["skills"]:
        assert s["certificate"]["status"] == "candidate"   # R-STATE
    assert m["coverage"] == {}          # nothing certified yet
    assert set(m["frontier"]) == {t for s in m["skills"] for t in s["trigger"]}


def test_dedup_merges_cross_run_repeats(tmp_path):
    m = bank(RUNS, tmp_path / "skills")
    c = m["counts"]
    assert c["provenance_entries"] > c["skills"]           # R-DEDUP fired
    assert c["dedup_merges"] == c["provenance_entries"] - c["skills"]


def test_distinct_checks_stay_distinct(tmp_path):
    cards = extract_run(REPO / "runs" / "grow-005")
    hashes = {c["method"]["hash"] for c in cards}
    assert len(hashes) == len(cards)    # same file, different check ≠ merged


def test_every_skill_carries_check_and_provenance(tmp_path):
    for rd in RUNS:
        for c in extract_run(rd):
            assert c["check"].get("predicate")             # R-CHECK
            assert c["provenance"][0]["banked_from"]       # R-PROV
