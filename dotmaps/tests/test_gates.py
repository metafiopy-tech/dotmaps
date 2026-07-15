"""Phase-2 gate: destructive gating works (spec §5).

A destructive dot must never be attempted without dry-run, a human confirm, or
an explicit per-run allow flag — and a blocked dot is skipped loudly, with the
decision on the audit trail.
"""
from conftest import SMOKE_MAP

from dotmaps.models import Dot, Map
from dotmaps.runtime.orchestrator import Orchestrator
from dotmaps.safety import gates


DESTRUCTIVE = Dot(id="d1", statement="wipe something", verifier="x.py", destructive=True)
SAFE = Dot(id="s1", statement="read something", verifier="y.py", destructive=False)


def test_non_destructive_always_allowed():
    cfg = gates.GateConfig()
    assert gates.guard(SAFE, cfg) == gates.ALLOW
    assert cfg.decisions == []  # only destructive decisions are audit-worthy


def test_destructive_blocked_by_default():
    cfg = gates.GateConfig()
    assert gates.guard(DESTRUCTIVE, cfg) == gates.BLOCK
    assert cfg.decisions[-1]["decision"] == gates.BLOCK


def test_destructive_allowed_in_dryrun():
    # dry-run should rehearse the destructive path (it's mocked anyway)
    assert gates.guard(DESTRUCTIVE, gates.GateConfig(dry_run=True)) == gates.ALLOW


def test_destructive_allowed_by_explicit_flag():
    assert gates.guard(DESTRUCTIVE, gates.GateConfig(allow_destructive=True)) == gates.ALLOW


def test_confirm_callback_outranks_flag():
    # a human "no" wins even when the flag would have allowed it
    cfg = gates.GateConfig(allow_destructive=True, confirm=lambda d: False)
    assert gates.guard(DESTRUCTIVE, cfg) == gates.BLOCK
    cfg2 = gates.GateConfig(confirm=lambda d: True)
    assert gates.guard(DESTRUCTIVE, cfg2) == gates.ALLOW


def test_orchestrator_skips_blocked_destructive_dot(tmp_path, monkeypatch):
    """End-to-end: flag the smoke map's second dot destructive; without any
    allow, the run must eat dot 001, skip 002, and end honestly red."""
    m = Map.load(SMOKE_MAP)
    dots = tuple(
        Dot(id=d.id, statement=d.statement, verifier=d.verifier,
            depends_on=d.depends_on, destructive=(d.id == "002"))
        for d in m.dots
    )
    m = Map(name=m.name, version=m.version, domain=m.domain,
            mcp_required=m.mcp_required, budget=m.budget, traveler=m.traveler,
            dots=dots, fog_ref=m.fog_ref, blast_radius_ref=m.blast_radius_ref,
            root=m.root)

    board = Orchestrator(m, tmp_path / "ws", verbose=False).run()
    assert "001" in board.eaten
    assert "002" not in board.eaten          # never attempted, let alone eaten
    assert board.ended == "budget_exhausted"  # red, loudly — not a fake green
    # and the workspace shows 002's action never ran
    assert (tmp_path / "ws" / "hello.txt").read_text() == "placeholder\n"
