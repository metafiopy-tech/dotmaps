"""Attack-pass hardenings (Phase 3) — each closed finding gets a proof.

A1/B2/C1: config tampering — verifiers judge the authoritative .dotmaps/ copy,
          not the traveler-writable workspace-root copy.
B1:       source rewriting — a source file that no longer matches the hash
          pinned at compile time is a hard verifier error, not a green board.
"""
import json

from conftest import MAPS

from dotmaps.compiler.intake import compile_map
from dotmaps.models import Map
from dotmaps.verifier.runner import Verifier

MAP1 = MAPS / "map-deploy-verify-cloudflare"
MAP2 = MAPS / "map-content-migration"


def test_verifier_prefers_authoritative_config_over_tampered(tmp_path):
    """A1: tamper the workspace-root target.json; the verifier must judge the
    .dotmaps/ copy. Dot 008 makes this observable offline: authentic config has
    no custom domain (vacuous pass); the tampered root copy sets one that would
    fail DNS."""
    m = Map.load(MAP1)
    ws = tmp_path / "ws"
    (ws / ".dotmaps").mkdir(parents=True)
    authentic = {"base_url": "https://example.com", "pages": ["/"], "custom_domain": None}
    (ws / ".dotmaps" / "target.json").write_text(json.dumps(authentic))
    # the traveler-writable copy, maliciously rewritten
    tampered = dict(authentic, custom_domain="attacker-chosen.invalid")
    (ws / "target.json").write_text(json.dumps(tampered))

    r = Verifier.for_map(m, mode="local").run_one(m, "008", ws)
    assert r.passed, r.evidence  # judged the authentic copy: vacuously satisfied
    assert "no custom domain" in r.evidence


def test_source_hash_pinned_at_compile(tmp_path):
    """B1 setup: compiling with the source export present pins its sha256."""
    m = Map.load(MAP2)
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "source_items.json").write_text('[{"slug": "a", "title": "A"}]')
    answers = {"source": "source_items.json", "target": "target_items.json",
               "slug_field": "slug", "required_fields": "title",
               "hash_fields": "title", "spot_hash_sample": 1,
               "links_field": "body", "internal_link_base": ""}
    out = compile_map(m, ws, answers=answers, approve=lambda b: True)
    cfg = json.loads(out.read_text())
    assert len(cfg["source_sha256"]) == 64
    # authoritative copy carries the pin too
    auth = json.loads((ws / ".dotmaps" / "migration.json").read_text())
    assert auth["source_sha256"] == cfg["source_sha256"]


def test_protected_source_is_unwritable_by_traveler(tmp_path):
    """B1 prevention (found live: the ollama traveler 'helpfully' rewrote the
    source to match its enriched target). After compile, the walls refuse
    traveler writes to the source file; reads still work."""
    import pytest
    from dotmaps.runtime.traveler import ScopeViolation, ToolBox

    m2 = Map.load(MAP2)
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "source_items.json").write_text('[{"slug": "a", "title": "Real"}]')
    answers = {"source": "source_items.json", "target": "target_items.json",
               "slug_field": "slug", "required_fields": "title",
               "hash_fields": "title", "spot_hash_sample": 1,
               "links_field": "body", "internal_link_base": ""}
    compile_map(m2, ws, answers=answers, approve=lambda b: True)
    assert json.loads((ws / ".dotmaps" / "protected_paths.json").read_text()) == \
        ["source_items.json"]

    tools = ToolBox(m2, ws)
    with pytest.raises(ScopeViolation, match="protected"):
        tools.call("filesystem.write_file", path="source_items.json", content="[]")
    # layered defense: map 2 no longer grants filesystem.delete AT ALL (tool-
    # level wall — the Stage-0 move-mode finding), so the wall fires before
    # the path protection ever gets asked.
    from dotmaps.runtime.traveler import WallViolation
    with pytest.raises(WallViolation):
        tools.call("filesystem.delete", path="source_items.json")
    # reading the source is fine — the traveler needs it to migrate
    assert "Real" in tools.call("filesystem.read_file", path="source_items.json")
    # and the actual work product is writable
    tools.call("filesystem.write_file", path="target_items.json", content="[]")


def test_tampered_source_is_a_hard_error_not_a_green_board(tmp_path):
    """B1: overwrite the source after compile; every migration dot must error."""
    m = Map.load(MAP2)
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "source_items.json").write_text('[{"slug": "a", "title": "Real Item"}]')
    answers = {"source": "source_items.json", "target": "target_items.json",
               "slug_field": "slug", "required_fields": "title",
               "hash_fields": "title", "spot_hash_sample": 1,
               "links_field": "body", "internal_link_base": ""}
    compile_map(m, ws, answers=answers, approve=lambda b: True)

    # the attack: traveler rewrites the source to match its (fabricated) target
    fabricated = '[{"slug": "a", "title": "Fabricated"}]'
    (ws / "source_items.json").write_text(fabricated)
    (ws / "target_items.json").write_text(fabricated)

    r = Verifier.for_map(m, mode="local").run_one(m, "m01", ws)
    assert not r.passed
    assert r.errored  # exit 2: refused to judge, loudly
    assert "hash" in r.evidence.lower()
