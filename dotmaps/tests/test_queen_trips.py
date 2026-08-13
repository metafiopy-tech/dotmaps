"""Q1 gate: the trip bus is append-only, and that's enforced, not assumed."""
import json

from dotmaps.queen import trips as trips_mod


def test_emit_then_read_roundtrips(tmp_path):
    p = tmp_path / "trips.jsonl"
    r1 = trips_mod.emit("CERTIFIED", path=p, dot="d1", skill="s1")
    r2 = trips_mod.emit("SLEEP", path=p, note="tick")
    recs = trips_mod.read_all(p)
    assert [r["type"] for r in recs] == ["CERTIFIED", "SLEEP"]
    assert recs[0]["seq"] == 1 and recs[1]["seq"] == 2
    assert r2["prev_hash"] == r1["hash"]


def test_unknown_type_rejected(tmp_path):
    p = tmp_path / "trips.jsonl"
    try:
        trips_mod.emit("NOT_A_TYPE", path=p)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_integrity_ok_on_untouched_log(tmp_path):
    p = tmp_path / "trips.jsonl"
    for i in range(5):
        trips_mod.emit("SHELVED", path=p, i=i)
    ok, reason = trips_mod.verify_integrity(p)
    assert ok and reason is None


def test_integrity_detects_rewrite(tmp_path):
    """A rewrite attempt — editing a line's content in place — must fail
    the chain check. This IS the append-only enforcement."""
    p = tmp_path / "trips.jsonl"
    trips_mod.emit("CERTIFIED", path=p, dot="d1")
    trips_mod.emit("CERTIFIED", path=p, dot="d2")
    trips_mod.emit("CERTIFIED", path=p, dot="d3")

    lines = p.read_text().splitlines()
    tampered = json.loads(lines[1])
    tampered["data"]["dot"] = "d2-REWRITTEN"      # forge the middle record
    lines[1] = json.dumps(tampered)
    p.write_text("\n".join(lines) + "\n")

    ok, reason = trips_mod.verify_integrity(p)
    assert not ok
    assert "seq 2" in reason or "seq" in reason


def test_work_order_type_accepted_with_phase_payload(tmp_path):
    """Q8/Q9: WORK_ORDER joins the fixed vocabulary; chain format unchanged
    (still hash-linked, still just a `type` + `data` record)."""
    p = tmp_path / "trips.jsonl"
    r1 = trips_mod.emit("WORK_ORDER", path=p, phase="start", target="migration")
    r2 = trips_mod.emit("WORK_ORDER", path=p, phase="complete", target="migration")
    assert [r["data"]["phase"] for r in trips_mod.read_all(p)] == ["start", "complete"]
    assert r2["prev_hash"] == r1["hash"]
    ok, reason = trips_mod.verify_integrity(p)
    assert ok and reason is None


def test_integrity_detects_deleted_line(tmp_path):
    p = tmp_path / "trips.jsonl"
    trips_mod.emit("CERTIFIED", path=p, dot="d1")
    trips_mod.emit("CERTIFIED", path=p, dot="d2")
    trips_mod.emit("CERTIFIED", path=p, dot="d3")

    lines = p.read_text().splitlines()
    del lines[1]                                    # excise the middle record
    p.write_text("\n".join(lines) + "\n")

    ok, reason = trips_mod.verify_integrity(p)
    assert not ok
