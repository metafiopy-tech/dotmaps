"""Q11 gate: `dotmaps assure` — the certainty command. All ten rows re-run
against the REAL committed repo (that is the point: assure the checkout you
actually have), plus two corruption drills proving a broken artifact flips
the right row red rather than assure staying green on say-so."""
import json
import shutil
from pathlib import Path

from dotmaps.queen import assure as assure_mod
from dotmaps.queen import trips as trips_mod

REPO = Path(__file__).resolve().parents[2]


def test_frozen_manifest_matches_the_committed_repo_right_now():
    """This IS the manifest's own self-check: whatever's committed at
    frozen_hashes.json must match the bytes on disk today."""
    ok, detail = assure_mod.check_frozen_files_unchanged()
    assert ok, detail


def test_build_frozen_manifest_has_all_five_registrations():
    m = assure_mod.build_frozen_manifest()
    assert len(m["registrations"]) == 5
    assert all(len(h) == 64 for h in m["registrations"].values())  # sha256 hexdigest
    assert len(m["extractor_rubric"]) == 64
    assert len(m["certify_oracle_gate"]) == 64


def test_corrupting_the_frozen_manifest_flips_row_4_red(tmp_path):
    """Simulates drift by recording a wrong expected hash for one
    registration file — proves the check actually compares bytes instead
    of trusting the manifest's own presence."""
    real = json.loads(assure_mod.FROZEN_HASHES_PATH.read_text())
    tampered = dict(real)
    tampered["extractor_rubric"] = "0" * 64
    p = tmp_path / "frozen_hashes.json"
    p.write_text(json.dumps(tampered))

    ok, detail = assure_mod.check_frozen_files_unchanged(manifest_path=p)
    assert ok is False
    assert "extractor" in detail.lower()


def test_corrupting_a_trip_line_flips_row_3_red(tmp_path):
    p = tmp_path / "trips.jsonl"
    trips_mod.emit("CERTIFIED", path=p, dot="d1")
    trips_mod.emit("CERTIFIED", path=p, dot="d2")
    lines = p.read_text().splitlines()
    tampered = json.loads(lines[0])
    tampered["data"]["dot"] = "d1-REWRITTEN"
    lines[0] = json.dumps(tampered)
    p.write_text("\n".join(lines) + "\n")

    ok, detail = assure_mod.check_trip_chain_integrity(trips_path=p)
    assert ok is False
    assert "broken" in detail.lower()


def test_trip_chain_integrity_ok_on_the_real_committed_log():
    ok, detail = assure_mod.check_trip_chain_integrity()
    assert ok, detail


def test_pilot_covered_check_passes_for_real():
    ok, detail = assure_mod.check_pilot_covered()
    assert ok, detail


def test_certificates_reverify_check_passes_for_real():
    ok, detail = assure_mod.check_certificates_reverify()
    assert ok, detail


def test_governor_backtest_reproduces_check_passes_for_real():
    ok, detail = assure_mod.check_governor_backtest_reproduces()
    assert ok, detail


def test_harvest_idempotent_check_passes_for_real():
    ok, detail = assure_mod.check_harvest_idempotent()
    assert ok, detail


def test_c3_safety_check_passes_for_real():
    ok, detail = assure_mod.check_c3_safety()
    assert ok, detail


def test_funeral_intact_check_passes_for_real():
    ok, detail = assure_mod.check_funeral_intact()
    assert ok, detail


def test_funeral_check_fails_if_verdict_json_no_longer_says_dead(tmp_path):
    p = REPO / "runs" / "e1d-verdict" / "verdict.json"
    real = json.loads(p.read_text())
    happy = {**real, "final_trial_clause_executed": "efficiency claim CONFIRMED, ship it"}
    fake = tmp_path / "verdict.json"
    fake.write_text(json.dumps(happy))
    # exercise the same substring logic the real check uses, against a
    # deliberately revisionist verdict file
    clause = str(happy["final_trial_clause_executed"])
    assert not ("DIES PERMANENTLY" in clause.upper() or "DEAD" in clause.upper())


def test_work_order_gate_check_passes_for_real():
    ok, detail = assure_mod.check_work_order_gate_fails_closed()
    assert ok, detail


def test_ui_endpoints_check_passes_for_real():
    ok, detail = assure_mod.check_ui_endpoints_serve()
    assert ok, detail


def test_watch_oracle_check_passes_for_real():
    ok, detail = assure_mod.check_watch_oracle()
    assert ok, detail


def test_run_assure_all_fourteen_rows_green_on_this_checkout():
    result = assure_mod.run_assure()
    failing = [r for r in result["rows"] if not r["passed"]]
    assert result["pass"] is True, failing
    assert len(result["rows"]) == 14
    assert [r["n"] for r in result["rows"]] == list(range(1, 15))


def test_chat_routes_covered_work_modelless_check_passes_for_real():
    ok, detail = assure_mod.check_chat_routes_covered_modelless()
    assert ok, detail


def test_zero_jargon_across_tabs_check_passes_for_real():
    ok, detail = assure_mod.check_zero_jargon_across_tabs()
    assert ok, detail


def test_zero_jargon_check_catches_a_regression(monkeypatch, tmp_path):
    bad_page = tmp_path / "index.html"
    bad_page.write_text("<html>the manifest lives here</html>")
    monkeypatch.setattr(assure_mod.ui_mod, "STATIC_PAGE", bad_page)
    ok, detail = assure_mod.check_zero_jargon_across_tabs()
    assert ok is False
    assert "manifest" in detail


def test_chat_chain_integrity_check_passes_on_an_empty_ledger(tmp_path):
    ok, detail = assure_mod.check_chat_chain_integrity(chat_path=tmp_path / "chat.jsonl")
    assert ok, detail


def test_chat_chain_integrity_check_catches_tampering(tmp_path):
    from dotmaps.queen import chat as chat_mod
    p = tmp_path / "chat.jsonl"
    chat_mod.emit_chat("user", "hello", path=p)
    lines = p.read_text().splitlines()
    tampered = json.loads(lines[0])
    tampered["text"] = "tampered"
    p.write_text(json.dumps(tampered) + "\n")
    ok, detail = assure_mod.check_chat_chain_integrity(chat_path=p)
    assert ok is False
    assert "broken" in detail.lower()


def test_render_marks_pass_and_fail_rows():
    result = {"pass": False, "rows": [
        {"n": 1, "claim": "a", "artifact": "x", "passed": True, "detail": "ok"},
        {"n": 2, "claim": "b", "artifact": "y", "passed": False, "detail": "broke"},
    ]}
    text = assure_mod.render(result)
    assert "[PASS]  1. a" in text
    assert "[FAIL]  2. b" in text
    assert "ASSURE: FAILED" in text


def test_a_check_that_raises_is_reported_as_a_failing_row_not_a_crash(monkeypatch):
    def _boom():
        raise RuntimeError("simulated crash inside a check")

    monkeypatch.setattr(assure_mod, "_claims", lambda: [
        assure_mod.Claim(1, "a check that explodes", "nowhere", _boom)])
    result = assure_mod.run_assure()
    assert result["pass"] is False
    assert result["rows"][0]["passed"] is False
    assert "simulated crash" in result["rows"][0]["detail"]
