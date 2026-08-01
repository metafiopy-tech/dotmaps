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
