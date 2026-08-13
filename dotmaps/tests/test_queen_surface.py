"""Q1 gate: synthetic ESCALATE flips the surface; resolve restores calm."""
from dotmaps.queen import surface as surface_mod


def test_calm_with_no_trips(tmp_path):
    p = tmp_path / "trips.jsonl"
    c = surface_mod.card(p)
    assert c["status"] == "calm"
    assert "Nothing needs you." == c["message"]


def test_escalate_flips_the_surface(tmp_path):
    p = tmp_path / "trips.jsonl"
    surface_mod.escalate("e1", "grow the frontier now?", ["yes", "no"], path=p)
    c = surface_mod.card(p)
    assert c["status"] == "decision"
    assert len(c["escalations"]) == 1
    assert c["escalations"][0]["id"] == "e1"
    rendered = surface_mod.render(c)
    assert "grow the frontier now?" in rendered
    assert "1. yes" in rendered and "2. no" in rendered


def test_resolve_restores_calm(tmp_path):
    p = tmp_path / "trips.jsonl"
    surface_mod.escalate("e1", "grow now?", ["yes", "no"], path=p)
    assert surface_mod.card(p)["status"] == "decision"
    surface_mod.resolve("e1", 1, path=p)
    c = surface_mod.card(p)
    assert c["status"] == "calm"


def test_resolve_unknown_id_raises(tmp_path):
    p = tmp_path / "trips.jsonl"
    try:
        surface_mod.resolve("nope", 1, path=p)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_resolve_out_of_range_choice_raises(tmp_path):
    p = tmp_path / "trips.jsonl"
    surface_mod.escalate("e1", "q?", ["only-one"], path=p)
    try:
        surface_mod.resolve("e1", 5, path=p)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_multiple_escalations_independent(tmp_path):
    p = tmp_path / "trips.jsonl"
    surface_mod.escalate("e1", "q1?", ["a", "b"], path=p)
    surface_mod.escalate("e2", "q2?", ["a", "b"], path=p)
    surface_mod.resolve("e1", 1, path=p)
    c = surface_mod.card(p)
    assert c["status"] == "decision"
    ids = {e["id"] for e in c["escalations"]}
    assert ids == {"e2"}


def test_reraise_after_resolve_reopens(tmp_path):
    p = tmp_path / "trips.jsonl"
    surface_mod.escalate("e1", "q?", ["a", "b"], path=p)
    surface_mod.resolve("e1", 1, path=p)
    assert surface_mod.card(p)["status"] == "calm"
    surface_mod.escalate("e1", "q again?", ["a", "b"], path=p)
    assert surface_mod.card(p)["status"] == "decision"
