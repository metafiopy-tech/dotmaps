"""E1c mechanism: fog gate blocks re-proposals mechanically."""
from dotmaps.grow.banking import already_fogged


def test_exact_fogged_statement_blocked():
    fogged = ["target_items.json does not exist yet in this workspace"]
    rule = {"statement": "target_items.json does not exist yet in this workspace"}
    assert already_fogged(rule, fogged)


def test_normalization_catches_case_and_whitespace():
    fogged = ["Target_items.json  does not exist yet in this workspace"]
    rule = {"statement": "target_items.json does not exist yet in this workspace "}
    assert already_fogged(rule, fogged)


def test_novel_statement_passes():
    fogged = ["target_items.json does not exist yet in this workspace"]
    rule = {"statement": "migration.json specifies slug_field as 'slug'"}
    assert not already_fogged(rule, fogged)


def test_empty_fog_never_blocks():
    assert not already_fogged({"statement": "anything"}, [])


from dotmaps.grow.banking import blocked_statement


def test_inflight_duplicate_blocked():
    open_h = [{"id": "r002", "statement": "target_items.json does not exist"}]
    rule = {"id": "r003", "statement": "target_items.json does not exist"}
    assert "in-flight" in (blocked_statement(rule, [], open_h) or "")


def test_self_never_blocks_at_revise():
    open_h = [{"id": "r002", "statement": "target_items.json does not exist"}]
    rule = {"id": "r002", "statement": "target_items.json does not exist"}
    assert blocked_statement(rule, [], open_h) is None


def test_fog_still_blocks():
    rule = {"id": "r009", "statement": "Some Dead End"}
    assert blocked_statement(rule, ["some dead end"], []) == "already-fogged"


def test_novel_passes_both_sets():
    open_h = [{"id": "r002", "statement": "a"}]
    assert blocked_statement({"id": "r9", "statement": "b"}, ["c"], open_h) is None
