"""H10 (HARDENING_BRIEF): assure grows four new claims covering the audit's
own hardening — chat proof boundary (H1), SSRF matrix (H3), env isolation
(H2), concurrency (H4). Same law as every existing claim: re-run the real
instrument, never trust a stored label."""
from dotmaps.queen import assure as assure_mod


def test_check_chat_proof_boundary_passes():
    ok, detail = assure_mod.check_chat_proof_boundary()
    assert ok, detail
    assert "blocked=True" in detail
    assert "filtered=True" in detail
    assert "gate=True" in detail


def test_check_ssrf_matrix_green_passes():
    ok, detail = assure_mod.check_ssrf_matrix_green()
    assert ok, detail
    assert "8/8" in detail


def test_check_env_isolation_passes():
    ok, detail = assure_mod.check_env_isolation()
    assert ok, detail
    assert "False" in detail


def test_check_concurrency_safe_journal_passes():
    ok, detail = assure_mod.check_concurrency_safe_journal()
    assert ok, detail
    assert "200/200" in detail


def test_all_eighteen_claims_are_registered_in_order():
    claims = assure_mod._claims()
    assert len(claims) == 18
    assert [c.n for c in claims] == list(range(1, 19))
    assert claims[14].text.startswith("Chat proof boundary")
    assert claims[15].text.startswith("SSRF matrix")
    assert claims[16].text.startswith("Env isolation")
    assert claims[17].text.startswith("Concurrency")
